"""
smart_sample_200.py — YojanaMitra Smart Scheme Sampler
=======================================================
Picks 200 DIVERSE schemes from your full dataset for demo/judging.
Ensures coverage across:
  - Categories (education, agriculture, women, health, etc.)
  - States vs Central schemes
  - Complexity levels (simple vs complex eligibility)
  - Edge cases (age limits, income slabs, caste conditions)
  - Gender, disability, minority targeting

Why this matters:
  Judges see your system handle VARIETY, not just easy cases.
  200 well-chosen schemes > 4000 random ones for a demo.

Usage:
    python smart_sample_200.py --input all_schemes_export.json --output sampled_200.json
    python smart_sample_200.py --input all_schemes_export.json --output sampled_200.json --count 200 --seed 42
"""

import json
import argparse
import random
import re
import sys
from collections import defaultdict
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# COMPLEXITY SCORER — measures how "interesting" a scheme is
# ─────────────────────────────────────────────────────────────────────────────

def complexity_score(scheme: dict) -> int:
    """
    Score scheme complexity 0–20.
    Higher = more interesting for demo (more conditions, more edge cases).
    """
    score = 0
    text_fields = [
        scheme.get("eligibility", "") or "",
        scheme.get("description", "") or "",
        scheme.get("exclusions", "") or "",
        scheme.get("application_process", "") or "",
        scheme.get("documents_required", "") or "",
        scheme.get("benefits", "") or "",
    ]
    combined = " ".join(text_fields).lower()

    # Age conditions
    if re.search(r'\b(age|years? old|year of age)\b', combined): score += 1
    if re.search(r'\b\d{1,2}\s*[-–to]\s*\d{2,3}\b', combined): score += 1

    # Income conditions
    if re.search(r'\b(income|salary|bpl|apl|annual|monthly|earning)\b', combined): score += 1
    if re.search(r'[₹rs\.]\s*[\d,]+', combined): score += 1

    # Caste/category
    if re.search(r'\b(sc|st|obc|ews|general|minority|scheduled)\b', combined): score += 1

    # Gender specificity
    if re.search(r'\b(women|female|girl|widow|single woman)\b', combined): score += 1

    # Disability
    if re.search(r'\b(disabled|disability|handicap|divyang|pwd)\b', combined): score += 1

    # Registration requirements
    if re.search(r'\b(registered|registration|bocw|udyam|msme|gst|kcc)\b', combined): score += 1

    # Geographic specificity
    if re.search(r'\b(district|taluk|village|block|gram panchayat)\b', combined): score += 1

    # Exclusions
    if scheme.get("exclusions") and len(scheme.get("exclusions", "")) > 50: score += 2

    # Document complexity
    docs = scheme.get("documents_required", "") or ""
    doc_count = len(re.findall(r'(certificate|card|proof|document|copy)', docs.lower()))
    score += min(doc_count, 3)

    # Benefits complexity
    benefits = scheme.get("benefits", "") or ""
    if len(benefits) > 200: score += 1

    # Multiple components
    if re.search(r'\b(or|either|one of|any of)\b', combined): score += 1

    # Structured columns present
    for field in ["min_age", "max_age", "max_income", "min_income",
                  "disability_percentage_min", "allowed_castes", "allowed_genders"]:
        if scheme.get(field) is not None:
            score += 0.5

    return int(score)


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY DETECTOR — normalize category labels
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_MAP = {
    "education": ["education", "scholarship", "student", "school", "college",
                  "learning", "skill", "training", "vocational"],
    "agriculture": ["agriculture", "farmer", "farming", "crop", "kisan",
                    "horticulture", "fisheries", "animal husbandry"],
    "women": ["women", "girl", "female", "widow", "maternity", "mahila",
              "stree", "nari"],
    "health": ["health", "medical", "hospital", "treatment", "medicine",
               "disease", "insurance", "accident", "disability"],
    "housing": ["housing", "house", "home", "shelter", "awas", "pradhan mantri awas"],
    "employment": ["employment", "job", "work", "labour", "labor", "worker",
                   "rojgar", "wage", "salary"],
    "business": ["enterprise", "msme", "startup", "business", "industry",
                 "manufacturing", "udyam", "entrepreneur"],
    "social_welfare": ["welfare", "pension", "assistance", "relief", "bpl",
                       "disabled", "senior", "old age", "child", "orphan"],
    "agriculture_finance": ["credit", "loan", "subsidy", "kcc", "pm kisan"],
    "minority": ["minority", "muslim", "christian", "waqf", "maulana"],
}

