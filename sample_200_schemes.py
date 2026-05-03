"""
YojanaMitra — Smart 200-Scheme Sampler + Validation Layer
==========================================================
Step 1: Run this to pick 200 DIVERSE schemes from your full dataset.
Step 2: Run extract_conditions_v4.py on the sampled output.
Step 3: Run the validator at the bottom to check extraction quality.

Usage:
    # Sample 200 diverse schemes:
    python sample_200_schemes.py --input all_schemes_export.json --output sampled_200.json

    # Then extract:
    python extract_conditions_v4.py --input sampled_200.json --output extracted_200.json

    # Then validate:
    python sample_200_schemes.py --validate --input extracted_200.json
"""

import json, sys, argparse, random, re
from collections import defaultdict
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# SMART SAMPLER
# Goal: 200 schemes that cover maximum diversity so demo looks strong
# ─────────────────────────────────────────────────────────────────────────────

# How many slots per category bucket (adjust if needed)
CATEGORY_SLOTS = {
    "education":      30,
    "agriculture":    25,
    "women":          25,
    "health":         20,
    "employment":     20,
    "housing":        15,
    "social welfare": 15,
    "business":       15,
    "disability":     10,
    "minority":       10,
    "other":          15,   # catch-all for anything else
}

# Complexity scoring — higher = more interesting for judges
def complexity_score(scheme: dict) -> int:
    """Score a scheme by how complex / diverse its eligibility is."""
    score = 0
    text = " ".join(str(v) for v in scheme.values()).lower()

    # Has age condition
    if re.search(r'\b(age|years old|above \d|below \d|minimum age|maximum age)\b', text):
        score += 2
    # Has income condition
    if re.search(r'\b(income|lakh|rupees|bpl|ews|apl)\b', text):
        score += 2
    # Has caste condition
    if re.search(r'\b(sc|st|obc|scheduled caste|scheduled tribe|backward class)\b', text):
        score += 2
    # Has gender condition
    if re.search(r'\b(women|female|girl|widow|single woman)\b', text):
        score += 1
    # Has state restriction
    if scheme.get("allowed_states") and scheme["allowed_states"] not in ([], ["ALL"], ["all"], ""):
        score += 1
    # Has exclusions
    if scheme.get("exclusions") and len(str(scheme["exclusions"])) > 30:
        score += 2
    # Has disability
    if re.search(r'\b(disab|handicap|divyang|pwd)\b', text):
        score += 2
    # Has registration requirement
    if re.search(r'\b(bocw|udyam|kisan credit|msme|gst registered|registered with)\b', text):
        score += 2
    # Has document list
    if scheme.get("documents_required") and len(str(scheme["documents_required"])) > 50:
        score += 1
    # Has marks/merit
    if re.search(r'\b(marks|percentage|merit|first class|distinction|neet|jee)\b', text):
        score += 2
    # Has parent conditions
    if re.search(r'\b(ward of|parent|guardian|father|mother)\b.*\b(worker|employee|farmer)\b', text):
        score += 2
    # Has enterprise condition
    if re.search(r'\b(startup|dpiit|greenfield|msme|turnover)\b', text):
        score += 2
    # Central vs state scheme
    if scheme.get("state") and scheme["state"].lower() not in ("central", "all", ""):
        score += 1

    return score


def categorize_scheme(scheme: dict) -> str:
    """Assign a scheme to a broad category bucket."""
    cat = str(scheme.get("category", "")).lower()
    name = str(scheme.get("name", "")).lower()
    text = cat + " " + name

    if any(k in text for k in ["education", "scholar", "student", "school", "college", "study", "training"]):
        return "education"
    if any(k in text for k in ["agri", "farmer", "kisan", "crop", "irrigation", "horticulture", "fishery", "fish"]):
        return "agriculture"
    if any(k in text for k in ["women", "woman", "girl", "widow", "maternity", "female", "mahila"]):
        return "women"
    if any(k in text for k in ["health", "medical", "hospital", "disease", "treatment", "medicine", "insurance"]):
        return "health"
    if any(k in text for k in ["employ", "job", "skill", "labour", "labor", "work", "apprentice", "vocational"]):
        return "employment"
    if any(k in text for k in ["hous", "shelter", "awas", "patta", "land", "construction"]):
        return "housing"
    if any(k in text for k in ["social", "welfare", "pension", "senior", "old age", "disability", "handicap"]):
        return "social welfare"
    if any(k in text for k in ["business", "enterprise", "msme", "startup", "entrepreneur", "industry", "trade"]):
        return "business"
    if any(k in text for k in ["disab", "handicap", "divyang", "pwd"]):
        return "disability"
    if any(k in text for k in ["minority", "muslim", "christian", "waqf", "maulana"]):
        return "minority"
    return "other"


