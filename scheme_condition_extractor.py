"""
scheme_condition_extractor.py
==============================
Batch job that sends every scheme's eligibility text to Gemini and extracts
structured conditions. Run ONCE. Stores output in scheme_conditions.json.

This replaces the regex-based semantic_rule_injector with AI understanding.
The output feeds ai_condition_evaluator.py which does pure deterministic matching
at query time — zero AI calls when users browse the dashboard.

Usage:
    python scheme_condition_extractor.py                    # process all 4324 schemes
    python scheme_condition_extractor.py --limit 50        # test run on 50 schemes
    python scheme_condition_extractor.py --resume          # skip already-processed
    python scheme_condition_extractor.py --scheme-id 239  # single scheme debug

Output:
    scheme_conditions.json  — {scheme_id: extracted_conditions, ...}
    extraction_log.json     — success/failure/skip counts per run

Rate limits: Gemini Flash allows ~60 RPM free tier. Script automatically
throttles to 45 RPM with exponential backoff on 429s.
"""

import json
import time
import os
import re
import argparse
import logging
from pathlib import Path
from datetime import datetime

# ── Gemini setup ──────────────────────────────────────────────────────────────
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "PASTE_YOUR_GEMINI_API_KEY_HERE")
genai.configure(api_key=GEMINI_API_KEY)
MODEL = genai.GenerativeModel("gemini-flash-latest")

# ── Config ────────────────────────────────────────────────────────────────────
SCHEMES_JSON = "all_schemes_export.json"
OUTPUT_FILE  = "scheme_conditions.json"
LOG_FILE     = "extraction_log.json"
REQUESTS_PER_MINUTE = 45  # stay under 60 RPM free tier limit
MIN_DELAY = 60.0 / REQUESTS_PER_MINUTE  # ~1.33s between calls

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("extractor")

# ── The extraction prompt ─────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert at analyzing Indian government scheme eligibility criteria.
Your job is to extract ALL eligibility conditions from scheme text and map them to a structured JSON format.

You must output ONLY valid JSON — no explanation, no markdown, no code blocks.
If a condition is not mentioned in the text, omit that field entirely.
If a condition is explicitly "any" or "all citizens", omit that field.

IMPORTANT RULES:
1. Only extract what is EXPLICITLY stated in the text. Do not infer or assume.
2. If the text is for INSTITUTIONS (NGOs, companies, colleges) and NOT individuals → set is_institutional_scheme: true and stop.
3. Monetary values: always convert to ANNUAL rupees (multiply monthly × 12).
4. Percentages for income: if "below poverty line" with no number → set is_bpl: true.
5. Education levels map to: none, primary(1-5), secondary(6-10), senior_secondary(11-12), diploma, graduation, postgrad, phd.
6. For caste: only set if EXPLICITLY restricted. ['sc','st','obc','general'] or subsets.
7. Age: extract the number. "60 years or older" = age_min:60. "below 35" = age_max:34.
8. State: only set if scheme is EXPLICITLY restricted to specific state(s). Use full state names.
9. Disqualifiers: conditions that explicitly EXCLUDE someone (e.g. "not receiving pension", "not a govt employee").

OUTPUT FORMAT:
{
  "is_institutional_scheme": false,
  "conditions": {
    "age_min": <int>,
    "age_max": <int>,
    "gender": "<male|female|any>",
    "state": ["<state_name>"],
    "residence": "<rural|urban|any>",
    "religion": "<religion_name>",
    "income_annual_max": <int>,
    "annual_family_income_max": <int>,
    "is_bpl": true,
    "is_income_taxpayer_disqualifies": true,
    "is_farmer": true,
    "land_owned_min_acres": <float>,
    "land_owned_max_acres": <float>,
    "is_govt_employee_disqualifies": true,
    "is_self_employed": true,
    "is_bocw_registered": true,
    "is_migrant_worker": true,
    "caste_category": ["sc","st","obc"],
    "is_minority": true,
    "is_tribal": true,
    "is_disabled": true,
    "disability_percentage_min": <int>,
    "is_widow": true,
    "is_single_woman": true,
    "is_orphan": true,
    "is_senior_citizen": true,
    "is_abandoned_woman": true,
    "is_acid_attack_survivor": true,
    "is_student": true,
    "education_level_min": "<level>",
    "education_level_max": "<level>",
    "is_first_gen_student": true,
    "is_school_dropout": true,
    "is_landless": true,
    "has_pucca_house_disqualifies": true,
    "requires_literary_contribution": true,
    "requires_sports_achievement": true,
    "requires_registered_enterprise": true,
    "requires_ngo_institution": true
  },
  "disqualifiers": [
    {"field": "<field_name>", "description": "<what disqualifies>"}
  ],
  "unmapped_conditions": [
    "<any condition in text that doesn't fit above fields>"
  ],
  "confidence": <0.0-1.0>,
  "notes": "<brief explanation of key conditions>"
}"""

# ── Core extraction function ───────────────────────────────────────────────────

def extract_conditions(scheme: dict, retries: int = 3) -> dict | None:
    """Call Gemini to extract structured conditions from a single scheme."""
    sid = scheme.get("id")
    name = scheme.get("name", "")
    elig = (scheme.get("eligibility") or "").strip()
    desc = (scheme.get("description") or "")[:300]

    if not elig or len(elig) < 20:
        # No eligibility text — mark as unknown
        return {
            "is_institutional_scheme": False,
            "conditions": {},
            "disqualifiers": [],
            "unmapped_conditions": [],
            "confidence": 0.0,
            "notes": "No eligibility text available",
            "_extraction_status": "no_text"
        }

    user_prompt = f"""Scheme Name: {name}

