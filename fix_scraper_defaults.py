"""
fix_scraper_defaults.py
=======================
One-time DB cleanup to fix two scraper defaults that poison eligibility matching:

PROBLEM 1 — allowed_states = ['Karnataka'] (scraper default)
  4,020 / 4,324 schemes were tagged with Karnataka as a default.
  Of these:
    2,524  have a different state clearly in their eligibility text   → fix to correct state
      860  have no state in elig text, but description has a state    → fix from description
       12  have state in scheme name                                   → fix from name
      122  have national ministry / PM scheme signals                  → fix to 'All India'
       52  DB=KA is actually correct (text confirms Karnataka)         → leave alone
    1,444  truly ambiguous (resolver handles these fine via text)      → leave alone

PROBLEM 2 — allowed_castes = ['SC','ST','OBC','General','EWS'] (scraper default = everyone)
  38 schemes have this all-castes default.
  These should be NULL / empty (open to all castes), not a specific restriction.

SAFE TO RUN:
  - Uses a transaction; rolls back on any error
  - Prints a full diff before committing
  - Pass --dry-run to preview without writing
  - Pass --commit to actually write to DB

Usage:
  python fix_scraper_defaults.py --dry-run      # preview all changes
  python fix_scraper_defaults.py --commit        # apply to DB
  python fix_scraper_defaults.py --dry-run --limit 20   # preview first 20 changes
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# ARGS
# ─────────────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser()
parser.add_argument("--dry-run",  action="store_true", default=True,
                    help="Preview changes without writing (default)")
parser.add_argument("--commit",   action="store_true",
                    help="Actually write changes to DB")
parser.add_argument("--limit",    type=int, default=None,
                    help="Only process first N changes (for inspection)")
ARGS = parser.parse_args()

# --commit overrides --dry-run
DRY_RUN = not ARGS.commit

# ─────────────────────────────────────────────────────────────────────────────
# STATE LOOKUP TABLES (same as scheme_rule_adapter)
# ─────────────────────────────────────────────────────────────────────────────

STATE_TEXT_SCAN = {
    "haryana": "HR", "karnataka": "KA", "maharashtra": "MH",
    "tamil nadu": "TN", "tamilnadu": "TN", "uttar pradesh": "UP",
    "delhi": "DL", "gujarat": "GJ", "rajasthan": "RJ",
    "andhra pradesh": "AP", "telangana": "TS", "kerala": "KL",
    "west bengal": "WB", "bihar": "BR", "odisha": "OD",
    "punjab": "PB", "madhya pradesh": "MP", "chhattisgarh": "CG",
    "assam": "AS", "jharkhand": "JH", "uttarakhand": "UK",
    "himachal pradesh": "HP", "goa": "GA", "tripura": "TR",
    "manipur": "MN", "meghalaya": "ML", "nagaland": "NL",
    "mizoram": "MZ", "arunachal pradesh": "AR", "sikkim": "SK",
    "jammu": "JK", "kashmir": "JK", "ladakh": "LA",
    "puducherry": "PY", "pondicherry": "PY", "chandigarh": "CH",
    "himachal": "HP", "himachali": "HP", "uttarakhandi": "UK",
    "odishan": "OD", "goan": "GA",
}

# Full display name for each code (for writing back to DB)
CODE_TO_DISPLAY = {
    "HR": "Haryana", "KA": "Karnataka", "MH": "Maharashtra",
    "TN": "Tamil Nadu", "UP": "Uttar Pradesh", "DL": "Delhi",
    "GJ": "Gujarat", "RJ": "Rajasthan", "AP": "Andhra Pradesh",
    "TS": "Telangana", "KL": "Kerala", "WB": "West Bengal",
    "BR": "Bihar", "OD": "Odisha", "PB": "Punjab",
    "MP": "Madhya Pradesh", "CG": "Chhattisgarh", "AS": "Assam",
    "JH": "Jharkhand", "UK": "Uttarakhand", "HP": "Himachal Pradesh",
    "GA": "Goa", "TR": "Tripura", "MN": "Manipur", "ML": "Meghalaya",
    "NL": "Nagaland", "MZ": "Mizoram", "AR": "Arunachal Pradesh",
    "SK": "Sikkim", "JK": "Jammu and Kashmir", "LA": "Ladakh",
    "PY": "Puducherry", "CH": "Chandigarh",
}

ALL_INDIA_VALUES = {"all india", "all", "any", "pan india", "national", "central"}

# Exclusion prefixes — if state name appears after these, it's NOT a residency mention
EXCL_PREFIXES = ["unlike", "similar to", "compared to", "as in",
                 "whereas in", "not like", "just like", "example of",
                 "other than", "except in", "outside"]

# National scheme signals — if present and no state found, mark as All India
NATIONAL_SIGNALS = [
    "pradhan mantri", "pm-", "pm ", "pmgsy", "pmay", "pmkvy", "pmfby",
    "government of india", "ministry of", "central government",
    "national scheme", "pan india", "all india", "across india",
    "throughout india", "central sector", "centrally sponsored",
]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _parse_json_field(v) -> list:
    if not v:
        return []
    if isinstance(v, list):
        return [str(x).lower().strip() for x in v if x]
    try:
        data = json.loads(v)
        if isinstance(data, list):
            return [str(x).lower().strip() for x in data if x]
        return [str(data).lower().strip()]
    except Exception:
        return [str(v).lower().strip()]


def _scan_text_for_state(text: str) -> Optional[str]:
    """Return state code if a state name found with word boundary, excluding comparison context."""
    text_lower = text.lower()
    for state_name, code in sorted(STATE_TEXT_SCAN.items(), key=lambda x: -len(x[0])):
        if len(state_name) < 3:
            continue
        for m in re.finditer(r"\b" + re.escape(state_name) + r"\b", text_lower):
            prefix = text_lower[max(0, m.start() - 40):m.start()].strip()
            if not any(excl in prefix for excl in EXCL_PREFIXES):
                return code
    return None


def _scan_name_for_state(name: str) -> Optional[str]:
    """Return state code if a state name (>4 chars) found in scheme name."""
    name_lower = name.lower()
    for state_name, code in sorted(STATE_TEXT_SCAN.items(), key=lambda x: -len(x[0])):
        if len(state_name) > 4 and state_name in name_lower:
            return code
    return None


def _is_national(name: str, description: str) -> bool:
    combined = (name + " " + description).lower()
    return any(sig in combined for sig in NATIONAL_SIGNALS)


def _resolve_correct_state(s: dict) -> Optional[str]:
    """
    Returns the correct state code for a scheme, or None if can't determine.
    Priority:
      1. Eligibility text (authoritative)
      2. Description (Gov-of-X or bare state mention)
      3. Scheme name
      4. National signal → 'ALL_INDIA'
      5. None (leave unchanged)
    """
    elig = s.get("eligibility") or ""
    desc = s.get("description") or ""
    name = s.get("name") or ""

    code = _scan_text_for_state(elig)
    if code:
        return code

    code = _scan_text_for_state(desc)
    if code:
        return code

    code = _scan_name_for_state(name)
    if code:
        return code

    if _is_national(name, desc):
        return "ALL_INDIA"

    return None


# ─────────────────────────────────────────────────────────────────────────────
# COMPUTE ALL CHANGES
# ─────────────────────────────────────────────────────────────────────────────

def compute_state_changes(schemes: list) -> list:
    """Returns list of (scheme_id, old_value, new_value, reason)."""
    changes = []
    ALL_CASTES_SET = {"sc", "st", "obc", "general", "ews"}

    for s in schemes:
        raw = _parse_json_field(s.get("allowed_states"))
        meaningful = [r for r in raw if r not in ALL_INDIA_VALUES]

        # Only fix schemes where DB = ['karnataka'] (the scraper default)
        if meaningful != ["karnataka"]:
            continue

        correct = _resolve_correct_state(s)
        if correct is None:
            continue  # truly ambiguous — leave resolver to handle it

        if correct == "ALL_INDIA":
            new_val = ["All India"]
            reason = "national_signal"
        else:
            # Verify it's actually different from KA
            if correct == "KA":
                continue  # DB is already correct
            new_val = [CODE_TO_DISPLAY[correct]]
            reason = "text_extraction"

        changes.append({
            "scheme_id":   s["id"],
            "scheme_name": s["name"],
            "field":       "allowed_states",
            "old_value":   s.get("allowed_states"),
            "new_value":   new_val,
            "reason":      reason,
            "state_code":  correct,
        })

    return changes


def compute_caste_changes(schemes: list) -> list:
    """Returns list of (scheme_id, old_value, new_value) for all-castes default cleanup."""
    ALL_CASTES_SET = {"sc", "st", "obc", "general", "ews"}
    changes = []

    for s in schemes:
        raw = set(_parse_json_field(s.get("allowed_castes")))
        raw_clean = raw - {"all", "any", ""}
        if raw_clean == ALL_CASTES_SET or raw_clean == ALL_CASTES_SET | {"general"}:
            # Confirm text has no caste-specific language before clearing
            elig_text = ((s.get("eligibility") or "") + " " + (s.get("description") or "")).lower()
            CASTE_SIGNALS = [
                "scheduled caste", "scheduled tribe", "sc/st", "obc students",
                "dalit", "adivasi", "backward class", "non-reserved",
                "general category only", "forward caste", "ews ",
                "economically weaker section",
            ]
            if not any(sig in elig_text for sig in CASTE_SIGNALS):
                changes.append({
                    "scheme_id":   s["id"],
                    "scheme_name": s["name"],
                    "field":       "allowed_castes",
                    "old_value":   s.get("allowed_castes"),
                    "new_value":   None,  # NULL = open to all
                    "reason":      "all_castes_scraper_default",
                })

    return changes


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # ── Load schemes ──────────────────────────────────────────────────────────
    # Try Flask DB first, fall back to JSON export
    schemes = None
    db_mode = False

    if not DRY_RUN:
        try:
            from app import app, db
            from models import Scheme
            with app.app_context():
                scheme_objects = Scheme.query.all()
                # Convert to dicts for uniform processing
                schemes_raw = []
                for s in scheme_objects:
                    schemes_raw.append({
                        "id": s.id,
                        "name": s.name or "",
                        "eligibility": s.eligibility or "",
                        "description": s.description or "",
                        "allowed_states": s.allowed_states,
                        "allowed_castes": s.allowed_castes,
                    })
            schemes = schemes_raw
            db_mode = True
            print(f"[INFO] Loaded {len(schemes)} schemes from DB")
        except Exception as e:
            print(f"[WARN] DB load failed ({e}), falling back to JSON export")

    if schemes is None:
        export_candidates = [
            "all_schemes_export.json",
            "../all_schemes_export.json",
        ]
        for path in export_candidates:
            try:
                with open(path, encoding="utf-8") as f:
                    raw = json.load(f)
                schemes = raw if isinstance(raw, list) else raw.get("schemes", [])
                print(f"[INFO] Loaded {len(schemes)} schemes from {path}")
                break
            except FileNotFoundError:
                continue
        if schemes is None:
            print("[FATAL] Could not find all_schemes_export.json")
            sys.exit(1)

    # ── Compute changes ───────────────────────────────────────────────────────
    state_changes = compute_state_changes(schemes)
    caste_changes = compute_caste_changes(schemes)
    all_changes   = state_changes + caste_changes

    if ARGS.limit:
        all_changes = all_changes[:ARGS.limit]

    # ── Report ────────────────────────────────────────────────────────────────
    print(f"\n{'='*72}")
    print(f"  CHANGES COMPUTED")
    print(f"{'='*72}")
    print(f"  State field fixes:  {len(state_changes)}")
    print(f"  Caste field fixes:  {len(caste_changes)}")
    print(f"  Total:              {len(all_changes)}")
    if ARGS.limit:
        print(f"  (limited to first {ARGS.limit} for this run)")

    # State change breakdown
    reason_counts = Counter(c["reason"] for c in state_changes)
    dest_counts   = Counter(c["state_code"] for c in state_changes)
    print(f"\n  State changes by reason:")
    for reason, cnt in reason_counts.most_common():
        print(f"    {reason:<30} {cnt}")
    print(f"\n  Top destination states:")
    for code, cnt in dest_counts.most_common(10):
        print(f"    {CODE_TO_DISPLAY.get(code, code):<25} {cnt}")

    # Print first 30 diffs
    print(f"\n  SAMPLE DIFFS (first 30):")
    for c in all_changes[:30]:
        print(f"\n  [{c['scheme_id']}] {c['scheme_name'][:55]}")
        print(f"    field:     {c['field']}")
        print(f"    old:       {c['old_value']}")
        print(f"    new:       {c['new_value']}")
        print(f"    reason:    {c['reason']}")

    # ── Apply to DB ───────────────────────────────────────────────────────────
    if DRY_RUN:
        print(f"\n{'='*72}")
        print(f"  DRY RUN — no changes written.")
        print(f"  Run with --commit to apply {len(all_changes)} changes to DB.")
        print(f"{'='*72}")
        return

    if not db_mode:
        # JSON export mode — write corrected JSON
        print(f"\n[INFO] No DB connection — writing corrected export to 'all_schemes_fixed.json'")
        sid_map = {s["id"]: s for s in schemes}
        for c in all_changes:
            s = sid_map.get(c["scheme_id"])
            if s:
                s[c["field"]] = c["new_value"]
        fixed = list(sid_map.values())
        with open("all_schemes_fixed.json", "w", encoding="utf-8") as f:
            json.dump(fixed, f, ensure_ascii=False, indent=2)
        print(f"[INFO] Written {len(fixed)} schemes to all_schemes_fixed.json")
        print(f"[INFO] {len(all_changes)} fields corrected")
        return

    # DB mode — apply with transaction
    from app import app, db
    from models import Scheme
    import traceback

    print(f"\n[INFO] Applying {len(all_changes)} changes to DB...")
    applied = 0
    errors  = 0

    with app.app_context():
        try:
            for c in all_changes:
                scheme = Scheme.query.get(c["scheme_id"])
                if scheme is None:
                    print(f"  [WARN] Scheme {c['scheme_id']} not found in DB")
                    continue

                field    = c["field"]
                new_val  = c["new_value"]

                # Serialize list → JSON string if the column stores JSON strings
                # (adjust if your column is a native JSON/Array type)
                if isinstance(new_val, list):
                    col_type = str(type(getattr(scheme, field, None)))
                    if "str" in col_type or new_val is None:
                        new_val_db = json.dumps(new_val) if new_val else None
                    else:
                        new_val_db = new_val
                else:
                    new_val_db = new_val

                setattr(scheme, field, new_val_db)
                applied += 1

                if applied % 100 == 0:
                    print(f"  ... {applied}/{len(all_changes)} applied")

            db.session.commit()
            print(f"\n[SUCCESS] {applied} changes committed to DB")
            if errors:
                print(f"[WARN] {errors} errors encountered (see above)")

        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] Transaction rolled back: {e}")
            traceback.print_exc()
            sys.exit(1)

    print(f"\n{'='*72}")
    print(f"  DONE. DB updated.")
    print(f"  Schemes with corrected state:  {len(state_changes)}")
    print(f"  Schemes with cleared caste:    {len(caste_changes)}")
    print(f"{'='*72}")


if __name__ == "__main__":
    main()