def sample_200(schemes: list, target: int = 200, seed: int = 42) -> list:
    """
    Pick `target` schemes with maximum diversity.
    Strategy:
      1. Score every scheme for complexity
      2. Bucket into categories
      3. Fill slots from each bucket (highest complexity first)
      4. Fill remaining slots from overflow (high complexity first)
    """
    random.seed(seed)

    # Score and categorize all schemes
    for s in schemes:
        s["_category"] = categorize_scheme(s)
        s["_complexity"] = complexity_score(s)

    # Group by category, sorted by complexity desc
    buckets = defaultdict(list)
    for s in schemes:
        buckets[s["_category"]].append(s)
    for cat in buckets:
        buckets[cat].sort(key=lambda x: x["_complexity"], reverse=True)

    selected = []
    used_ids = set()

    # Fill category slots
    for cat, slots in CATEGORY_SLOTS.items():
        pool = buckets.get(cat, [])
        for scheme in pool:
            if len(selected) >= target:
                break
            sid = scheme.get("id")
            if sid not in used_ids:
                selected.append(scheme)
                used_ids.add(sid)
                slots -= 1
                if slots <= 0:
                    break

    # Fill remaining from all schemes (high complexity, not yet selected)
    if len(selected) < target:
        overflow = sorted(
            [s for s in schemes if s.get("id") not in used_ids],
            key=lambda x: x["_complexity"],
            reverse=True
        )
        for s in overflow:
            if len(selected) >= target:
                break
            selected.append(s)
            used_ids.add(s.get("id"))

    # Clean internal fields before saving
    for s in selected:
        s.pop("_category", None)
        s.pop("_complexity", None)

    return selected[:target]


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION LAYER
# Run this AFTER extract_conditions_v4.py to QA the output
# ─────────────────────────────────────────────────────────────────────────────

VALID_OPERATORS = {"eq", "neq", "gte", "lte", "in", "not_in", "between", "boolean"}
VALID_CONDITION_TYPES = {"hard", "soft"}
VALID_GENDERS = {"male", "female", "transgender", "any"}
VALID_CASTES = {"sc", "st", "obc", "ews", "general", "minority"}
VALID_RESIDENCE = {"rural", "urban", "any"}

KNOWN_FIELDS = {
    "age", "min_age", "max_age", "gender", "category", "annual_income",
    "annual_family_income", "monthly_income", "annual_parental_income_max",
    "state", "residence", "district", "is_citizen", "is_nri", "is_indian_national",
    "is_disabled", "disability_percentage", "is_senior_citizen", "is_widow",
    "is_orphan", "is_bpl", "ration_card_type", "is_ews", "is_income_tax_payer",
    "education_level", "current_class", "min_marks_percentage",
    "min_marks_percentage_10th", "course_type", "occupation", "employment_status",
    "is_farmer", "is_student", "is_self_employed", "is_unorganised_worker",
    "is_govt_employee", "is_construction_worker", "is_sanitation_worker",
    "is_fisher", "is_artisan", "is_weaver", "marital_status", "num_children",
    "num_daughters", "is_head_of_family", "has_aadhaar", "has_bank_account",
    "has_ration_card", "has_income_certificate", "has_domicile",
    "has_caste_certificate", "has_disability_certificate", "is_bocw_registered",
    "is_lfw_registered", "has_kcc", "has_udyam_registration", "is_msme_registered",
    "is_gst_registered", "is_dpiit_recognized_startup", "enterprise_type",
    "enterprise_age_years", "is_greenfield_project", "is_non_corporate",
    "parent_occupation", "parent_is_construction_worker", "parent_is_sanitation_worker",
    "parent_is_lfw_registered", "scheme_previously_availed", "has_existing_loan_default",
    "is_tribal", "is_minority", "is_pregnant", "is_single_woman", "religion",
    "land_size_acres", "is_landless", "owns_land", "has_land_records",
    "has_udyam_registration", "has_entrance_exam_qualification",
    "father_occupation", "mother_occupation", "quota_based", "max_children_benefited",
    "membership_duration_months",
}


