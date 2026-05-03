"""
profile_vs_gemini_audit_v2.py
==============================
Phase 1 — AUDIT:
  Sends your profile to Gemini alongside each scheme's eligibility text and
  gets a direct YES/NO verdict. Compares that against the deterministic engine.

Phase 2 — CONDITION SYNTHESIS (NEW):
  Uses Gemini's reasoning output (key_conditions_checked) across ALL audited
  schemes to learn and emit a machine-readable condition schema that perfectly
  mirrors Gemini's intelligence. Outputs:
    synthesized_conditions.json   — per-scheme structured conditions extracted
                                    from Gemini's verdicts
    condition_patterns.json       — cross-scheme patterns: what conditions appear
                                    most often, canonical field names, value ranges
    engine_patches.json           — exact patches to fix false positives/negatives
                                    in your deterministic engine
    audit_report.json             — full structured results (unchanged)
    false_positives.json          — only FP cases with Gemini's explanation
    audit_summary.txt             — human-readable summary

Usage:
  # Audit engine-matched schemes + synthesize conditions
  python profile_vs_gemini_audit_v2.py

  # Audit ALL 4324 schemes (slow — ~2 hrs, use --resume)
  python profile_vs_gemini_audit_v2.py --all-schemes --resume

  # Only run Phase 2 synthesis on an existing audit_report.json
  python profile_vs_gemini_audit_v2.py --synthesize-only

  # Single scheme debug (includes condition extraction)
  python profile_vs_gemini_audit_v2.py --scheme-id 239

  # Custom profile
  python profile_vs_gemini_audit_v2.py --profile my_profile.json
"""

import json
import time
import os
import re
import argparse
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ── Gemini setup ──────────────────────────────────────────────────────────────
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "PASTE_YOUR_GEMINI_API_KEY_HERE")
genai.configure(api_key=GEMINI_API_KEY)
MODEL = genai.GenerativeModel("gemini-flash-latest")

SCHEMES_JSON            = "all_schemes_export.json"
OUTPUT_JSON             = "audit_report.json"
FP_JSON                 = "false_positives.json"
SUMMARY_TXT             = "audit_summary.txt"
SYNTHESIZED_JSON        = "synthesized_conditions.json"
PATTERNS_JSON           = "condition_patterns.json"
ENGINE_PATCHES_JSON     = "engine_patches.json"
REQUESTS_PER_MIN        = 45
DELAY                   = 60.0 / REQUESTS_PER_MIN

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("audit")


# ─────────────────────────────────────────────────────────────────────────────
#  PHASE 1 PROMPTS — Audit (eligibility verdict)
# ─────────────────────────────────────────────────────────────────────────────

AUDIT_SYSTEM_PROMPT = """You are an expert evaluator for Indian government scheme eligibility.
You will be given:
1. A user's profile with their actual demographic and socioeconomic data
2. A scheme's eligibility criteria text

Your job: Determine if this specific user is eligible for this scheme.

RULES:
- Base your decision ONLY on what the eligibility text explicitly states
- If a requirement is not mentioned in the text, assume the user qualifies for that aspect
- If the text is for institutions/organizations (not individuals), output: NOT_ELIGIBLE with reason "Institutional scheme"
- Be strict: if the user clearly fails any stated requirement, output NOT_ELIGIBLE
- Be fair: if the text is vague or the requirement is unclear, give benefit of doubt → ELIGIBLE

OUTPUT FORMAT (JSON only, no explanation outside JSON):
{
  "verdict": "ELIGIBLE" or "NOT_ELIGIBLE",
  "confidence": 0.0-1.0,
  "key_conditions_checked": [
    {"condition": "<what was checked>", "user_value": "<user's value>", "required": "<what scheme needs>", "pass": true/false}
  ],
  "blocking_reason": "<if NOT_ELIGIBLE: the specific reason why>",
  "notes": "<any important observations>"
}"""


# ─────────────────────────────────────────────────────────────────────────────
#  PHASE 2 PROMPTS — Condition Extraction (NEW)
# ─────────────────────────────────────────────────────────────────────────────

