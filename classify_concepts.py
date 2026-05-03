import json

# Load registry
with open('C:/yojanamitra_complete/concept_registry.json') as f:
    data = json.load(f)

concepts = data['concepts']

# BASE concepts - core identity/profile attributes
BASE_CONCEPTS = {
    'age',
    'gender', 
    'category',
    'state',
    'annual_income',
    'residence',
    'education_level',
    'occupation',
    'marital_status',
    'has_aadhaar',
    'has_bank_account',
    'is_citizen'
}

# Add type_group to each concept
for concept in concepts:
    concept_name = concept['concept']
    if concept_name in BASE_CONCEPTS:
        concept['type_group'] = 'base'
    else:
        concept['type_group'] = 'dynamic'

# Save updated registry
with open('C:/yojanamitra_complete/concept_registry.json', 'w') as f:
    json.dump(data, f, indent=2)

# Validation
base_count = sum(1 for c in concepts if c['type_group'] == 'base')
dynamic_count = sum(1 for c in concepts if c['type_group'] == 'dynamic')
missing = [c['concept'] for c in concepts if 'type_group' not in c]

print(f"Total concepts: {len(concepts)}")
print(f"BASE: {base_count}")
print(f"DYNAMIC: {dynamic_count}")
print(f"Missing type_group: {len(missing)}")

# Assertions
assert all("type_group" in c for c in concepts), "Some concepts missing type_group"
assert base_count == 12, f"Expected 12 base, got {base_count}"
print("All validations PASSED")

# List BASE concepts
print("\nBASE concepts:")
base_concepts = [c['concept'] for c in concepts if c['type_group'] == 'base']
for c in base_concepts:
    print(f"  - {c}")