def detect_category(scheme: dict) -> str:
    """Detect scheme category from name + description."""
    text = " ".join([
        (scheme.get("name") or ""),
        (scheme.get("category") or ""),
        (scheme.get("description") or "")[:200],
    ]).lower()

    for cat, keywords in CATEGORY_MAP.items():
        if any(kw in text for kw in keywords):
            return cat
    return "other"


# ─────────────────────────────────────────────────────────────────────────────
# EDGE CASE DETECTOR — flag schemes with interesting conditions
# ─────────────────────────────────────────────────────────────────────────────

def detect_edge_cases(scheme: dict) -> list:
    """Return list of edge case tags present in scheme."""
    combined = " ".join([
        (scheme.get("eligibility") or ""),
        (scheme.get("exclusions") or ""),
        (scheme.get("description") or ""),
        (scheme.get("name") or ""),
    ]).lower()

    edges = []
    patterns = {
        "age_range": r'\b\d{1,2}\s*[-–to]+\s*\d{2,3}\b',
        "income_slab": r'[₹rs\.]\s*[\d,]+',
        "marks_threshold": r'\b(\d{2,3})\s*%\b',
        "multiple_caste": r'\b(sc|st|obc|ews)\b.*\b(sc|st|obc|ews)\b',
        "OR_logic": r'\bor\b.{5,50}\b(eligible|apply|qualify)\b',
        "exclusion_heavy": None,  # checked separately
        "registration_required": r'\b(registered|registration|bocw|udyam)\b',
        "parent_condition": r'\b(parent|father|mother|guardian|ward of)\b',
        "first_generation": r'\bfirst.{0,10}(generation|graduate|learner)\b',
        "domicile": r'\b(domicile|resident|residing|permanent resident)\b',
        "time_bound": r'\b(\d+\s*(day|month|year)s?\s*(of|after|from|within))\b',
    }

    for tag, pattern in patterns.items():
        if tag == "exclusion_heavy":
            excl = scheme.get("exclusions") or ""
            if len(excl) > 100:
                edges.append(tag)
        elif pattern and re.search(pattern, combined):
            edges.append(tag)

    return edges


# ─────────────────────────────────────────────────────────────────────────────
# SMART SAMPLER — stratified + diversity-aware selection
# ─────────────────────────────────────────────────────────────────────────────