EXTRACTION_SYSTEM_PROMPT = """You are an expert at converting Indian government scheme eligibility text into
structured machine-readable condition schemas for a deterministic eligibility engine.

You will be given:
1. A scheme's raw eligibility text
2. Gemini's audit result showing which conditions were checked, how they were interpreted,
   and the final verdict for a real user

Your job: Extract the COMPLETE set of eligibility conditions as a structured schema,
informed by how Gemini actually interpreted the text.

FIELD NAME CONVENTIONS (use these exact keys for the profile fields):
  age, gender, state, residence (urban/rural), caste_category (general/OBC/SC/ST),
  social_category, annual_family_income, is_student, is_farmer, is_bpl, is_disabled,
  disability_percentage, is_widow, is_minority, is_tribal, is_senior_citizen,
  is_orphan, is_pregnant, is_govt_employee, is_ex_serviceman, marital_status,
  occupation_type, employment_status, education_level, land_size_acres,
  num_children, num_daughters, religion, years_in_state, exam_percentage

CONDITION TYPES:
  range       — numeric field with min/max (use null for open-ended)
  enum        — must be one of a set of values
  boolean     — must be true/false
  not_enum    — must NOT be one of a set of values
  multi_caste — eligibility based on caste/social category list

OUTPUT FORMAT (JSON only, no explanation outside JSON):
{
  "scheme_id": <int>,
  "scheme_name": "<string>",
  "is_institutional": false,
  "gemini_verdict": "ELIGIBLE" | "NOT_ELIGIBLE",
  "conditions": [
    {
      "field": "<profile field name>",
      "type": "range" | "enum" | "boolean" | "not_enum" | "multi_caste",
      "operator": "AND" | "OR",
      "values": <array or null>,
      "min": <number or null>,
      "max": <number or null>,
      "required": true | false,
      "source_text": "<verbatim snippet from eligibility text that drives this condition>",
      "confidence": 0.0-1.0,
      "gemini_interpreted_as": "<how Gemini read this condition>",
      "engine_missed": true | false
    }
  ],
  "implicit_conditions": [
    "<conditions Gemini applied that were NOT in the eligibility text>"
  ],
  "ambiguities": [
    "<parts of the eligibility text that are vague or could be interpreted multiple ways>"
  ],
  "extraction_confidence": 0.0-1.0
}"""


def build_audit_prompt(profile: dict, scheme: dict) -> str:
    profile_lines = [f"  {k}: {v}" for k, v in profile.items()
                     if v is not None and v != "" and v != [] and v != {}]
    profile_str = "\n".join(profile_lines)

    elig = (scheme.get("eligibility") or "").strip()
    if not elig:
        elig = (scheme.get("description") or "")[:500]

    return f"""USER PROFILE:
{profile_str}

SCHEME: {scheme.get('name', '')}
CATEGORY: {scheme.get('category', '')}

ELIGIBILITY CRITERIA:
{elig[:2500]}

Is this user eligible? Output JSON only."""


def build_extraction_prompt(scheme: dict, gemini_audit: dict) -> str:
    elig = (scheme.get("eligibility") or "").strip()
    if not elig:
        elig = (scheme.get("description") or "")[:500]

    audit_summary = {
        "verdict": gemini_audit.get("verdict"),
        "confidence": gemini_audit.get("confidence"),
        "key_conditions_checked": gemini_audit.get("key_conditions_checked", []),
        "blocking_reason": gemini_audit.get("blocking_reason", ""),
        "notes": gemini_audit.get("notes", "")
    }

    return f"""SCHEME ID: {scheme.get('id')}
SCHEME NAME: {scheme.get('name', '')}
CATEGORY: {scheme.get('category', '')}

ELIGIBILITY TEXT:
{elig[:3000]}

GEMINI AUDIT RESULT (how Gemini interpreted this text for a real user):
{json.dumps(audit_summary, indent=2)}

Extract the complete condition schema. Output JSON only."""


# ─────────────────────────────────────────────────────────────────────────────
#  Gemini callers
# ─────────────────────────────────────────────────────────────────────────────

def call_gemini_audit(profile: dict, scheme: dict, retries: int = 3) -> dict:
    """Phase 1: Get eligibility verdict."""
    user_prompt = build_audit_prompt(profile, scheme)
    return _call_gemini(AUDIT_SYSTEM_PROMPT, user_prompt, retries)


def call_gemini_extraction(scheme: dict, gemini_audit: dict, retries: int = 3) -> dict:
    """Phase 2: Extract structured conditions from eligibility text + audit insight."""
    user_prompt = build_extraction_prompt(scheme, gemini_audit)
    return _call_gemini(EXTRACTION_SYSTEM_PROMPT, user_prompt, retries)


def _call_gemini(system_prompt: str, user_prompt: str, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            response = MODEL.generate_content(
                [system_prompt, user_prompt],
                generation_config=genai.GenerationConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                )
            )
            raw = response.text.strip()
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            return json.loads(raw)

        except json.JSONDecodeError:
            log.warning(f"JSON parse error attempt {attempt + 1}")
            if attempt == retries - 1:
                return {"error": "JSON parse failed"}

        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower():
                wait = (2 ** attempt) * 30
                log.warning(f"Rate limit. Waiting {wait}s...")
                time.sleep(wait)
            else:
                log.error(f"Gemini error: {e}")
                return {"error": str(e)}

    return {"error": "Max retries exceeded"}


# ─────────────────────────────────────────────────────────────────────────────
#  Engine runner
# ─────────────────────────────────────────────────────────────────────────────