def validate_single_condition(cond: dict, scheme_id, idx: int) -> list:
    """Returns list of issue strings for one condition. Empty = valid."""
    issues = []
    prefix = f"  [Scheme {scheme_id} | cond #{idx}]"

    # Required keys
    for k in ("field", "operator", "value", "condition_type", "confidence"):
        if k not in cond:
            issues.append(f"{prefix} Missing key: '{k}'")

    field = cond.get("field", "")
    op = cond.get("operator", "")
    val = cond.get("value")
    ctype = cond.get("condition_type", "")
    conf = cond.get("confidence", 0)

    if op not in VALID_OPERATORS:
        issues.append(f"{prefix} Bad operator: '{op}'")

    if ctype not in VALID_CONDITION_TYPES:
        issues.append(f"{prefix} Bad condition_type: '{ctype}'")

    try:
        c = float(conf)
        if not (0.0 <= c <= 1.0):
            issues.append(f"{prefix} confidence out of range: {conf}")
    except (TypeError, ValueError):
        issues.append(f"{prefix} confidence not numeric: {conf}")

    if field not in KNOWN_FIELDS:
        issues.append(f"{prefix} Unknown field: '{field}' (may be custom — review)")

    # Operator-value consistency
    if op == "between":
        if not isinstance(val, list) or len(val) != 2:
            issues.append(f"{prefix} 'between' needs [min, max] list, got: {val}")
        else:
            try:
                if float(val[0]) > float(val[1]):
                    issues.append(f"{prefix} 'between' min > max: {val}")
            except (TypeError, ValueError):
                issues.append(f"{prefix} 'between' values not numeric: {val}")

    if op in ("in", "not_in") and not isinstance(val, list):
        issues.append(f"{prefix} '{op}' needs a list, got: {type(val).__name__}")

    if op in ("gte", "lte", "gt", "lt"):
        try:
            float(val)
        except (TypeError, ValueError):
            issues.append(f"{prefix} Numeric operator '{op}' but value not numeric: {val}")

    # Gender values
    if field == "gender":
        vals = val if isinstance(val, list) else [val]
        for v in vals:
            if str(v).lower() not in VALID_GENDERS:
                issues.append(f"{prefix} Unknown gender value: '{v}'")

    # Caste values
    if field == "category":
        vals = val if isinstance(val, list) else [val]
        for v in vals:
            if str(v).lower() not in VALID_CASTES:
                issues.append(f"{prefix} Unknown caste value: '{v}'")

    # Residence
    if field == "residence" and str(val).lower() not in VALID_RESIDENCE:
        issues.append(f"{prefix} Unknown residence value: '{val}'")

    # Boolean fields should have bool values
    bool_fields = {f for f in KNOWN_FIELDS if f.startswith("is_") or f.startswith("has_")}
    if field in bool_fields and op in ("eq", "boolean"):
        if not isinstance(val, bool):
            issues.append(f"{prefix} Boolean field '{field}' should have bool value, got: {type(val).__name__} ({val})")

    return issues


def validate_extraction(extracted: list) -> dict:
    """
    Full validation pass over extraction output.
    Returns a report dict with stats + all issues found.
    """
    total_schemes = len(extracted)
    total_conditions = 0
    all_issues = []
    empty_schemes = []
    low_confidence_schemes = []
    gemini_failed = []

    field_freq = defaultdict(int)

    for item in extracted:
        sid = item.get("scheme_id", "?")
        conds = item.get("conditions", [])
        total_conditions += len(conds)

        if not conds:
            empty_schemes.append(sid)

        if item.get("extraction_confidence", 1.0) < 0.65:
            low_confidence_schemes.append(sid)

        if not item.get("gemini_used", True) and item.get("condition_count", 0) < 2:
            gemini_failed.append(sid)

        for i, cond in enumerate(conds):
            issues = validate_single_condition(cond, sid, i + 1)
            all_issues.extend(issues)
            field_freq[cond.get("field", "UNKNOWN")] += 1

    # Top fields used
    top_fields = sorted(field_freq.items(), key=lambda x: x[1], reverse=True)[:20]

    report = {
        "summary": {
            "total_schemes": total_schemes,
            "total_conditions": total_conditions,
            "avg_conditions_per_scheme": round(total_conditions / max(total_schemes, 1), 2),
            "empty_schemes_count": len(empty_schemes),
            "low_confidence_count": len(low_confidence_schemes),
            "gemini_failed_count": len(gemini_failed),
            "total_issues_found": len(all_issues),
            "validation_pass": len(all_issues) == 0,
        },
        "top_fields_used": top_fields,
        "empty_schemes": empty_schemes[:20],
        "low_confidence_schemes": low_confidence_schemes[:20],
        "gemini_failed_schemes": gemini_failed[:20],
        "issues": all_issues[:100],  # Show first 100 issues max
    }
    return report


