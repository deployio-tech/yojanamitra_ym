"""
profile_vs_gemini_audit.py
===========================
Sends your profile to Gemini alongside each scheme's eligibility text and
gets a direct YES/NO verdict. Compares that against the deterministic engine.

Three categories of disagreement:
  FALSE POSITIVE  — engine says ELIGIBLE, Gemini says NOT ELIGIBLE  (the real problem)
  FALSE NEGATIVE  — engine says NOT ELIGIBLE, Gemini says ELIGIBLE
  AGREEMENT       — both agree

Output:
  audit_report.json          — full structured results
  false_positives.json       — only FP cases with Gemini's explanation
  audit_summary.txt          — human-readable summary

Usage:
  # Run against schemes the engine matched (fast — only checks matched schemes)
  python profile_vs_gemini_audit.py

  # Run against ALL 4324 schemes (slow — ~2 hrs, use --resume)
  python profile_vs_gemini_audit.py --all-schemes --resume

  # Run against a single scheme for debugging
  python profile_vs_gemini_audit.py --scheme-id 239

  # Use a custom profile JSON instead of fetching from /api/user
  python profile_vs_gemini_audit.py --profile my_profile.json
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

SCHEMES_JSON       = "all_schemes_export.json"
OUTPUT_JSON        = "audit_report.json"
FP_JSON            = "false_positives.json"
SUMMARY_TXT        = "audit_summary.txt"
REQUESTS_PER_MIN   = 45
DELAY              = 60.0 / REQUESTS_PER_MIN

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("audit")

# ── The Gemini evaluation prompt ──────────────────────────────────────────────
# Critically: we give Gemini the raw eligibility text + user's actual values.
# It must reason from text, not from structured conditions.

SYSTEM_PROMPT = """You are an expert evaluator for Indian government scheme eligibility.
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


def build_user_prompt(profile: dict, scheme: dict) -> str:
    """Construct the prompt with user data and scheme eligibility text."""
    # Format profile as readable key-value
    profile_lines = []
    for k, v in profile.items():
        if v is not None and v != "" and v != [] and v != {}:
            profile_lines.append(f"  {k}: {v}")
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


def call_gemini(profile: dict, scheme: dict, retries: int = 3) -> dict:
    """Send profile + scheme to Gemini and get eligibility verdict."""
    user_prompt = build_user_prompt(profile, scheme)

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
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            parsed = json.loads(raw)
            return parsed

        except json.JSONDecodeError:
            log.warning(f"JSON parse error attempt {attempt+1}")
            if attempt == retries - 1:
                return {"verdict": "ERROR", "confidence": 0, "blocking_reason": "JSON parse failed", "key_conditions_checked": [], "notes": ""}

        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower():
                wait = (2 ** attempt) * 30
                log.warning(f"Rate limit. Waiting {wait}s...")
                time.sleep(wait)
            else:
                log.error(f"Gemini error: {e}")
                return {"verdict": "ERROR", "confidence": 0, "blocking_reason": str(e), "key_conditions_checked": [], "notes": ""}

    return {"verdict": "ERROR", "confidence": 0, "blocking_reason": "Max retries", "key_conditions_checked": [], "notes": ""}


def get_engine_results(profile_raw: dict, schemes: list) -> dict:
    """Run the deterministic engine and return {scheme_id: result} dict."""
    try:
        import sys
        sys.path.insert(0, ".")
        from yojanamitra_eligibility_engine_v2 import EligibilityEngine, ProfileNormalizer
        from scheme_rule_adapter import build_rule

        normalizer = ProfileNormalizer()
        engine = EligibilityEngine()
        user = normalizer.normalize(profile_raw)

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


def load_profile(profile_path: str = None) -> dict:
    """Load user profile from file or prompt for manual entry."""
    if profile_path and Path(profile_path).exists():
        with open(profile_path, encoding="utf-8") as f:
            data = json.load(f)
        # Handle nested profile key
        return data.get("profile", data)

    # Try fetching from running Flask app
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:5000/api/user", timeout=3) as resp:
            data = json.loads(resp.read())
            profile = data.get("user", {})
            p = profile.get("profile", {})
            # Merge top-level user fields with profile
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

    # Fallback: prompt user for a minimal profile
    log.warning("Could not auto-load profile. Using example profile — edit MANUAL_PROFILE in script.")
    return MANUAL_PROFILE


