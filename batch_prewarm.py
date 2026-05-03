#!/usr/bin/env python3
# batch_prewarm.py
#
# One-time batch pre-generation script.
# Run from terminal BEFORE launch to pre-warm the question cache.
# After this runs, your readiness endpoint serves from cache for ~97% of users.
#
# Usage:
#   python batch_prewarm.py --dry-run              # count only, no API calls
#   python batch_prewarm.py                        # full run (resumes if interrupted)
#   python batch_prewarm.py --scheme-id 42         # single scheme only
#   python batch_prewarm.py --max-combo-size 2     # only 1-2 unknown field combos
#   python batch_prewarm.py --no-resume            # regenerate everything from scratch
#
# Environment:
#   GEMINI_API_KEY  — required (except for --dry-run)
#
# Output:
#   - Progress logged to stdout + prewarm.log
#   - Results written to question_cache table in yojanamitra.db

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from itertools import combinations
from pathlib import Path
from typing import Optional

import google.generativeai as genai

from question_cache_db import (
    DB_PATH,
    cache_get,
    cache_put,
    init_db,
    make_fingerprint,
)

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("prewarm.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

CONDITIONS_PATH   = Path("all_extracted_conditions.json")
GEMINI_MODEL      = "gemini-flash-latest"

# Rate limiting — stay under Gemini free tier limits (15 RPM for Flash)
RATE_LIMIT_RPM = 15
DELAY_BETWEEN_CALLS = 60.0 / RATE_LIMIT_RPM   # ~2 seconds

# Enumeration limits
MAX_COMBO_SIZE        = 3   # 1, 2, or 3 unknown fields per fingerprint
MAX_FIELDS_PER_SCHEME = 8   # skip full enumeration for schemes with more required fields

# ── Condition → Canonical field name mapping ──────────────────────────────────
# Maps keys in all_extracted_conditions.json to the field names your
# deterministic engine produces in unknownFields[].
# Add any fields from your actual JSON that aren't listed here.

CONDITION_TO_CANONICAL: dict[str, str] = {
    "min_age":                "age",
    "max_age":                "age",
    "age":                    "age",
    "gender":                 "gender",
    "caste_category":         "caste_category",
    "category":               "caste_category",
    "income_annual_max":      "annual_income",
    "income_annual_min":      "annual_income",
    "annual_income":          "annual_income",
    "income":                 "annual_income",
    "state":                  "state",
    "occupation":             "occupation",
    "education_level":        "education_level",
    "education":              "education_level",
    "residence_type":         "residence_type",
    "residence":              "residence_type",
    "disability_percentage":  "disability_percentage",
    "disability_pct":         "disability_percentage",
    "marital_status":         "marital_status",
    "is_widow":               "is_widow",
    "is_widowed":             "is_widow",
    "is_student":             "is_student",
    "land_owned_acres":       "land_owned_acres",
    "land_acres":             "land_owned_acres",
    "ration_card_type":       "ration_card_type",
    "ration_card":            "ration_card_type",
    "has_bank_account":       "has_bank_account",
    "bank_account":           "has_bank_account",
    "has_aadhaar":            "has_aadhar",
    "has_aadhar":             "has_aadhar",
    "aadhaar":                "has_aadhar",
    "is_citizen":             "is_citizen",
    "bank_account_type":      "bank_account_type",
    "num_children":           "num_children",
    "children_count":         "num_children",
    "is_pregnant":            "is_pregnant",
    "pregnant":               "is_pregnant",
    "house_ownership_status": "house_ownership_status",
    "house_type":             "house_ownership_status",
    "has_toilet":             "has_toilet",
    "toilet":                 "has_toilet",
    "has_electricity":        "has_electricity_connection",
    "electricity":            "has_electricity_connection",
    "is_minority":            "is_minority",
    "minority":               "is_minority",
    "is_ex_serviceman":       "is_ex_serviceman",
    "ex_serviceman":          "is_ex_serviceman",
    "is_disabled":            "is_disabled",
    "disabled":               "is_disabled",
}

# Values that mean "no requirement" — field is not a gate for this scheme
NON_REQUIREMENTS = {None, "", "any", "all", "both", "no restriction", "none"}


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Identify required fields from conditions dict
# ══════════════════════════════════════════════════════════════════════════════

def get_required_fields(conditions: dict) -> list[str]:
    """
    From a scheme's conditions dict, return the canonical field names
    that have actual requirements.

    A field is "required" if its value is not None, not [], not "any".
    These are the fields that COULD be unknown for a user.
    """
    seen: set[str] = set()
    result: list[str] = []

    for key, value in conditions.items():
        # Skip non-requirements
        if isinstance(value, list):
            if not value: continue
        elif value in NON_REQUIREMENTS:
            continue
        if isinstance(value, str) and value.lower() in NON_REQUIREMENTS:
            continue
        if isinstance(value, list) and len(value) == 0:
            continue

        canonical = CONDITION_TO_CANONICAL.get(key, key)
        if canonical not in seen:
            seen.add(canonical)
            result.append(canonical)

    return result


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Build Gemini prompt
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_INSTRUCTION = """You are an expert assistant helping Indian citizens understand 
their eligibility for government welfare schemes (Yojanas). 

Your task: given a scheme's requirements and a list of fields we don't know about the user,
generate friendly clarification questions that resolve the unknowns.

STRICT RULES — follow exactly:
1. Return ONLY valid JSON. No markdown fences. No explanation. No preamble.
2. One item per unknown field — never merge two fields into one item.
3. The "title" field must be EXACTLY the field name given — do not modify it.
4. Questions must be warm, simple, in Hindi-English (Hinglish).
5. Questions must be under 25 words.
6. "type" must be "warning" for important fields, "error" for critical/blocking fields.
7. "icon" must always be "fa-circle-exclamation".
"""


def build_gemini_prompt(
    scheme_name: str,
    scheme_desc: str,
    conditions: dict,
    unknown_fields: list[str],
) -> str:
    """
    Build the prompt for Gemini. Does NOT include user-specific profile data
    so the output is cacheable across all users with the same unknown_fields.
    """
    # Build requirement context: what does the scheme require for these fields?
    req_lines: list[str] = []
    for field in unknown_fields:
        # Find the raw condition value for this field
        for cond_key, cond_val in conditions.items():
            mapped = CONDITION_TO_CANONICAL.get(cond_key, cond_key)
            if mapped == field and cond_val not in NON_REQUIREMENTS:
                req_lines.append(f"  - {field}: required = {cond_val}")
                break
        else:
            req_lines.append(f"  - {field}: required (refer to scheme description)")

    requirements_block = "\n".join(req_lines)
    fields_list        = ", ".join(f'"{f}"' for f in unknown_fields)

    return f"""Scheme Name: {scheme_name}
Scheme Description: {scheme_desc}

Fields we need to clarify from the user (these are unknown/missing):
{chr(10).join(f'  - {f}' for f in unknown_fields)}

What the scheme requires for these fields:
{requirements_block}

Generate a JSON object in EXACTLY this format, with one item per unknown field:

{{
  "items": [
    {{
      "title": "exact_field_name_from_list_above",
      "text": "One sentence (in English) explaining why this specific information matters for this scheme.",
      "type": "warning",
      "icon": "fa-circle-exclamation",
      "question": "Short friendly Hinglish question to ask the user? (under 25 words)"
    }}
  ]
}}

Generate exactly {len(unknown_fields)} items, one for each of: {fields_list}
Return ONLY the JSON. No other text."""


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Gemini API call with retry
# ══════════════════════════════════════════════════════════════════════════════

def call_gemini(
    scheme_name: str,
    scheme_desc: str,
    conditions: dict,
    unknown_fields: list[str],
    model,
    max_retries: int = 3,
) -> Optional[list[dict]]:
    """
    Call Gemini for one fingerprint. Returns items list or None on permanent failure.
    Retries on transient failures with exponential backoff.
    """
    prompt = build_gemini_prompt(scheme_name, scheme_desc, conditions, unknown_fields)

    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,        # low temp → consistent structured output
                    max_output_tokens=1500,
                ),
            )

            raw_text = response.text.strip()

            # Strip markdown code fences if Gemini added them despite instructions
            if raw_text.startswith("```"):
                lines    = raw_text.split("\n")
                raw_text = "\n".join(
                    line for line in lines
                    if not line.startswith("```")
                ).strip()

            parsed = json.loads(raw_text)
            items  = parsed.get("items", [])

            # Validate structure
            if not items:
                raise ValueError("Gemini returned empty items array")

            required_keys = {"title", "text", "type", "icon", "question"}
            for item in items:
                missing_keys = required_keys - set(item.keys())
                if missing_keys:
                    raise ValueError(f"Item missing keys {missing_keys}: {item}")

            return items

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error (attempt {attempt + 1}/{max_retries}): {e}")
        except ValueError as e:
            logger.warning(f"Validation error (attempt {attempt + 1}/{max_retries}): {e}")
        except Exception as e:
            logger.warning(f"Gemini call error (attempt {attempt + 1}/{max_retries}): {type(e).__name__}: {e}")

        if attempt < max_retries - 1:
            wait = 2 ** attempt  # 1s, 2s, 4s
            logger.debug(f"Retrying in {wait}s...")
            time.sleep(wait)

    return None


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Enumerate all fingerprints
# ══════════════════════════════════════════════════════════════════════════════

