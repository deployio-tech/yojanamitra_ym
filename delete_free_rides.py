"""
Delete all 'free ride' schemes (zero classified_conditions) from the database and JSON.
Run from: c:\scrollyym\yojana-mitra-backend
"""
import json, sys, os

# Identify free-ride IDs from the JSON
with open('all_conditions_classified.json', encoding='utf-8') as f:
    data = json.load(f)

free_ride_ids = []
for sid, conds in data.items():
    entry = conds[0] if isinstance(conds, list) else conds
    if isinstance(entry, dict) and len(entry.get('classified_conditions', [])) == 0:
        free_ride_ids.append(int(sid))

print(f"Free-ride scheme IDs to delete ({len(free_ride_ids)}): {free_ride_ids}")

# --- 1. Remove from JSON ---
removed_json = []
for sid in free_ride_ids:
    if str(sid) in data:
        del data[str(sid)]
        removed_json.append(sid)

with open('all_conditions_classified.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)

print(f"Removed {len(removed_json)} entries from all_conditions_classified.json")

# --- 2. Remove from database via Flask app context ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db, Scheme

with app.app_context():
    deleted = 0
    for sid in free_ride_ids:
        scheme = Scheme.query.get(sid)
        if scheme:
            db.session.delete(scheme)
            deleted += 1
            print(f"  Deleted DB scheme {sid}: {scheme.name}")
        else:
            print(f"  Scheme {sid} not found in DB (may already be gone)")
    db.session.commit()
    print(f"\nDeleted {deleted} schemes from database.")

print("\nDone. Restart app.py to apply changes.")