def print_report(report: dict):
    s = report["summary"]
    print("\n" + "="*60)
    print("  EXTRACTION VALIDATION REPORT")
    print("="*60)
    print(f"  Schemes validated     : {s['total_schemes']}")
    print(f"  Total conditions      : {s['total_conditions']}")
    print(f"  Avg conditions/scheme : {s['avg_conditions_per_scheme']}")
    print(f"  Empty schemes         : {s['empty_schemes_count']}")
    print(f"  Low confidence        : {s['low_confidence_count']}")
    print(f"  Gemini failures       : {s['gemini_failed_count']}")
    print(f"  Issues found          : {s['total_issues_found']}")
    print(f"  VALIDATION {'✅ PASS' if s['validation_pass'] else '❌ FAIL (see issues below)'}")
    print()
    print("  TOP FIELDS EXTRACTED:")
    for field, count in report["top_fields_used"][:10]:
        bar = "█" * min(count // 2, 30)
        print(f"    {field:<40} {bar} {count}")
    if report["empty_schemes"]:
        print(f"\n  ⚠ Empty schemes (no conditions extracted): {report['empty_schemes']}")
    if report["low_confidence_schemes"]:
        print(f"\n  ⚠ Low-confidence schemes: {report['low_confidence_schemes']}")
    if report["issues"]:
        print(f"\n  ❌ ISSUES (first {min(len(report['issues']),100)}):")
        for issue in report["issues"][:50]:
            print(f"    {issue}")
    print("="*60 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Smart 200-Scheme Sampler + Validation Layer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sample 200 diverse schemes:
  python sample_200_schemes.py --input all_schemes_export.json --output sampled_200.json

  # Sample with custom count:
  python sample_200_schemes.py --input all_schemes_export.json --output sampled_300.json --count 300

  # Validate extraction output:
  python sample_200_schemes.py --validate --input extracted_200.json

  # Validate and save report:
  python sample_200_schemes.py --validate --input extracted_200.json --report validation_report.json
        """
    )
    parser.add_argument("--input", required=True, help="Input JSON file")
    parser.add_argument("--output", default="sampled_200.json", help="Output sampled schemes file")
    parser.add_argument("--count", type=int, default=200, help="Number of schemes to sample (default: 200)")
    parser.add_argument("--validate", action="store_true", help="Run validation on extracted output instead of sampling")
    parser.add_argument("--report", default=None, help="Save validation report to this JSON file")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")

    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    if args.validate:
        # Validation mode
        if not isinstance(data, list):
            print("ERROR: Expected a JSON array of extracted scheme results.")
            sys.exit(1)
        print(f"Validating {len(data)} extracted schemes...")
        report = validate_extraction(data)
        print_report(report)
        if args.report:
            with open(args.report, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"Report saved to: {args.report}")
    else:
        # Sampling mode
        if isinstance(data, dict) and "schemes" in data:
            data = data["schemes"]
        if not isinstance(data, list):
            print("ERROR: Expected a JSON array of schemes.")
            sys.exit(1)

        print(f"Input: {len(data)} total schemes")
        sampled = sample_200(data, target=args.count, seed=args.seed)
        print(f"Sampled: {len(sampled)} schemes (diverse across categories + complexity)")

        # Show category breakdown
        cats = defaultdict(int)
        for s in sampled:
            cats[categorize_scheme(s)] += 1
        print("\nCategory breakdown:")
        for cat, cnt in sorted(cats.items(), key=lambda x: -x[1]):
            print(f"  {cat:<20} {cnt}")

        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(sampled, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to: {args.output}")
        print(f"\nNext step:")
        print(f"  python extract_conditions_v4.py --input {args.output} --output extracted_200.json")
        print(f"\nThen validate:")
        print(f"  python sample_200_schemes.py --validate --input extracted_200.json")


if __name__ == "__main__":
    main()