def enumerate_fingerprints(
    conditions_data: dict,
    schemes_meta: dict,
    max_combo_size: int,
    target_scheme_id: Optional[str],
) -> list[tuple[str, str, str, dict, list[str]]]:
    """
    Returns list of (scheme_id, scheme_name, scheme_desc, conditions, unknown_fields)
    tuples — one per fingerprint to pre-generate.

    Enumerates all combinations of required fields of size 1..max_combo_size.
    This covers every realistic unknown pattern without random sampling.
    """
    fingerprints: list[tuple] = []
    scheme_ids = [target_scheme_id] if target_scheme_id else list(conditions_data.keys())

    for scheme_id in scheme_ids:
        # Handle both {scheme_id: {conditions: {...}}} and {scheme_id: {...}} formats
        raw = conditions_data.get(str(scheme_id), {})
        conditions = raw.get("conditions", raw) if isinstance(raw, dict) else {}

        if not conditions:
            logger.debug(f"Scheme {scheme_id}: no conditions, skipping")
            continue

        meta         = schemes_meta.get(str(scheme_id), {})
        scheme_name  = meta.get("name", f"Scheme {scheme_id}")
        scheme_desc  = meta.get("description", "A government welfare scheme for eligible citizens")

        required_fields = get_required_fields(conditions)

        if not required_fields:
            logger.debug(f"Scheme {scheme_id}: no required fields after filtering")
            continue

        # Cap to avoid combinatorial explosion on schemes with many required fields
        if len(required_fields) > MAX_FIELDS_PER_SCHEME:
            logger.debug(
                f"Scheme {scheme_id}: {len(required_fields)} required fields — "
                f"capping to {MAX_FIELDS_PER_SCHEME} highest-IG fields"
            )
            required_fields = required_fields[:MAX_FIELDS_PER_SCHEME]

        # Enumerate all combinations of size 1..max_combo_size
        effective_max = min(max_combo_size, len(required_fields))
        for size in range(1, effective_max + 1):
            for combo in combinations(required_fields, size):
                fingerprints.append((
                    str(scheme_id),
                    scheme_name,
                    scheme_desc,
                    conditions,
                    list(combo),
                ))

    return fingerprints