def get_engine_results(profile_raw: dict, schemes: list) -> dict:
    try:
        import sys
        sys.path.insert(0, ".")
        from eligibility_engine_strict_v21 import StrictEligibilityEngine as EligibilityEngine, UserProfile
        from scheme_rule_adapter import build_rule

        # Re-use the engine's expected UserProfile instead of legacy Normalizer
        user = UserProfile(
            user_id=profile_raw.get("email") or profile_raw.get("user_id") or "test@example.com",
            age=int(profile_raw.get("age", 0)),
            gender=(profile_raw.get("gender") or "male").lower(),
            state=profile_raw.get("state") or "KA",
            income_annual=int(profile_raw.get("annual_family_income") or profile_raw.get("income", 0)),
            occupation=[profile_raw.get("occupation")] if profile_raw.get("occupation") else [],
            caste_category=(profile_raw.get("caste_category") or "general").lower(),
            is_student=profile_raw.get("is_student") == "Yes",
            is_farmer=profile_raw.get("is_farmer") == "Yes",
            is_disabled=profile_raw.get("is_disabled") == "Yes",
            is_widow=profile_raw.get("is_widow") == "Yes",
            is_minority=profile_raw.get("is_minority") == "Yes",
            is_senior_citizen=profile_raw.get("is_senior_citizen") == "Yes"
        )
        engine = EligibilityEngine()

        results = {}
        for s in schemes:
            class Obj: pass
            obj = Obj()
            for k, v in s.items():
                setattr(obj, k, v)
            obj.disability_percentage_min = getattr(obj, 'disability_percentage_min', None)
            try:
                rule = build_rule(obj)
                if rule is None:
                    results[s['id']] = {'class': 'FILTERED', 'score': 0, 'rejection': 'build_rule filtered'}
                    continue
                r = engine.evaluate(user, rule)
                results[s['id']] = {
                    'class': r.eligibility_class.value,
                    'score': r.confidence_score,
                    'rejection': r.rejection_detail or '',
                    'rejection_code': r.rejection_code.value if r.rejection_code else ''
                }
            except Exception as e:
                results[s['id']] = {'class': 'ERROR', 'score': 0, 'rejection': str(e)}

        return results

    except ImportError as e:
        log.warning(f"Could not load engine: {e}. Skipping deterministic results.")
        return {}


# ─────────────────────────────────────────────────────────────────────────────
#  Profile loader
# ─────────────────────────────────────────────────────────────────────────────