def smart_sample(schemes: list, count: int = 200, seed: int = 42) -> list:
    """
    Stratified sampling to maximize coverage for demo.

    Strategy:
      40% — spread across categories (all categories represented)
      20% — high complexity schemes (hard cases)
      15% — state-specific schemes (geographic variety)
      10% — central government schemes
      10% — edge cases (age range, income slab, OR logic, etc.)
       5% — random fill (avoid bias)
    """
    random.seed(seed)
    selected_ids = set()
    selected = []

    def pick(pool: list, n: int):
        """Pick n unique schemes from pool not already selected."""
        available = [s for s in pool if s.get("id") not in selected_ids]
        picks = random.sample(available, min(n, len(available)))
        for p in picks:
            selected_ids.add(p["id"])
            selected.append(p)

    # Annotate all schemes
    print(f"Annotating {len(schemes)} schemes...")
    for s in schemes:
        s["_category"] = detect_category(s)
        s["_complexity"] = complexity_score(s)
        s["_edge_cases"] = detect_edge_cases(s)
        s["_is_central"] = any(
            kw in (s.get("name") or "").upper()
            for kw in ["PM ", "PRADHAN MANTRI", "CENTRAL", "NATIONAL", "GOI"]
        ) or (s.get("state") in [None, "", "ALL", "Central", "central"])

    # ── BUCKET 1: Category coverage (40% = 80 schemes) ──
    # At least floor(80/num_categories) per category, rest by random
    by_category = defaultdict(list)
    for s in schemes:
        by_category[s["_category"]].append(s)

    cat_target = 80
    per_cat = max(2, cat_target // len(by_category))
    print(f"Categories found: {list(by_category.keys())}")

    for cat, cat_schemes in by_category.items():
        # Within each category, prefer higher complexity
        sorted_cat = sorted(cat_schemes, key=lambda x: x["_complexity"], reverse=True)
        pick(sorted_cat, per_cat)

    # Fill remaining category quota randomly
    remaining_cat = cat_target - len(selected)
    if remaining_cat > 0:
        pick(schemes, remaining_cat)

    # ── BUCKET 2: High complexity (20% = 40 schemes) ──
    high_complexity = sorted(schemes, key=lambda x: x["_complexity"], reverse=True)[:200]
    pick(high_complexity, 40)

    # ── BUCKET 3: State-specific diversity (15% = 30 schemes) ──
    states_seen = defaultdict(list)
    for s in schemes:
        state = (s.get("state") or s.get("allowed_states") or "")
        if isinstance(state, list):
            state = state[0] if state else ""
        if state and state.lower() not in ("all", "", "central"):
            states_seen[state.lower()].append(s)

    # Pick from different states
    for state, state_schemes in sorted(states_seen.items()):
        if len(selected) >= (80 + 40 + 30):
            break
        pick(state_schemes, 1)

    # ── BUCKET 4: Central government schemes (10% = 20 schemes) ──
    central = [s for s in schemes if s.get("_is_central")]
    pick(central, 20)

    # ── BUCKET 5: Edge cases (10% = 20 schemes) ──
    edge_case_tags = [
        "age_range", "income_slab", "marks_threshold",
        "exclusion_heavy", "OR_logic", "parent_condition",
        "registration_required", "first_generation"
    ]
    for tag in edge_case_tags:
        tagged = [s for s in schemes if tag in s.get("_edge_cases", [])]
        pick(tagged, max(1, 20 // len(edge_case_tags)))

    # ── BUCKET 6: Random fill to hit target ──
    remaining = count - len(selected)
    if remaining > 0:
        pick(schemes, remaining)

    result = selected[:count]
    print(f"\n✅ Sampled {len(result)} schemes")

    # Print coverage report
    cats = defaultdict(int)
    for s in result:
        cats[s["_category"]] += 1
    print("\n📊 Category coverage:")
    for cat, n in sorted(cats.items(), key=lambda x: -x[1]):
        bar = "█" * n
        print(f"  {cat:<25} {n:>3}  {bar}")

    complexities = [s["_complexity"] for s in result]
    avg = sum(complexities) / len(complexities)
    print(f"\n📈 Complexity: avg={avg:.1f}, min={min(complexities)}, max={max(complexities)}")

    edge_counts = [len(s["_edge_cases"]) for s in result]
    print(f"🎯 Edge cases: {sum(1 for e in edge_counts if e > 0)} schemes have edge cases")

    # Clean internal annotations before saving
    for s in result:
        s.pop("_category", None)
        s.pop("_complexity", None)
        s.pop("_edge_cases", None)
        s.pop("_is_central", None)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Smart stratified sampler for YojanaMitra demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python smart_sample_200.py --input all_schemes_export.json --output sampled_200.json
  python smart_sample_200.py --input all_schemes_export.json --output sampled_200.json --count 150 --seed 99
        """
    )
    parser.add_argument("--input", default="all_schemes_export.json",
                        help="Full schemes JSON file")
    parser.add_argument("--output", default="sampled_200.json",
                        help="Output: sampled schemes JSON")
    parser.add_argument("--count", type=int, default=200,
                        help="Number of schemes to sample (default: 200)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")
    parser.add_argument("--report", action="store_true",
                        help="Save a coverage report JSON alongside output")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"ERROR: {args.input} not found")
        sys.exit(1)

    print(f"Loading {args.input}...")
    with open(args.input, "r", encoding="utf-8") as f:
        all_schemes = json.load(f)

    if isinstance(all_schemes, dict) and "schemes" in all_schemes:
        all_schemes = all_schemes["schemes"]

    if len(all_schemes) < args.count:
        print(f"WARNING: Only {len(all_schemes)} schemes available, sampling all")
        args.count = len(all_schemes)

    sampled = smart_sample(all_schemes, count=args.count, seed=args.seed)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(sampled, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved {len(sampled)} schemes → {args.output}")
    print(f"   Now run: python extract_conditions_v4.py --input {args.output} --output extracted_200.json --end {args.count}")


if __name__ == "__main__":
    main()
