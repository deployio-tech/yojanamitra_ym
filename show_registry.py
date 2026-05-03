import json

data = json.load(open('C:/yojanamitra_complete/concept_registry.json'))

# Show last 5 concepts (the ones we just added)
print('=== UPDATED REGISTRY (Last 5 Concepts) ===')
print()

last_5 = data['concepts'][-5:]
for c in last_5:
    concept_name = c['concept']
    question = c['question']
    concept_type = c.get('type', 'unknown')
    fields = c.get('fields', [])
    
    print(f'concept: {concept_name}')
    print(f'  question: {question}')
    print(f'  type: {concept_type}')
    print(f'  fields: {fields}')
    print()

# Show new field mappings
print('=== NEW FIELD MAPPINGS ===')
new_fields = ['has_goat_farming_license', 'is_active_fisherman', 'owns_cattle_herd', 'is_rural_entrepreneur', 'has_poultry_farm']
for f in new_fields:
    concept = data['field_to_concept'].get(f, 'NOT MAPPED')
    print(f'  {f} -> {concept}')

print()
print('Total concepts:', len(data['concepts']))
print('Total mappings:', len(data['field_to_concept']))