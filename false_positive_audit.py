"""
FALSE POSITIVE AUDIT — YojanaMitra Inference Engine
====================================================
Tests multiple realistic user profiles against ALL 4,216 schemes and surfaces
every suspicious match with full condition-level evidence.

Usage:
    python false_positive_audit.py

Output:
    - FULLY_ELIGIBLE schemes that contradict the user's known hard data (leaks)
    - POSSIBLY_ELIGIBLE schemes where no condition was actually checked (free rides)
    - Summary stats per profile
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from static.engine import YojanaMitraInferenceEngine


# ─── load data ────────────────────────────────────────────────────────────────
def load_schemes(path="all_conditions_classified.json"):
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    schemes = []
    for sid, conds in raw.items():
        if isinstance(conds, list):
            entry = conds[0] if conds else {}
        else:
            entry = conds

        if not isinstance(entry, dict):
            continue

        entry = dict(entry)
        entry["id"] = sid
        schemes.append(entry)

    return schemes


# ─── test profiles ────────────────────────────────────────────────────────────
TEST_PROFILES = [
    {
        "label": "25-yr Male student, Delhi",
        "profile": {
            "age": 25, "gender": "male", "state": "Delhi",
            "occupation": "Student", "is_student": True,
            "annual_family_income": 400000, "caste": "General",
            "is_disabled": False, "is_farmer": False,
        },
        # Explicit rules: these should NEVER appear as FULLY/POSSIBLY eligible
        "must_not_match": [
            ("min_age > 25",      lambda c: c["field"] == "age" and c["operator"] in (">=",">") and _num(c["value"]) > 25),
            ("female-only",       lambda c: c["field"] == "gender" and str(c["value"]).lower() in ("female","woman","महिला")),
            ("state != Delhi",    lambda c: c["field"] == "state" and str(c["value"]).lower() not in ("delhi","all","all india","")),
            ("60+ scheme",        lambda c: c["field"] == "age" and c["operator"] in (">=",">") and _num(c["value"]) >= 60),
        ],
    },
    {
        "label": "45-yr Female widow, Odisha, BPL, annual income 80k",
        "profile": {
            "age": 45, "gender": "female", "state": "Odisha",
            "occupation": "Homemaker", "annual_family_income": 80000,
            "caste": "SC", "is_disabled": False, "is_farmer": False,
            "is_widow_single_woman": True, "is_bpl": True,
        },
        "must_not_match": [
            ("male-only",         lambda c: c["field"] == "gender" and str(c["value"]).lower() in ("male","man")),
            ("state != Odisha",   lambda c: c["field"] == "state" and str(c["value"]).lower() not in ("odisha","all","all india","")),
            ("min_age > 45",      lambda c: c["field"] == "age" and c["operator"] in (">=",">") and _num(c["value"]) > 45),
            ("max_income < 80k",  lambda c: c["field"] == "annual_family_income" and c["operator"] in ("<=","<") and _num(c["value"]) < 80000),
        ],
    },
    {
        "label": "65-yr Male senior citizen, Punjab, General, annual income 150k",
        "profile": {
            "age": 65, "gender": "male", "state": "Punjab",
            "occupation": "Retired", "annual_family_income": 150000,
            "caste": "General", "is_disabled": False, "is_farmer": False,
            "is_senior_citizen": True,
        },
        "must_not_match": [
            ("max_age < 65",      lambda c: c["field"] == "age" and c["operator"] in ("<=","<") and _num(c["value"]) < 65),
            ("female-only",       lambda c: c["field"] == "gender" and str(c["value"]).lower() in ("female","woman","महिला")),
            ("state != Punjab",   lambda c: c["field"] == "state" and str(c["value"]).lower() not in ("punjab","all","all india","")),
            ("SC/ST-only caste",  lambda c: c["field"] == "caste" and str(c["value"]).lower() in ("sc","st","sc/st")),
        ],
    },
    {
        "label": "30-yr Male farmer, Rajasthan, OBC, annual income 60k, owns land",
        "profile": {
            "age": 30, "gender": "male", "state": "Rajasthan",
            "occupation": "Farmer", "annual_family_income": 60000,
            "caste": "OBC", "is_disabled": False, "is_farmer": True,
            "land_size_hectares": 2.5,
        },
        "must_not_match": [
            ("female-only",       lambda c: c["field"] == "gender" and str(c["value"]).lower() in ("female","woman","महिला")),
            ("state != Rajasthan",lambda c: c["field"] == "state" and str(c["value"]).lower() not in ("rajasthan","all","all india","")),
            ("60+ age gate",      lambda c: c["field"] == "age" and c["operator"] in (">=",">") and _num(c["value"]) > 30),
        ],
    },
]


# ─── helpers ──────────────────────────────────────────────────────────────────
def _num(val):
    try:
        return float(val)
    except Exception:
        return 0.0


def check_leak(scheme, must_not_match_rules):
    """
    Returns list of violated rules: conditions in the scheme that the user
    explicitly contradicts but which were NOT caught by the engine.
    """
    violations = []
    for rule_name, rule_fn in must_not_match_rules:
        for cond in scheme.get("classified_conditions", []):
            try:
                if rule_fn(cond):
                    violations.append((rule_name, cond))
                    break
            except Exception:
                pass
    return violations


def classify_suspicious(status, res, scheme):
    """Marks a match as suspicious if engine gave FULLY_ELIGIBLE with 0 conditions."""
    if status == "FULLY_ELIGIBLE" and len(scheme.get("classified_conditions", [])) == 0:
        return "FREE_RIDE: No conditions at all — engine cannot guarantee eligibility"
    return None


# ─── main audit ───────────────────────────────────────────────────────────────
def run_audit():
    print("Loading schemes...")
    schemes = load_schemes()
    print(f"Loaded {len(schemes)} schemes.\n")

    grand_leaks = 0

    for test in TEST_PROFILES:
        label   = test["label"]
        profile = test["profile"]
        rules   = test["must_not_match"]

        engine = YojanaMitraInferenceEngine(profile)

        leaks       = []  # FULLY or POSSIBLY eligible but contradicts known data
        free_rides  = []  # FULLY eligible with zero conditions

        for scheme in schemes:
            res    = engine.evaluate_scheme(scheme)
            status = res["status"]

            if status == "NOT_ELIGIBLE":
                continue

            sid   = scheme.get("id", "?")
            name  = scheme.get("scheme_name") or scheme.get("name") or f"Scheme {sid}"
            conds = scheme.get("classified_conditions", [])

            # 1. Check condition-level violations
            violations = check_leak(scheme, rules)
            if violations:
                leaks.append({
                    "id": sid, "name": name, "status": status,
                    "confidence": res["confidence"],
                    "violations": violations,
                    "conditions": conds,
                    "engine_reason": res.get("reason", ""),
                })

            # 2. Check free rides (FULLY_ELIGIBLE, no conditions)
            if status == "FULLY_ELIGIBLE" and len(conds) == 0:
                free_rides.append({"id": sid, "name": name})

        grand_leaks += len(leaks)

        # ── print report ──
        print("=" * 70)
        print(f"PROFILE: {label}")
        print(f"  Profile data: {profile}")
        print(f"  -> Total Leaks (hard guard violations): {len(leaks)}")
        print(f"  -> Free Rides (FULLY_ELIGIBLE, 0 conditions): {len(free_rides)}")
        print()

        if leaks:
            print(f"  [LEAKS] Schemes that should be NOT_ELIGIBLE but are {leaks[0]['status']}:")
            for i, leak in enumerate(leaks[:20]):  # cap at 20 per profile
                print(f"\n    [{i+1}] {leak['name']} (ID: {leak['id']})")
                print(f"         Status: {leak['status']} | Confidence: {leak['confidence']}")
                print(f"         Engine Reason: {leak['engine_reason']}")
                for vname, vcond in leak["violations"]:
                    print(f"         >> VIOLATED RULE: '{vname}'")
                    print(f"            Condition: field={vcond['field']}, "
                          f"op={vcond.get('operator')}, "
                          f"value={vcond.get('value')}, "
                          f"classification={vcond.get('classification')}")
            if len(leaks) > 20:
                print(f"\n    ... and {len(leaks) - 20} more leaks (truncated)")
        else:
            print("  [OK] No hard-guard leaks detected for this profile.")

        if free_rides:
            print(f"\n  [FREE RIDES] FULLY_ELIGIBLE with zero conditions (first 10):")
            for fr in free_rides[:10]:
                print(f"    - {fr['name']} (ID: {fr['id']})")

        print()

    print("=" * 70)
    print(f"GRAND TOTAL LEAKS ACROSS ALL PROFILES: {grand_leaks}")
    print("=" * 70)


if __name__ == "__main__":
    run_audit()
