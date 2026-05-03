import json
import sys
sys.path.insert(0, 'C:/yojanamitra_complete')

# Validate concept registry
with open('C:/yojanamitra_complete/concept_registry.json') as f:
    data = json.load(f)

print("="*50)
print("VALIDATION: Concept Registry")
print("="*50)

concepts = data['concepts']
field_to_concept = data['field_to_concept']

# 1. Check all concepts have type
missing_type = []
for c in concepts:
    if 'type' not in c:
        missing_type.append(c['concept'])

status = "PASS" if not missing_type else "FAIL"
print(f"1. All concepts have type: {status}")
if missing_type:
    print(f"   Missing type: {missing_type[:10]}")

# 2. Check choice types have options
no_options = []
for c in concepts:
    if c.get('type') in ('single_choice', 'multi_choice') and not c.get('options'):
        no_options.append(c['concept'])

status = "PASS" if not no_options else "FAIL"
print(f"2. Choice types have options: {status}")
if no_options:
    print(f"   Missing options: {no_options[:10]}")

# 3. Check field_to_concept coverage
print(f"3. Field mappings count: {len(field_to_concept)} (expected: 679)")
status = "PASS" if len(field_to_concept) >= 679 else "FAIL"
print(f"   Coverage check: {status}")

# 4. Show type distribution
type_counts = {}
for c in concepts:
    t = c.get('type', 'unknown')
    type_counts[t] = type_counts.get(t, 0) + 1

print(f"\n4. Type distribution:")
for t, count in sorted(type_counts.items()):
    print(f"   {t}: {count}")

# 5. Test normalization
print("\n" + "="*50)
print("VALIDATION: Normalization")
print("="*50)

from app.engine.normalize import (
    normalize_answer, TRUE_SET, FALSE_SET, clean_number, normalize_multi_choice
)

# Test boolean
print("\nBoolean normalization:")
tests = [('yes', True), ('Yes', True), ('true', True), ('1', True), ('no', False), ('', None)]
for inp, expected in tests:
    result = normalize_answer(inp, 'has_aadhaar')
    status = "PASS" if result == expected else f"FAIL (got {result})"
    print(f"   '{inp}' -> {result} {status}")

# Test number cleaning
print("\nNumber cleaning:")
num_tests = [('150000', 150000.0), ('1.5 lakh', 150000.0), ('2.5 crore', 25000000.0), ('1,50,000', 150000.0)]
for inp, expected in num_tests:
    result = clean_number(inp)
    status = "PASS" if result == expected else f"FAIL (got {result})"
    print(f"   '{inp}' -> {result} {status}")

# Test single choice
print("\nSingle choice normalization:")
sc_tests = [('MALE', 'male'), ('General', 'general'), ('  OBC  ', 'obc')]
for inp, expected in sc_tests:
    result = normalize_answer(inp, 'gender')
    status = "PASS" if result == expected else f"FAIL (got {result})"
    print(f"   '{inp}' -> {result} {status}")

# Test multi choice
print("\nMulti choice normalization:")
mc_tests = [('sc, st, obc', {'sc', 'st', 'obc'}), (['sc', 'st'], {'sc', 'st'})]
for inp, expected in mc_tests:
    result = normalize_answer(inp, 'categories')
    status = "PASS" if result == expected else f"FAIL (got {result})"
    print(f"   {inp} -> {result} {status}")

print("\n" + "="*50)
print("VALIDATION: Complete")
print("="*50)