# ── Edit this for your profile if auto-loading fails ─────────────────────────
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


# ── Main audit runner ─────────────────────────────────────────────────────────

def run_audit(
    profile: dict,
    schemes_to_check: list,
    all_schemes: list,
    engine_results: dict,
    resume: bool = False,
    output_file: str = OUTPUT_JSON
):
    # Load existing results if resuming
    existing = {}
    if resume and Path(output_file).exists():
        with open(output_file, encoding="utf-8") as f:
            existing = json.load(f)
        log.info(f"Resuming: {len(existing)} schemes already audited")

    to_check = [s for s in schemes_to_check if str(s['id']) not in existing]
    log.info(f"Auditing {len(to_check)} schemes via Gemini...")

    results = dict(existing)
    last_call = 0.0
    stats = {"fp": 0, "fn": 0, "agree_eligible": 0, "agree_not": 0, "error": 0, "skipped": len(existing)}

    for i, scheme in enumerate(to_check):
        sid = str(scheme['id'])
        eng = engine_results.get(scheme['id'], {})
        eng_class = eng.get('class', 'UNKNOWN')

        # Throttle
        elapsed = time.time() - last_call
        if elapsed < DELAY:
            time.sleep(DELAY - elapsed)

        log.info(f"[{i+1}/{len(to_check)}] [{sid}] {scheme.get('name','')[:55]} | engine={eng_class}")

        gemini = call_gemini(profile, scheme)
        last_call = time.time()

        gem_verdict = gemini.get("verdict", "ERROR")

        # Classify agreement/disagreement
        engine_eligible = eng_class in ("FULLY_ELIGIBLE", "POSSIBLY_ELIGIBLE")
        gemini_eligible = gem_verdict == "ELIGIBLE"

        if gem_verdict == "ERROR":
            comparison = "ERROR"
            stats["error"] += 1
        elif engine_eligible and not gemini_eligible:
            comparison = "FALSE_POSITIVE"   # engine wrong — shows scheme but shouldn't
            stats["fp"] += 1
        elif not engine_eligible and gemini_eligible:
            comparison = "FALSE_NEGATIVE"   # engine wrong — hides scheme but shouldn't
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

        # Save checkpoint every 10
        if (i + 1) % 10 == 0:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            log.info(f"  Checkpoint | FP={stats['fp']} FN={stats['fn']} AGREE={stats['agree_eligible']+stats['agree_not']}")

    # Final save
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results, stats


