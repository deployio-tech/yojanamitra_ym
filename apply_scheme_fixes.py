"""
apply_scheme_fixes.py
=====================
Reads all_schemes_fixed.json (produced by fix_scraper_defaults.py --commit)
and updates allowed_states + allowed_castes in yojanamitra.db directly via SQLite.

Does NOT require Flask app context or models.py — uses raw SQLite.

Usage:
  python apply_scheme_fixes.py --dry-run     # preview, no writes
  python apply_scheme_fixes.py --commit      # write to DB

Requires:
  - all_schemes_fixed.json   (produced by fix_scraper_defaults.py --commit)
  - yojanamitra.db           (your SQLite database)
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--dry-run",   action="store_true", default=True)
parser.add_argument("--commit",    action="store_true")
parser.add_argument("--db",        type=str, default="yojanamitra.db")
parser.add_argument("--fixed-json",type=str, default="all_schemes_fixed.json")
ARGS = parser.parse_args()
DRY_RUN = not ARGS.commit

# ─────────────────────────────────────────────────────────────────────────────

def load_fixed(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    schemes = data if isinstance(data, list) else data.get("schemes", [])
    return {s["id"]: s for s in schemes}

def load_db_states(conn) -> dict:
    """Load current allowed_states + allowed_castes from DB, keyed by id."""
    # Auto-detect table name (SQLAlchemy default is lowercase class name)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    print(f"[INFO] Tables in DB: {tables}")

    table = None
    for candidate in ("scheme", "schemes", "Scheme"):
        if candidate in tables:
            table = candidate
            break
    if table is None:
        print(f"[FATAL] No scheme table found. Tables: {tables}")
        sys.exit(1)

    print(f"[INFO] Using table: '{table}'")
    cur = conn.execute(f"SELECT id, allowed_states, allowed_castes FROM {table}")
    return {row[0]: {"allowed_states": row[1], "allowed_castes": row[2]}
            for row in cur.fetchall()}, table

def serialize(val) -> str | None:
    """Serialize a Python list to JSON string for DB storage, or None."""
    if val is None:
        return None
    if isinstance(val, list):
        return json.dumps(val, ensure_ascii=False)
    return str(val)

# ─────────────────────────────────────────────────────────────────────────────

def main():
    fixed_path = Path(ARGS.fixed_json)
    db_path    = Path(ARGS.db)

    if not fixed_path.exists():
        print(f"[FATAL] {fixed_path} not found. Run fix_scraper_defaults.py --commit first.")
        sys.exit(1)
    if not db_path.exists():
        print(f"[FATAL] {db_path} not found. Check --db path.")
        sys.exit(1)

    print(f"[INFO] Loading fixed JSON from {fixed_path} ...")
    fixed = load_fixed(str(fixed_path))
    print(f"[INFO] {len(fixed)} schemes loaded from fixed JSON")

    conn = sqlite3.connect(str(db_path))
    print(f"[INFO] Connected to {db_path}")

    db_current, table = load_db_states(conn)
    print(f"[INFO] {len(db_current)} schemes found in DB")

    # ── Compute diffs ─────────────────────────────────────────────────────────
    state_updates = []
    caste_updates = []

    for sid, fixed_scheme in fixed.items():
        db_row = db_current.get(sid)
        if db_row is None:
            continue  # scheme not in DB (shouldn't happen)

        # allowed_states
        fixed_states = fixed_scheme.get("allowed_states")
        db_states_raw = db_row["allowed_states"]
        db_states_parsed = json.loads(db_states_raw) if db_states_raw else None

        if fixed_states != db_states_parsed:
            state_updates.append({
                "id":      sid,
                "name":    fixed_scheme.get("name", "")[:60],
                "old":     db_states_parsed,
                "new":     fixed_states,
            })

        # allowed_castes
        fixed_castes = fixed_scheme.get("allowed_castes")
        db_castes_raw = db_row["allowed_castes"]
        db_castes_parsed = json.loads(db_castes_raw) if db_castes_raw else None

        if fixed_castes != db_castes_parsed:
            caste_updates.append({
                "id":      sid,
                "name":    fixed_scheme.get("name", "")[:60],
                "old":     db_castes_parsed,
                "new":     fixed_castes,
            })

    total = len(state_updates) + len(caste_updates)

    print(f"\n{'='*70}")
    print(f"  DIFF SUMMARY")
    print(f"{'='*70}")
    print(f"  allowed_states changes: {len(state_updates)}")
    print(f"  allowed_castes changes: {len(caste_updates)}")
    print(f"  Total:                  {total}")

    # Print sample diffs
    print(f"\n  SAMPLE STATE CHANGES (first 20):")
    for u in state_updates[:20]:
        print(f"  [{u['id']}] {u['name']}")
        print(f"    old: {u['old']}")
        print(f"    new: {u['new']}")

    if caste_updates:
        print(f"\n  SAMPLE CASTE CHANGES (first 10):")
        for u in caste_updates[:10]:
            print(f"  [{u['id']}] {u['name']}")
            print(f"    old: {u['old']}")
            print(f"    new: {u['new']}")

    if DRY_RUN:
        print(f"\n{'='*70}")
        print(f"  DRY RUN — no changes written.")
        print(f"  Run with --commit to apply {total} changes to {db_path}.")
        print(f"{'='*70}")
        conn.close()
        return

    # ── Apply changes ─────────────────────────────────────────────────────────
    print(f"\n[INFO] Applying {total} changes to {db_path} ...")

    try:
        cur = conn.cursor()

        # Batch state updates
        for i, u in enumerate(state_updates):
            new_val = serialize(u["new"])
            cur.execute(f"UPDATE {table} SET allowed_states = ? WHERE id = ?",
                        (new_val, u["id"]))
            if (i + 1) % 200 == 0:
                print(f"  ... {i+1}/{len(state_updates)} state updates")

        # Batch caste updates
        for i, u in enumerate(caste_updates):
            new_val = serialize(u["new"])
            cur.execute(f"UPDATE {table} SET allowed_castes = ? WHERE id = ?",
                        (new_val, u["id"]))
            if (i + 1) % 50 == 0:
                print(f"  ... {i+1}/{len(caste_updates)} caste updates")

        conn.commit()
        print(f"\n[SUCCESS] {total} changes committed to {db_path}")
        print(f"  State fields updated: {len(state_updates)}")
        print(f"  Caste fields updated: {len(caste_updates)}")

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Rolled back. {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

    print(f"\n{'='*70}")
    print(f"  DONE.")
    print(f"  Restart your Flask app to pick up the new DB values.")
    print(f"  The resolver will now have accurate state data and will no longer")
    print(f"  need to override incorrect Karnataka defaults for 3,736 schemes.")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
