import json

with open('C:/yojanamitra_complete/concept_registry.json') as f:
    data = json.load(f)

# Show sample fields for each concept
for c in data['concepts']:
    fields = c['fields']
    # Determine type based on field patterns
    has_is_prefix = any(f.startswith('is_') for f in fields)
    has_number = any(f in ['age', 'income', 'land', 'area', 'count', 'percentage'] for f in fields)
    
    if has_number:
        typ = "number"
    elif has_is_prefix:
        typ = "boolean"
    else:
        typ = "single_choice"
    
    print(f"{c['concept']}: {typ} - {fields[:3]}")