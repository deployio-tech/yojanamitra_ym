import json
from collections import OrderedDict

# Load registry
with open('C:/yojanamitra_complete/concept_registry.json') as f:
    data = json.load(f)

concepts = data['concepts']

# Remove duplicate concepts - keep first occurrence (which has 'gender' field)
seen = set()
unique = []

for c in concepts:
    name = c['concept']
    if name in seen:
        print(f"Skipping duplicate: {name}")
        continue
    seen.add(name)
    unique.append(c)

print(f"Original: {len(concepts)}, After dedup: {len(unique)}")

# Update data
data['concepts'] = unique

# Now classify
BASE_CONCEPTS = {
    'age', 'gender', 'category', 'state', 'annual_income',
    'residence', 'education_level', 'occupation', 'marital_status',
    'has_aadhaar', 'has_bank_account', 'is_citizen'
}

for c in data['concepts']:
    c['type_group'] = 'base' if c['concept'] in BASE_CONCEPTS else 'dynamic'

# Save
with open('C:/yojanamitra_complete/concept_registry.json', 'w') as f:
    json.dump(data, f, indent=2)

# Validate
base_count = sum(1 for c in data['concepts'] if c.get('type_group') == 'base')
print(f"BASE: {base_count}, DYNAMIC: {len(data['concepts']) - base_count}")

assert base_count == 12
print("PASSED")

print("\nBASE concepts:")
for c in sorted([c['concept'] for c in data['concepts'] if c.get('type_group') == 'base']):
    print(f"  - {c}")