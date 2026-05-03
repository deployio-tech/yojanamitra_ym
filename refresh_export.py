"""
refresh_export.py
=================
Copies the corrected allowed_states and allowed_castes from all_schemes_fixed.json
back into all_schemes_export.json so the --standalone test harness uses accurate data.

Run: python refresh_export.py
"""
import json, sys
from pathlib import Path

FIXED  = Path("all_schemes_fixed.json")
EXPORT = Path("all_schemes_export.json")

if not FIXED.exists():
    print(f"[FATAL] {FIXED} not found. Run: python fix_scraper_defaults.py --commit")
    sys.exit(1)
if not EXPORT.exists():
    print(f"[FATAL] {EXPORT} not found.")
    sys.exit(1)

print(f"[INFO] Loading {FIXED} ...")
with open(FIXED, encoding="utf-8") as f:
    fixed_data = json.load(f)
fixed_map = {s["id"]: s for s in (fixed_data if isinstance(fixed_data, list) else fixed_data.get("schemes", []))}

print(f"[INFO] Loading {EXPORT} ...")
with open(EXPORT, encoding="utf-8") as f:
    export_data = json.load(f)
export_list = export_data if isinstance(export_data, list) else export_data.get("schemes", [])

state_updated = 0
caste_updated = 0
for s in export_list:
    fixed = fixed_map.get(s["id"])
    if fixed is None:
        continue
    if s.get("allowed_states") != fixed.get("allowed_states"):
        s["allowed_states"] = fixed["allowed_states"]
        state_updated += 1
    if s.get("allowed_castes") != fixed.get("allowed_castes"):
        s["allowed_castes"] = fixed["allowed_castes"]
        caste_updated += 1

out = export_list if isinstance(export_data, list) else {"schemes": export_list}
with open(EXPORT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"[SUCCESS] {EXPORT} updated:")
print(f"  allowed_states refreshed: {state_updated}")
print(f"  allowed_castes refreshed: {caste_updated}")
print(f"  The --standalone harness will now use accurate state data.")
