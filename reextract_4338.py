import sys
import os
import json
sys.path.insert(0, '.')

from app import app, db, Condition
from app.pipeline.extractor import GeminiExtractor

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'PASTE_YOUR_GEMINI_API_KEY_HERE')

# Load the scheme data
JSON_FILE = 'all_schemes_fixed.json'
json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), JSON_FILE)
if not os.path.exists(json_path):
    json_path = 'C:/yojanamitra_complete/all_schemes_fixed.json'

with open(json_path, encoding='utf-8') as f:
    schemes = json.load(f)

# Find scheme 4338
scheme_data = None
for s in schemes:
    if s.get('id') == 4338:
        scheme_data = s
        break

if not scheme_data:
    print('Scheme 4338 not found in JSON')
    exit(1)

print('Found scheme:', scheme_data.get('name'))

# Extract using new extractor
extractor = GeminiExtractor(GEMINI_API_KEY)

# Build full text
text_parts = []
if scheme_data.get('eligibility'):
    text_parts.append(scheme_data['eligibility'])
if scheme_data.get('name'):
    text_parts.append(scheme_data['name'])
if scheme_data.get('description'):
    text_parts.append(scheme_data['description'])
full_text = ' '.join(text_parts)[:8000]

print('Extracting conditions...')
conditions, version, error, low_conf = extractor.extract(full_text, scheme_data)

print()
print('=== EXTRACTION RESULTS ===')
print('Version:', version)
print('Low confidence:', low_conf)
print('Error:', error)
print('Conditions:', len(conditions))
for c in conditions:
    src = c.get('source_fragment', '')
    print(f'  {c.get("condition_type"):6} | {c.get("field")} {c.get("operator")} {c.get("value")} (src: {src})')

# Save to DB
with app.app_context():
    Condition.query.filter_by(scheme_id=4338).delete()
    
    for cond in conditions:
        value = cond.get('value')
        if isinstance(value, (list, dict)):
            value_json = json.dumps(value)
        elif isinstance(value, (int, float, bool)):
            value_json = json.dumps(value)
        else:
            value_json = str(value)
        
        c = Condition(
            scheme_id=4338,
            field=cond.get('field', 'unknown'),
            operator=cond.get('operator', 'eq'),
            value=value_json,
            condition_type=cond.get('condition_type', 'soft'),
            confidence=cond.get('confidence', 0.5),
            source=version,
            source_fragment=cond.get('source_fragment', '')
        )
        db.session.add(c)
    
    db.session.commit()
    print()
    print('✅ Saved to DB')

