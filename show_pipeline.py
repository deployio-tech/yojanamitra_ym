import sys
sys.path.insert(0, 'C:/yojanamitra_complete')

# Step 1: Show raw Gemini response
from app.engine.gemini_client import build_prompt, call_gemini, parse_gemini_response
from app.engine.concept_validator import validate_batch

fields = ['has_goat_farming_license', 'is_active_fisherman', 'owns_cattle_herd', 'is_rural_entrepreneur', 'has_poultry_farm']
prompt = build_prompt(fields)

print('='*60)
print('1. RAW GEMINI RESPONSE')
print('='*60)
raw = call_gemini(prompt)
print(raw[:2000] if len(raw) > 2000 else raw)
print('...' if len(raw) > 2000 else '')

print('\n' + '='*60)
print('2. PARSED OUTPUT (after JSON parser)')
print('='*60)
parsed = parse_gemini_response(raw)
for p in parsed:
    print(f"  field: {p['field']}")
    print(f"  concept: {p['concept']}")
    print(f"  question: {p['question']}")
    print()

print('='*60)
print('3. VALIDATOR DECISIONS')
print('='*60)
results = validate_batch(parsed)

print(f'ADD ({len(results["add"])}):')
for r in results['add']:
    print(f"  + {r['concept']} -> {r.get('field', '')}")

print(f'\nREUSE ({len(results["reuse"])}):')
for r in results['reuse']:
    print(f"  = {r['concept']} -> {r.get('field', '')}")

print(f'\nREJECT ({len(results["reject"])}):')
for r in results['reject']:
    print(f"  - {r.get('field', '')}: {r['reason']}")

print('\n' + '='*60)
print('SUMMARY')
print('='*60)
total = len(results['add']) + len(results['reuse']) + len(results['reject'])
print(f"Total processed: {total}")
print(f"Acceptance rate: {((len(results['add']) + len(results['reuse'])) / total * 100):.1f}%")