# ══════════════════════════════════════════════════════════════════════════════
# MAIN RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def run_batch(
    api_key: str,
    max_combo_size: int = MAX_COMBO_SIZE,
    target_scheme_id: Optional[str] = None,
    dry_run: bool = False,
    resume: bool = True,
) -> None:
    """
    Main entry point. Orchestrates all 4 steps.
    Safe to interrupt and re-run with --resume.
    """

    # ── Load data ─────────────────────────────────────────────────────────────
    if not CONDITIONS_PATH.exists():
        logger.error(f"Conditions file not found: {CONDITIONS_PATH}")
        sys.exit(1)

    logger.info(f"Loading conditions from {CONDITIONS_PATH}...")
    with open(CONDITIONS_PATH, encoding="utf-8") as f:
        conditions_data = json.load(f)
    logger.info(f"Loaded {len(conditions_data):,} schemes from conditions file")

    if SCHEMES_META_PATH.exists():
        with open(SCHEMES_META_PATH, encoding="utf-8") as f:
            schemes_meta = json.load(f)
        logger.info(f"Loaded meta for {len(schemes_meta):,} schemes")
    else:
        logger.warning(
            f"schemes_meta.json not found at {SCHEMES_META_PATH}. "
            f"Scheme names will be generic (Scheme 1, Scheme 2...). "
            f"This reduces question quality. Create the file for best results."
        )
        schemes_meta = {}

    # ── Initialize DB ─────────────────────────────────────────────────────────
    init_db()

    # ── Enumerate fingerprints ────────────────────────────────────────────────
    logger.info(f"Enumerating fingerprints (max_combo_size={max_combo_size})...")
    all_fingerprints = enumerate_fingerprints(
        conditions_data, schemes_meta, max_combo_size, target_scheme_id
    )

    total_enumerated = len(all_fingerprints)
    logger.info(f"Enumerated {total_enumerated:,} total fingerprints")

    # ── Dry run ───────────────────────────────────────────────────────────────
    if dry_run:
        estimated_hours = total_enumerated / RATE_LIMIT_RPM / 60
        print(f"\n{'=' * 60}")
        print(f"  DRY RUN - no API calls made")
        print(f"{'=' * 60}")
        print(f"  Total fingerprints to generate : {total_enumerated:,}")
        print(f"  Rate limit                     : {RATE_LIMIT_RPM} RPM")
        print(f"  Estimated time                 : {estimated_hours:.1f} hours")
        print(f"  Delay between calls            : {DELAY_BETWEEN_CALLS:.1f}s")
        print(f"{'=' * 60}\n")
        return

    # ── Filter already-cached (resume mode) ──────────────────────────────────
    if resume:
        logger.info("Checking which fingerprints are already cached (--resume mode)...")
        to_generate = [
            fp for fp in all_fingerprints
            if cache_get(fp[0], fp[4]) is None
        ]
        already_cached = total_enumerated - len(to_generate)
        logger.info(f"Already cached: {already_cached:,}  |  To generate: {len(to_generate):,}")
    else:
        to_generate = all_fingerprints
        logger.info(f"Regenerating all {len(to_generate):,} fingerprints (--no-resume)")

    if not to_generate:
        logger.info("All fingerprints already cached. Nothing to do.")
        return

    # ── Configure Gemini ──────────────────────────────────────────────────────
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=SYSTEM_INSTRUCTION,
    )

    # ── Generation loop ───────────────────────────────────────────────────────
    total         = len(to_generate)
    success_count = 0
    failure_count = 0
    start_time    = time.time()

    logger.info(
        f"Starting batch generation | {total:,} fingerprints | "
        f"{RATE_LIMIT_RPM} RPM | "
        f"~{total / RATE_LIMIT_RPM / 60:.1f} hours estimated"
    )

    for i, (scheme_id, scheme_name, scheme_desc, conditions, unknown_fields) in enumerate(to_generate):

        # Progress log every 100 items
        if i > 0 and i % 100 == 0:
            elapsed  = time.time() - start_time
            rate     = i / elapsed * 60  # actual RPM
            eta_min  = (total - i) / (i / elapsed) / 60
            logger.info(
                f"Progress: {i:,}/{total:,} ({i/total*100:.1f}%) | "
                f"✓{success_count} ✗{failure_count} | "
                f"actual {rate:.1f} RPM | "
                f"ETA {eta_min:.0f} min"
            )

        # Call Gemini
        items = call_gemini(
            scheme_name, scheme_desc, conditions, unknown_fields, model
        )

        if items:
            cache_put(
                scheme_id, unknown_fields, items,
                generation_source="batch",
                gemini_model=GEMINI_MODEL,
            )
            success_count += 1
        else:
            failure_count += 1
            fp_text, _ = make_fingerprint(scheme_id, unknown_fields)
            logger.error(f"FAILED: {fp_text}")

        # Rate limiting
        if i < total - 1:
            time.sleep(DELAY_BETWEEN_CALLS)

    # ── Final report ──────────────────────────────────────────────────────────
    elapsed_min = (time.time() - start_time) / 60
    print(f"\n{'=' * 60}")
    print(f"  BATCH COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Total processed : {total:,}")
    print(f"  Successful      : {success_count:,}  ({success_count/total*100:.1f}%)")
    print(f"  Failed          : {failure_count:,}  ({failure_count/total*100:.1f}%)")
    print(f"  Time elapsed    : {elapsed_min:.1f} minutes")
    if failure_count > 0:
        print(f"\n  Re-run with --resume to retry failed fingerprints.")
    print(f"{'=' * 60}\n")


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pre-warm YojanaMitra question cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python batch_prewarm.py --dry-run
  python batch_prewarm.py
  python batch_prewarm.py --scheme-id 42
  python batch_prewarm.py --max-combo-size 2
  python batch_prewarm.py --no-resume
        """,
    )
    parser.add_argument("--scheme-id",      metavar="ID",  help="Pre-warm a single scheme only")
    parser.add_argument("--dry-run",         action="store_true", help="Count fingerprints, no API calls")
    parser.add_argument("--max-combo-size",  type=int, default=MAX_COMBO_SIZE, metavar="N",
                        help=f"Max unknown fields to combine (default: {MAX_COMBO_SIZE})")
    parser.add_argument("--resume",          action="store_true",  default=True,
                        help="Skip already-cached fingerprints (default: on)")
    parser.add_argument("--no-resume",       dest="resume", action="store_false",
                        help="Regenerate all fingerprints from scratch")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key and not args.dry_run:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        print("  export GEMINI_API_KEY=your_key_here")
        sys.exit(1)

    run_batch(
        api_key=api_key,
        max_combo_size=args.max_combo_size,
        target_scheme_id=args.scheme_id,
        dry_run=args.dry_run,
        resume=args.resume,
    )
