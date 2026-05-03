"""
remove_problematic_schemes.py
=============================
Removes schemes that had no eligibility text or failed condition extraction.
These schemes cause false positives (appear under "Fully Eligible" for everyone).

Run ONCE:
    python remove_problematic_schemes.py
"""

import json
import os
import sys

# ── Find problematic scheme IDs from scheme_conditions.json ──────────────────

SCHEMES_CONDITIONS_FILE = "scheme_conditions.json"
SCHEMES_EXPORT_FILE = "all_schemes_export.json"
SCHEMES_FIXED_FILE = "all_schemes_fixed.json"

BAD_STATUSES = {"no_text", "parse_error", "api_error", "max_retries"}

def find_problematic_ids():
    """Read scheme_conditions.json and return IDs with bad extraction status."""
    with open(SCHEMES_CONDITIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    bad_ids = set()
    for sid, entry in data.items():
        status = entry.get("_extraction_status", "")
        if status in BAD_STATUSES:
            bad_ids.add(sid)
    return bad_ids

def clean_conditions_json(bad_ids):
    """Remove bad entries from scheme_conditions.json."""
    with open(SCHEMES_CONDITIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    before = len(data)
    for sid in bad_ids:
        data.pop(sid, None)
    after = len(data)
    
    with open(SCHEMES_CONDITIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"  scheme_conditions.json: {before} -> {after} (removed {before - after})")

def clean_export_json(bad_ids):
    """Remove bad schemes from all_schemes_export.json."""
    for fname in [SCHEMES_EXPORT_FILE, SCHEMES_FIXED_FILE]:
        if not os.path.exists(fname):
            print(f"  {fname}: not found, skipping")
            continue
        with open(fname, "r", encoding="utf-8") as f:
            schemes = json.load(f)
        before = len(schemes)
        schemes = [s for s in schemes if str(s.get("id", "")) not in bad_ids]
        after = len(schemes)
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(schemes, f, ensure_ascii=False, indent=2)
        print(f"  {fname}: {before} -> {after} (removed {before - after})")

def clean_database(bad_ids):
    """Remove schemes from SQLite/Postgres database."""
    # Import Flask app to get db context
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app import app, db, Scheme, User
    
    int_ids = [int(sid) for sid in bad_ids]
    
    with app.app_context():
        # Delete schemes
        deleted = Scheme.query.filter(Scheme.id.in_(int_ids)).delete(synchronize_session=False)
        
        # Clear any user verified_schemes_data caches that reference these IDs
        users = User.query.all()
        cache_cleaned = 0
        for user in users:
            if user.verified_schemes_data:
                try:
                    cached = json.loads(user.verified_schemes_data)
                    if isinstance(cached, list):
                        cleaned = [s for s in cached if s.get("id") not in int_ids and str(s.get("id", "")) not in bad_ids]
                        if len(cleaned) != len(cached):
                            user.verified_schemes_data = json.dumps(cleaned)
                            cache_cleaned += 1
                except (json.JSONDecodeError, TypeError):
                    pass
            if user.verified_scheme_ids:
                try:
                    cached_ids = json.loads(user.verified_scheme_ids)
                    if isinstance(cached_ids, list):
                        cleaned_ids = [sid for sid in cached_ids if sid not in int_ids and str(sid) not in bad_ids]
                        if len(cleaned_ids) != len(cached_ids):
                            user.verified_scheme_ids = json.dumps(cleaned_ids)
                except (json.JSONDecodeError, TypeError):
                    pass
        
        db.session.commit()
        print(f"  Database: deleted {deleted} schemes, cleaned {cache_cleaned} user caches")

def main():
    print("=" * 60)
    print("YojanaMitra — Problematic Scheme Cleanup")
    print("=" * 60)
    
    bad_ids = find_problematic_ids()
    print(f"\nFound {len(bad_ids)} problematic schemes")
    print(f"IDs: {sorted(bad_ids, key=lambda x: int(x))[:20]}{'...' if len(bad_ids) > 20 else ''}")
    
    print("\n1. Cleaning scheme_conditions.json...")
    clean_conditions_json(bad_ids)
    
    print("\n2. Cleaning export JSON files...")
    clean_export_json(bad_ids)
    
    print("\n3. Cleaning database...")
    clean_database(bad_ids)
    
    print("\n✅ Cleanup complete!")
    print(f"   {len(bad_ids)} schemes removed from all sources.")

if __name__ == "__main__":
    main()
