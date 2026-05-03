"""Trace AI conditions pipeline — run from project dir."""
import json
from scheme_rule_adapter import _build_ai_conditions, _SCHEME_CONDITIONS

# Check how many schemes produce AI conditions
total_with_conds = 0
total_ai = 0
for sid in _SCHEME_CONDITIONS:
    conds, disqs = _build_ai_conditions(int(sid))
    if conds or disqs:
        total_with_conds += 1
        total_ai += len(conds) + len(disqs)

print(f"Schemes in JSON: {len(_SCHEME_CONDITIONS)}")
print(f"Schemes generating AI conditions: {total_with_conds}")
print(f"Total AI condition objects: {total_ai}")

# Sample a few schemes
for sid in ['58', '100', '500', '1000']:
    entry = _SCHEME_CONDITIONS.get(sid, {})
    conds, disqs = _build_ai_conditions(int(sid))
    name = entry.get('_scheme_name', '?')[:60]
    print(f"\nScheme {sid}: {name}")
    print(f"  Raw AI: {entry.get('conditions', {})}")
    print(f"  Conf: {entry.get('confidence', 0)}")
    print(f"  Built: {len(conds)} conds, {len(disqs)} disqs")
    for c in conds:
        print(f"    COND: {c.field} {c.operator} {c.value} mand={c.is_mandatory}")
