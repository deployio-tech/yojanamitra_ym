import json

# Load registry
with open('C:/yojanamitra_complete/concept_registry.json') as f:
    data = json.load(f)

concepts = data['concepts']

# Remove duplicate gender concepts - keep the one with more fields
seen_concepts = set()
unique_concepts = []

for c in concepts:
    name = c['concept']
    if name == 'gender' and name in seen_concepts:
        # Skip duplicate - keep first occurrence or the one with more fields?
        # Let's keep the one with 'gender' field (more useful)
        if 'gender' not in c.get('fields', []):
            continue  # Skip this one
    unique_concepts.append(c)
    seen_concepts.add(name)

# Update concepts list
data['concepts'] = unique_concepts

# Save
with open('C:/yojanamitra_complete/concept_registry.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f"Total concepts: {len(data['concepts'])}")

# Now run the classification again
BASE_CONCEPTS = {
    'age', 'gender', 'category', 'state', 'annual_income',
    'residence', 'education_level', 'occupation', 'marital_status',
    'has_aadhaar', 'has_bank_account', 'is_citizen'
}

for concept in data['concepts']:
    concept['concept'] = concept['concept']  # Ensure consistent
    if concept['concept'] in BASE_CONCEPTS:
        concept['type_group'] = 'base'
    else:
        concept['type_group'] = 'dynamic'

# Save again
with open('C:/yojanamitra_complete/concept_registry.json', 'w') as f:
    json.dump(data, f, indent=2)

# Final validation
concepts = data['concepts']
base_count = sum(1 for c in concepts if c.get('type_group') == 'base')
dynamic_count = sum(1 for c in concepts if c.get('type_group') == 'dynamic')

print(f"BASE: {base_count}")
print(f"DYNAMIC: {dynamic_count}")

assert all("type_group" in c for c in concepts)
assert base_count == 12, f"Expected 12 base, got {base_count}"
print("All validations PASSED")

print("\nBASE concepts:")
for c in sorted([c['concept'] for c in concepts if c.get('type_group') == 'base']):
    print(f"  - {c}")