def load_profile(profile_path: str = None) -> dict:
    if profile_path and Path(profile_path).exists():
        with open(profile_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("profile", data)

    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:5000/api/user", timeout=3) as resp:
            data = json.loads(resp.read())
            profile = data.get("user", {})
            p = profile.get("profile", {})
            merged = {
                "name": profile.get("name"),
                "age": p.get("age"),
                "gender": p.get("gender"),
                "date_of_birth": profile.get("dob"),
                "state": p.get("state"),
                "district": p.get("district"),
                "residence": p.get("residence"),
                "annual_family_income": p.get("annualFamilyIncome"),
                "income": p.get("income"),
                "caste_category": p.get("caste"),
                "social_category": p.get("socialCategory"),
                "marital_status": p.get("maritalStatus"),
                "occupation": p.get("occupation"),
                "employment_status": p.get("employmentStatus"),
                "occupation_type": p.get("occupationType"),
                "is_farmer": p.get("isFarmer"),
                "land_size_acres": p.get("landSizeAcres"),
                "disability": p.get("disability"),
                "disability_percentage": p.get("disabilityPercentage"),
                "is_bpl": p.get("isBpl") or p.get("rationCardType") == "BPL",
                "education_level": p.get("highestEducationLevel"),
                "is_student": p.get("educationStatus") == "Studying",
                "is_widow": p.get("isWidowSingleWoman") == "Yes",
                "is_minority": p.get("minorityStatus") == "Yes",
                "is_tribal": p.get("isTribal") == "Yes",
                "is_orphan": p.get("isOrphan") == "Yes",
                "is_senior_citizen": p.get("isSeniorCitizen") == "Yes",
                "is_govt_employee": p.get("govtEmployeeInFamily") == "Yes",
                "religion": p.get("religion"),
                "num_children": p.get("numChildren"),
                "years_in_state": p.get("yearsInCurrentState"),
                "is_ex_serviceman": p.get("isExServiceman"),
                "is_shg_member": p.get("isShgMember"),
                "has_critical_illness": p.get("hasCriticalIllness"),
                "is_pregnant": p.get("isPregnant"),
            }
            return {k: v for k, v in merged.items() if v is not None and v != ""}
    except Exception:
        pass

    log.warning("Could not auto-load profile. Using MANUAL_PROFILE.")
    return MANUAL_PROFILE


MANUAL_PROFILE = {
    "user_id": "shreyas6504@gmail.com",
    "email": "shreyas6504@gmail.com",
    "name": "Shreyas",
    "age": 21,
    "gender": "Male",
    "state": "KA",
    "district": "Davanagere",
    "residence": "rural",
    "caste_category": "general",
    "social_category": "General",
    "marital_status": "Single",
    "employment_status": "Student",
    "occupation_type": "Other",
    "annual_family_income": 800000,
    "has_bank_account": "Yes",
    "is_bpl": "No",
    "is_student": "Yes",
    "is_farmer": "No",
    "is_disabled": "No",
    "is_minority": "No",
    "is_widow": "No",
    "is_senior_citizen": "No",
    "is_govt_employee": "No",
    "is_migrant_worker": "No",
    "has_tractor": "No",
    "has_kcc": "No",
    "is_pregnant": "No",
    "is_orphan": "No",
    "num_children": 0,
    "num_daughters": 0,
    "num_sons": 0,
    "exam_percentage": 7.2
}


# ─────────────────────────────────────────────────────────────────────────────
#  PHASE 1: Audit runner
# ─────────────────────────────────────────────────────────────────────────────

def run_audit(
    profile: dict,
    schemes_to_check: list,
    all_schemes: list,
    engine_results: dict,
    resume: bool = False,
    output_file: str = OUTPUT_JSON
) -> tuple[dict, dict]:

    existing = {}
    if resume and Path(output_file).exists():
        with open(output_file, encoding="utf-8") as f:
            existing = json.load(f)
        log.info(f"Resuming: {len(existing)} schemes already audited")

    to_check = [s for s in schemes_to_check if str(s['id']) not in existing]
    log.info(f"[Phase 1] Auditing {len(to_check)} schemes via Gemini...")

    results = dict(existing)
    last_call = 0.0
    stats = {"fp": 0, "fn": 0, "agree_eligible": 0, "agree_not": 0, "error": 0, "skipped": len(existing)}

    for i, scheme in enumerate(to_check):
        sid = str(scheme['id'])
        eng = engine_results.get(scheme['id'], {})
        eng_class = eng.get('class', 'UNKNOWN')

        elapsed = time.time() - last_call
        if elapsed < DELAY:
            time.sleep(DELAY - elapsed)

        log.info(f"[{i+1}/{len(to_check)}] [{sid}] {scheme.get('name','')[:55]} | engine={eng_class}")

        gemini = call_gemini_audit(profile, scheme)
        last_call = time.time()

        gem_verdict = gemini.get("verdict", "ERROR")

        engine_eligible = eng_class in ("FULLY_ELIGIBLE", "POSSIBLY_ELIGIBLE")
        gemini_eligible = gem_verdict == "ELIGIBLE"

        if gem_verdict == "ERROR" or "error" in gemini:
            comparison = "ERROR"
            stats["error"] += 1
        elif engine_eligible and not gemini_eligible:
            comparison = "FALSE_POSITIVE"
            stats["fp"] += 1
        elif not engine_eligible and gemini_eligible:
            comparison = "FALSE_NEGATIVE"
            stats["fn"] += 1
        elif engine_eligible and gemini_eligible:
            comparison = "AGREE_ELIGIBLE"
            stats["agree_eligible"] += 1
        else:
            comparison = "AGREE_NOT_ELIGIBLE"
            stats["agree_not"] += 1

        results[sid] = {
            "scheme_id": scheme['id'],
            "scheme_name": scheme.get('name', ''),
            "category": scheme.get('category', ''),
            "eligibility_text": (scheme.get("eligibility") or "")[:1000],
            "engine": {
                "class": eng_class,
                "score": eng.get('score', 0),
                "rejection": eng.get('rejection', ''),
                "rejection_code": eng.get('rejection_code', '')
            },
            "gemini": {
                "verdict": gem_verdict,
                "confidence": gemini.get("confidence", 0),
                "blocking_reason": gemini.get("blocking_reason", ""),
                "conditions_checked": gemini.get("key_conditions_checked", []),
                "notes": gemini.get("notes", "")
            },
            "comparison": comparison
        }

        if (i + 1) % 10 == 0:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            log.info(f"  Checkpoint | FP={stats['fp']} FN={stats['fn']} AGREE={stats['agree_eligible']+stats['agree_not']}")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results, stats


# ─────────────────────────────────────────────────────────────────────────────
#  PHASE 2: Condition synthesis
# ─────────────────────────────────────────────────────────────────────────────

def synthesize_conditions(
    audit_results: dict,
    all_schemes: list,
    resume: bool = False
) -> tuple[dict, dict, dict]:
    """
    For every audited scheme, run Gemini's extraction prompt to turn the raw
    eligibility text + audit insight into a machine-readable condition schema.

    Returns:
        synthesized    — {scheme_id: condition_schema}
        patterns       — cross-scheme patterns (field frequency, canonical values)
        engine_patches — exact diffs to fix the deterministic engine
    """
    scheme_map = {str(s['id']): s for s in all_schemes}

    # Load existing synthesis if resuming
    existing_synth = {}
    if resume and Path(SYNTHESIZED_JSON).exists():
        with open(SYNTHESIZED_JSON, encoding="utf-8") as f:
            existing_synth = json.load(f)
        log.info(f"[Phase 2] Resuming synthesis: {len(existing_synth)} already done")

    synthesized = dict(existing_synth)
    last_call = 0.0

    # Only synthesize schemes where audit gave us real Gemini conditions
    to_synthesize = [
        (sid, result) for sid, result in audit_results.items()
        if sid not in synthesized
        and result.get("comparison") not in ("ERROR",)
        and result.get("gemini", {}).get("verdict") in ("ELIGIBLE", "NOT_ELIGIBLE")
    ]

    log.info(f"[Phase 2] Extracting conditions from {len(to_synthesize)} schemes...")

    for i, (sid, result) in enumerate(to_synthesize):
        scheme = scheme_map.get(sid)
        if not scheme:
            continue

        gemini_audit = result.get("gemini", {})
        elapsed = time.time() - last_call
        if elapsed < DELAY:
            time.sleep(DELAY - elapsed)

        log.info(f"  Extracting [{i+1}/{len(to_synthesize)}] [{sid}] {result.get('scheme_name','')[:50]}")

        extraction = call_gemini_extraction(scheme, gemini_audit)
        last_call = time.time()

        if "error" not in extraction:
            # Annotate whether this scheme had engine disagreement
            extraction["engine_comparison"] = result.get("comparison")
            extraction["engine_class"] = result["engine"]["class"]
            extraction["engine_rejection"] = result["engine"]["rejection"]
            synthesized[sid] = extraction
        else:
            log.warning(f"  Extraction failed for {sid}: {extraction.get('error')}")

        if (i + 1) % 10 == 0:
            with open(SYNTHESIZED_JSON, "w", encoding="utf-8") as f:
                json.dump(synthesized, f, ensure_ascii=False, indent=2)
            log.info(f"  Synthesis checkpoint: {len(synthesized)} done")

    # Save final synthesis
    with open(SYNTHESIZED_JSON, "w", encoding="utf-8") as f:
        json.dump(synthesized, f, ensure_ascii=False, indent=2)

    # Build cross-scheme patterns
    patterns = _build_patterns(synthesized)

    # Build engine patches for FP/FN cases
    engine_patches = _build_engine_patches(synthesized, audit_results)

    return synthesized, patterns, engine_patches


def _build_patterns(synthesized: dict) -> dict:
    """
    Cross-scheme analysis: which fields appear most often, what values are common,
    which conditions are most frequently missed by the engine.
    """
    field_freq: dict[str, int] = defaultdict(int)
    field_types: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    field_values: dict[str, list] = defaultdict(list)
    missed_fields: dict[str, int] = defaultdict(int)   # engine_missed=true
    caste_groups: list[str] = []
    ambiguities: list[str] = []

    for sid, schema in synthesized.items():
        for cond in schema.get("conditions", []):
            field = cond.get("field", "unknown")
            field_freq[field] += 1
            ctype = cond.get("type", "unknown")
            field_types[field][ctype] += 1

            if cond.get("values"):
                field_values[field].extend(cond["values"])

            if cond.get("min") is not None:
                field_values[f"{field}__min"].append(cond["min"])
            if cond.get("max") is not None:
                field_values[f"{field}__max"].append(cond["max"])

            if cond.get("engine_missed"):
                missed_fields[field] += 1

            if field == "caste_category" and cond.get("values"):
                caste_groups.extend(cond["values"])

        ambiguities.extend(schema.get("ambiguities", []))

    # Summarize
    def top_values(vals: list, n=10) -> list:
        from collections import Counter
        return [v for v, _ in Counter(vals).most_common(n)]

    patterns = {
        "generated_at": datetime.now().isoformat(),
        "total_schemes_analyzed": len(synthesized),
        "field_frequency": dict(sorted(field_freq.items(), key=lambda x: -x[1])),
        "field_type_distribution": {
            field: dict(types) for field, types in field_types.items()
        },
        "common_field_values": {
            field: top_values(vals)
            for field, vals in field_values.items()
            if not field.endswith("__min") and not field.endswith("__max")
        },
        "numeric_ranges": {
            field.replace("__min", "").replace("__max", ""): {
                "observed_mins": sorted(set(field_values.get(f"{field}__min", []))),
                "observed_maxs": sorted(set(field_values.get(f"{field}__max", [])))
            }
            for field in field_freq
            if field_values.get(f"{field}__min") or field_values.get(f"{field}__max")
        },
        "engine_most_missed_fields": dict(sorted(missed_fields.items(), key=lambda x: -x[1])),
        "common_caste_groups": top_values(caste_groups),
        "sample_ambiguities": list(set(ambiguities))[:30],
    }

    with open(PATTERNS_JSON, "w", encoding="utf-8") as f:
        json.dump(patterns, f, ensure_ascii=False, indent=2)

    return patterns


def _build_engine_patches(synthesized: dict, audit_results: dict) -> dict:
    """
    For each FALSE_POSITIVE and FALSE_NEGATIVE, produce a concrete patch
    description: what conditions the engine needs to add, tighten, or relax.
    """
    patches = {
        "generated_at": datetime.now().isoformat(),
        "false_positive_patches": [],
        "false_negative_patches": [],
        "summary": {}
    }

    for sid, schema in synthesized.items():
        comparison = schema.get("engine_comparison")
        if comparison not in ("FALSE_POSITIVE", "FALSE_NEGATIVE"):
            continue

        audit = audit_results.get(sid, {})
        failed_conditions = [
            c for c in schema.get("conditions", [])
            if c.get("engine_missed")
        ]
        gemini_conditions = audit.get("gemini", {}).get("conditions_checked", [])
        failed_gemini = [c for c in gemini_conditions if not c.get("pass", True)]

        patch = {
            "scheme_id": schema.get("scheme_id"),
            "scheme_name": schema.get("scheme_name"),
            "engine_class": schema.get("engine_class"),
            "engine_rejection": schema.get("engine_rejection"),
            "gemini_verdict": schema.get("gemini_verdict"),
            "problem": (
                "Engine passes user but Gemini rejects — engine is missing/too-loose conditions"
                if comparison == "FALSE_POSITIVE"
                else "Engine rejects user but Gemini passes — engine has wrong/too-strict conditions"
            ),
            "conditions_to_add_or_fix": failed_conditions,
            "gemini_failed_checks": failed_gemini,
            "recommended_action": _recommend_patch_action(comparison, failed_conditions, failed_gemini, schema),
        }

        if comparison == "FALSE_POSITIVE":
            patches["false_positive_patches"].append(patch)
        else:
            patches["false_negative_patches"].append(patch)

    patches["summary"] = {
        "false_positive_patches": len(patches["false_positive_patches"]),
        "false_negative_patches": len(patches["false_negative_patches"]),
        "total_patches": len(patches["false_positive_patches"]) + len(patches["false_negative_patches"])
    }

    with open(ENGINE_PATCHES_JSON, "w", encoding="utf-8") as f:
        json.dump(patches, f, ensure_ascii=False, indent=2)

    return patches


def _recommend_patch_action(
    comparison: str,
    missed_conditions: list,
    gemini_failed: list,
    schema: dict
) -> str:
    """Generate a plain-English patch instruction for each disagreement."""
    lines = []

    if comparison == "FALSE_POSITIVE":
        lines.append("ADD or TIGHTEN the following conditions to prevent incorrect matches:")
        for c in missed_conditions:
            field = c.get("field", "?")
            ctype = c.get("type")
            if ctype == "range":
                lines.append(f"  • {field}: enforce range [{c.get('min','?')} – {c.get('max','?')}]")
            elif ctype in ("enum", "multi_caste"):
                lines.append(f"  • {field}: restrict to values {c.get('values')}")
            elif ctype == "boolean":
                lines.append(f"  • {field}: must be {c.get('values', [True])[0] if c.get('values') else 'true'}")
            elif ctype == "not_enum":
                lines.append(f"  • {field}: must NOT be in {c.get('values')}")
            else:
                lines.append(f"  • {field}: review condition '{c.get('source_text','')[:100]}'")

        for c in gemini_failed:
            lines.append(f"  • [{c.get('condition','')}]: user has '{c.get('user_value','')}', scheme needs '{c.get('required','')}'")

    else:  # FALSE_NEGATIVE
        lines.append("RELAX or REMOVE overly strict conditions that block eligible users:")
        eng_rej = schema.get("engine_rejection", "")
        if eng_rej:
            lines.append(f"  • Engine rejected because: {eng_rej[:120]}")
        lines.append("  • Review whether the blocking condition exists in the raw eligibility text.")
        lines.append("  • If not found verbatim, remove or downgrade to SOFT condition.")

    return "\n".join(lines) if lines else "Manual review required."


# ─────────────────────────────────────────────────────────────────────────────
#  Report writers
# ─────────────────────────────────────────────────────────────────────────────

def write_reports(results: dict, stats: dict, profile: dict, patterns: dict, patches: dict):
    # ── false_positives.json ──────────────────────────────────────────────────
    fps = [v for v in results.values() if v["comparison"] == "FALSE_POSITIVE"]
    fps.sort(key=lambda x: x["gemini"]["confidence"], reverse=True)

    with open(FP_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "total_false_positives": len(fps),
            "profile_summary": {k: v for k, v in profile.items() if k in
                ("name","age","gender","state","caste_category","social_category",
                 "annual_family_income","residence","is_student","is_farmer")},
            "false_positives": [
                {
                    "scheme_id": fp["scheme_id"],
                    "scheme_name": fp["scheme_name"],
                    "category": fp["category"],
                    "engine_score": fp["engine"]["score"],
                    "engine_class": fp["engine"]["class"],
                    "gemini_confidence": fp["gemini"]["confidence"],
                    "why_not_eligible": fp["gemini"]["blocking_reason"],
                    "conditions_that_failed": [
                        c for c in fp["gemini"]["conditions_checked"] if not c.get("pass", True)
                    ]
                }
                for fp in fps
            ]
        }, f, ensure_ascii=False, indent=2)

    # ── audit_summary.txt ─────────────────────────────────────────────────────
    total = sum(stats[k] for k in ("fp","fn","agree_eligible","agree_not","error"))
    fp_rate = stats['fp'] / (stats['fp'] + stats['agree_eligible']) * 100 if (stats['fp'] + stats['agree_eligible']) > 0 else 0

    with open(SUMMARY_TXT, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("  YOJANAMITRA PROFILE AUDIT — DETERMINISTIC vs GEMINI  (v2)\n")
        f.write(f"  Run: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 70 + "\n\n")

        f.write("PROFILE:\n")
        for k, v in profile.items():
            if v is not None and v != "":
                f.write(f"  {k}: {v}\n")

        f.write(f"\nSCHEMES AUDITED: {total}\n\n")
        f.write(f"  FALSE POSITIVES  (engine eligible, Gemini says NO): {stats['fp']}\n")
        f.write(f"  FALSE NEGATIVES  (engine not eligible, Gemini YES): {stats['fn']}\n")
        f.write(f"  AGREE ELIGIBLE:                                      {stats['agree_eligible']}\n")
        f.write(f"  AGREE NOT ELIGIBLE:                                  {stats['agree_not']}\n")
        f.write(f"  ERRORS:                                              {stats['error']}\n")
        f.write(f"\n  FALSE POSITIVE RATE (of engine matches): {fp_rate:.1f}%\n")

        # ── Phase 2 summary ──────────────────────────────────────────────────
        f.write(f"\n{'═'*70}\n")
        f.write(f"  PHASE 2 — CONDITION SYNTHESIS SUMMARY\n")
        f.write(f"{'═'*70}\n\n")
        f.write(f"  Engine patches generated: {patches['summary'].get('total_patches', 0)}\n")
        f.write(f"    • False Positive fixes:  {patches['summary'].get('false_positive_patches', 0)}\n")
        f.write(f"    • False Negative fixes:  {patches['summary'].get('false_negative_patches', 0)}\n\n")

        if patterns:
            top_fields = list(patterns.get("field_frequency", {}).items())[:10]
            f.write("  Top 10 most common eligibility fields:\n")
            for field, count in top_fields:
                missed = patterns.get("engine_most_missed_fields", {}).get(field, 0)
                f.write(f"    {field:<30} appears in {count} schemes  (engine missed {missed}×)\n")

        # ── False Positives detail ────────────────────────────────────────────
        if fps:
            f.write(f"\n{'─'*70}\n")
            f.write(f"FALSE POSITIVES — {len(fps)} schemes engine showed but Gemini rejects:\n")
            f.write(f"{'─'*70}\n\n")
            for fp in fps:
                f.write(f"  [{fp['scheme_id']}] {fp['scheme_name'][:60]}\n")
                f.write(f"    Engine: {fp['engine']['class']} (score {fp['engine']['score']}%)\n")
                f.write(f"    Gemini: NOT ELIGIBLE (confidence {fp['gemini']['confidence']:.0%})\n")
                f.write(f"    Reason: {fp['gemini']['blocking_reason']}\n")
                failed = [c for c in fp['gemini']['conditions_checked'] if not c.get('pass', True)]
                for c in failed:
                    f.write(f"      ✗ {c.get('condition','')}: needed {c.get('required','')}, user has {c.get('user_value','')}\n")
                f.write("\n")

        fns = [v for v in results.values() if v["comparison"] == "FALSE_NEGATIVE"]
        if fns:
            f.write(f"\n{'─'*70}\n")
            f.write(f"FALSE NEGATIVES — {len(fns)} schemes engine missed but Gemini says YES:\n")
            f.write(f"{'─'*70}\n\n")
            for fn in fns[:20]:
                f.write(f"  [{fn['scheme_id']}] {fn['scheme_name'][:60]}\n")
                f.write(f"    Engine: {fn['engine']['class']} — {fn['engine']['rejection'][:80]}\n")
                f.write(f"    Gemini: ELIGIBLE (confidence {fn['gemini']['confidence']:.0%})\n")
                f.write(f"    Notes: {fn['gemini']['notes']}\n\n")

    print(f"\n{'='*70}")
    print(f"  AUDIT + SYNTHESIS COMPLETE")
    print(f"  False Positives:  {stats['fp']}")
    print(f"  False Negatives:  {stats['fn']}")
    print(f"  Agree Eligible:   {stats['agree_eligible']}")
    print(f"  Agree Not:        {stats['agree_not']}")
    print(f"\n  Reports written:")
    print(f"  → {OUTPUT_JSON}           (full audit)")
    print(f"  → {FP_JSON}        (false positive detail)")
    print(f"  → {SYNTHESIZED_JSON}  (per-scheme condition schemas)")
    print(f"  → {PATTERNS_JSON}    (cross-scheme field patterns)")
    print(f"  → {ENGINE_PATCHES_JSON}     (engine fix instructions)")
    print(f"  → {SUMMARY_TXT}         (human-readable summary)")
    print(f"{'='*70}\n")


# ─────────────────────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="YojanaMitra audit v2: compare + synthesize Gemini-quality conditions"
    )
    parser.add_argument("--profile",          default=None,       help="Path to profile JSON")
    parser.add_argument("--scheme-id",        type=int, default=None, help="Debug single scheme ID")
    parser.add_argument("--all-schemes",      action="store_true", help="Audit all schemes (slow)")
    parser.add_argument("--resume",           action="store_true", help="Skip already-audited schemes")
    parser.add_argument("--schemes-file",     default=SCHEMES_JSON)
    parser.add_argument("--output",           default=OUTPUT_JSON)
    parser.add_argument("--synthesize-only",  action="store_true",
                        help="Skip Phase 1 audit, only run Phase 2 on existing audit_report.json")
    parser.add_argument("--skip-synthesis",   action="store_true",
                        help="Run Phase 1 audit only, skip Phase 2 condition synthesis")
    args = parser.parse_args()

    # Load schemes
    with open(args.schemes_file, encoding="utf-8") as f:
        all_schemes = json.load(f)
    log.info(f"Loaded {len(all_schemes)} schemes")

    # Load profile
    profile = load_profile(args.profile)
    log.info(f"Profile: {profile.get('name','?')}, age {profile.get('age','?')}, {profile.get('state','?')}")

    # ── Single scheme debug ───────────────────────────────────────────────────
    if args.scheme_id:
        scheme = next((s for s in all_schemes if s['id'] == args.scheme_id), None)
        if not scheme:
            print(f"Scheme {args.scheme_id} not found")
            exit(1)

        log.info("Running deterministic engine for single scheme...")
        engine_results = get_engine_results(profile, all_schemes)
        eng = engine_results.get(args.scheme_id, {})

        print(f"\n[ENGINE] {scheme['name']}")
        print(f"  Class: {eng.get('class')}  Score: {eng.get('score')}%")
        print(f"  Rejection: {eng.get('rejection','')}")

        print(f"\n[GEMINI AUDIT] Sending to Gemini for eligibility verdict...")
        gemini = call_gemini_audit(profile, scheme)
        print(f"  Verdict: {gemini.get('verdict')}")
        print(f"  Confidence: {gemini.get('confidence',0):.0%}")
        print(f"  Blocking reason: {gemini.get('blocking_reason','')}")
        print(f"  Conditions checked:")
        for c in gemini.get("key_conditions_checked", []):
            status = "✓" if c.get("pass") else "✗"
            print(f"    {status} {c.get('condition','')}: need={c.get('required','')}, have={c.get('user_value','')}")

        time.sleep(DELAY)
        print(f"\n[GEMINI EXTRACTION] Extracting structured conditions...")
        extraction = call_gemini_extraction(scheme, gemini)
        print(json.dumps(extraction, indent=2, ensure_ascii=False))
        exit(0)

    # ── Phase 1: Audit ────────────────────────────────────────────────────────
    if args.synthesize_only:
        log.info("--synthesize-only: loading existing audit results...")
        if not Path(args.output).exists():
            print(f"ERROR: {args.output} not found. Run without --synthesize-only first.")
            exit(1)
        with open(args.output, encoding="utf-8") as f:
            audit_results = json.load(f)
        stats = {"fp": 0, "fn": 0, "agree_eligible": 0, "agree_not": 0, "error": 0, "skipped": 0}
        for v in audit_results.values():
            c = v.get("comparison", "ERROR")
            if c == "FALSE_POSITIVE":     stats["fp"] += 1
            elif c == "FALSE_NEGATIVE":   stats["fn"] += 1
            elif c == "AGREE_ELIGIBLE":   stats["agree_eligible"] += 1
            elif c == "AGREE_NOT_ELIGIBLE": stats["agree_not"] += 1
            else:                         stats["error"] += 1
    else:
        log.info("Running deterministic engine...")
        engine_results = get_engine_results(profile, all_schemes)
        engine_matched = [s for s in all_schemes
                          if engine_results.get(s['id'], {}).get('class') in ('FULLY_ELIGIBLE', 'POSSIBLY_ELIGIBLE')]
        log.info(f"Engine matched: {len(engine_matched)} schemes")

        schemes_to_check = all_schemes if args.all_schemes else engine_matched
        log.info(f"Audit mode: {'ALL' if args.all_schemes else 'engine-matched'} ({len(schemes_to_check)} schemes)")

        audit_results, stats = run_audit(
            profile=profile,
            schemes_to_check=schemes_to_check,
            all_schemes=all_schemes,
            engine_results=engine_results,
            resume=args.resume,
            output_file=args.output
        )

    # ── Phase 2: Condition synthesis ──────────────────────────────────────────
    if args.skip_synthesis:
        log.info("--skip-synthesis: skipping Phase 2.")
        patterns, patches = {}, {"summary": {}}
    else:
        log.info("Starting Phase 2: condition extraction and synthesis...")
        synthesized, patterns, patches = synthesize_conditions(
            audit_results=audit_results,
            all_schemes=all_schemes,
            resume=args.resume
        )
        log.info(f"Phase 2 complete: {len(synthesized)} condition schemas synthesized")

    write_reports(audit_results, stats, profile, patterns, patches)