Eligibility Criteria:
{elig[:2000]}

Brief Description:
{desc}

Extract all eligibility conditions as JSON."""

    for attempt in range(retries):
        try:
            response = MODEL.generate_content(
                [SYSTEM_PROMPT, user_prompt],
                generation_config=genai.GenerationConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                )
            )
            raw = response.text.strip()

            # Strip markdown fences if present
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)

            parsed = json.loads(raw)
            parsed["_extraction_status"] = "ok"
            parsed["_scheme_name"] = name
            return parsed

        except json.JSONDecodeError as e:
            log.warning(f"[{sid}] JSON parse error attempt {attempt+1}: {e}")
            if attempt == retries - 1:
                return {"_extraction_status": "parse_error", "_raw": raw[:500], "confidence": 0.0,
                        "conditions": {}, "disqualifiers": [], "unmapped_conditions": []}

        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower():
                wait = (2 ** attempt) * 30  # 30s, 60s, 120s
                log.warning(f"[{sid}] Rate limit. Waiting {wait}s...")
                time.sleep(wait)
            elif "500" in err_str or "503" in err_str:
                wait = 10 * (attempt + 1)
                log.warning(f"[{sid}] Server error attempt {attempt+1}. Waiting {wait}s...")
                time.sleep(wait)
            else:
                log.error(f"[{sid}] Unrecoverable error: {e}")
                return {"_extraction_status": "api_error", "_error": str(e),
                        "confidence": 0.0, "conditions": {}, "disqualifiers": [], "unmapped_conditions": []}

    return {"_extraction_status": "max_retries", "confidence": 0.0,
            "conditions": {}, "disqualifiers": [], "unmapped_conditions": []}


# ── Main batch runner ─────────────────────────────────────────────────────────

def run_batch(schemes: list, output_file: str, resume: bool = False, limit: int = None):
    # Load existing results if resuming
    existing = {}
    if resume and Path(output_file).exists():
        with open(output_file, encoding="utf-8") as f:
            existing = json.load(f)
        log.info(f"Resuming: {len(existing)} schemes already processed")

    # Filter to process
    to_process = [s for s in schemes if str(s["id"]) not in existing]
    if limit:
        to_process = to_process[:limit]

    log.info(f"Processing {len(to_process)} schemes (total: {len(schemes)})")

    results = dict(existing)
    stats = {"ok": 0, "no_text": 0, "parse_error": 0, "api_error": 0, "skipped": len(existing)}
    last_call_time = 0.0

    for i, scheme in enumerate(to_process):
        sid = str(scheme["id"])

        # Rate limiting
        elapsed = time.time() - last_call_time
        if elapsed < MIN_DELAY:
            time.sleep(MIN_DELAY - elapsed)

        log.info(f"[{i+1}/{len(to_process)}] scheme={sid} — {scheme.get('name','')[:50]}")

        extracted = extract_conditions(scheme)
        last_call_time = time.time()

        results[sid] = extracted
        status = extracted.get("_extraction_status", "ok")
        stats[status] = stats.get(status, 0) + 1

        # Save every 10 schemes (crash recovery)
        if (i + 1) % 10 == 0:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            log.info(f"  Checkpoint saved. Stats: {stats}")

    # Final save
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Write log
    log_entry = {
        "run_time": datetime.now().isoformat(),
        "total_schemes": len(schemes),
        "processed_this_run": len(to_process),
        "stats": stats
    }
    logs = []
    if Path(LOG_FILE).exists():
        with open(LOG_FILE, encoding="utf-8") as f:
            logs = json.load(f)
    logs.append(log_entry)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)

    log.info(f"\nDONE. Results: {stats}")
    log.info(f"Output: {output_file}")
    return results


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YojanaMitra Gemini condition extractor")
    parser.add_argument("--limit", type=int, help="Process only N schemes (for testing)")
    parser.add_argument("--resume", action="store_true", help="Skip already-processed schemes")
    parser.add_argument("--scheme-id", type=int, help="Process single scheme by ID (debug)")
    parser.add_argument("--schemes-file", default=SCHEMES_JSON)
    parser.add_argument("--output", default=OUTPUT_FILE)
    args = parser.parse_args()

    with open(args.schemes_file, encoding="utf-8") as f:
        schemes = json.load(f)

    if args.scheme_id:
        # Single scheme debug mode
        scheme = next((s for s in schemes if s["id"] == args.scheme_id), None)
        if not scheme:
            print(f"Scheme {args.scheme_id} not found")
            exit(1)
        result = extract_conditions(scheme)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        run_batch(schemes, args.output, resume=args.resume, limit=args.limit)