def write_reports(results: dict, stats: dict, profile: dict):
    """Write false_positives.json and audit_summary.txt."""

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
    total_checked = total  # skipped already processed

    with open(SUMMARY_TXT, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("  YOJANAMITRA PROFILE AUDIT — DETERMINISTIC vs GEMINI\n")
        f.write(f"  Run: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 70 + "\n\n")

        f.write("PROFILE:\n")
        for k, v in profile.items():
            if v is not None and v != "":
                f.write(f"  {k}: {v}\n")

        f.write(f"\nSCHEMES AUDITED: {total_checked}\n\n")
        f.write(f"  FALSE POSITIVES  (engine eligible, Gemini says NO): {stats['fp']}\n")
        f.write(f"  FALSE NEGATIVES  (engine not eligible, Gemini YES): {stats['fn']}\n")
        f.write(f"  AGREE ELIGIBLE:                                      {stats['agree_eligible']}\n")
        f.write(f"  AGREE NOT ELIGIBLE:                                  {stats['agree_not']}\n")
        f.write(f"  ERRORS:                                              {stats['error']}\n")

        if total_checked > 0:
            fp_rate = stats['fp'] / (stats['fp'] + stats['agree_eligible']) * 100 if (stats['fp'] + stats['agree_eligible']) > 0 else 0
            f.write(f"\n  FALSE POSITIVE RATE (of what engine showed): {fp_rate:.1f}%\n")

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
            for fn in fns[:20]:  # top 20
                f.write(f"  [{fn['scheme_id']}] {fn['scheme_name'][:60]}\n")
                f.write(f"    Engine: {fn['engine']['class']} — {fn['engine']['rejection'][:80]}\n")
                f.write(f"    Gemini: ELIGIBLE (confidence {fn['gemini']['confidence']:.0%})\n")
                f.write(f"    Notes: {fn['gemini']['notes']}\n\n")

    print(f"\n{'='*70}")
    print(f"  AUDIT COMPLETE")
    print(f"  False Positives:  {stats['fp']}")
    print(f"  False Negatives:  {stats['fn']}")
    print(f"  Agree Eligible:   {stats['agree_eligible']}")
    print(f"  Agree Not:        {stats['agree_not']}")
    print(f"\n  Reports written:")
    print(f"  → {OUTPUT_JSON}")
    print(f"  → {FP_JSON}")
    print(f"  → {SUMMARY_TXT}")
    print(f"{'='*70}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YojanaMitra profile audit: deterministic vs Gemini")
    parser.add_argument("--profile",       default=None,        help="Path to profile JSON file")
    parser.add_argument("--scheme-id",     type=int, default=None, help="Audit single scheme ID")
    parser.add_argument("--all-schemes",   action="store_true", help="Audit all 4324 schemes (slow)")
    parser.add_argument("--resume",        action="store_true", help="Skip already-audited schemes")
    parser.add_argument("--schemes-file",  default=SCHEMES_JSON)
    parser.add_argument("--output",        default=OUTPUT_JSON)
    parser.add_argument("--only-matched",  action="store_true", help="Only audit schemes engine matched (default)")
    args = parser.parse_args()

    # Load schemes
    with open(args.schemes_file, encoding="utf-8") as f:
        all_schemes = json.load(f)
    log.info(f"Loaded {len(all_schemes)} schemes")

    # Load profile
    profile = load_profile(args.profile)
    log.info(f"Profile: {profile.get('name','?')}, age {profile.get('age','?')}, {profile.get('state','?')}")

    # Run engine on all schemes to get baseline
    log.info("Running deterministic engine...")
    engine_results = get_engine_results(profile, all_schemes)
    engine_matched = [s for s in all_schemes if engine_results.get(s['id'], {}).get('class') in ('FULLY_ELIGIBLE', 'POSSIBLY_ELIGIBLE')]
    log.info(f"Engine matched: {len(engine_matched)} schemes")

    # Single scheme debug mode
    if args.scheme_id:
        scheme = next((s for s in all_schemes if s['id'] == args.scheme_id), None)
        if not scheme:
            print(f"Scheme {args.scheme_id} not found")
            exit(1)
        eng = engine_results.get(args.scheme_id, {})
        print(f"\n[ENGINE] {scheme['name']}")
        print(f"  Class: {eng.get('class')}  Score: {eng.get('score')}%")
        print(f"  Rejection: {eng.get('rejection','')}")
        print(f"\n[GEMINI] Sending to Gemini...")
        gemini = call_gemini(profile, scheme)
        print(f"  Verdict: {gemini.get('verdict')}")
        print(f"  Confidence: {gemini.get('confidence',0):.0%}")
        print(f"  Blocking reason: {gemini.get('blocking_reason','')}")
        print(f"  Conditions checked:")
        for c in gemini.get("key_conditions_checked", []):
            status = "✓" if c.get("pass") else "✗"
            print(f"    {status} {c.get('condition','')}: need={c.get('required','')}, have={c.get('user_value','')}")
        exit(0)

    # Select which schemes to audit
    if args.all_schemes:
        schemes_to_check = all_schemes
        log.info("Mode: ALL schemes")
    else:
        # Default: only audit what engine matched (the FP candidates)
        schemes_to_check = engine_matched
        log.info(f"Mode: engine-matched only ({len(schemes_to_check)} schemes)")

    # Run audit
    results, stats = run_audit(
        profile=profile,
        schemes_to_check=schemes_to_check,
        all_schemes=all_schemes,
        engine_results=engine_results,
        resume=args.resume,
        output_file=args.output
    )

    write_reports(results, stats, profile)

