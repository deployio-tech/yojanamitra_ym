import json
import os
from collections import defaultdict
from typing import Dict, List, Any, Set

# Load the dataset
file_path = "all_schemes_export.json"

print("=" * 80)
print("COMPREHENSIVE DATASET ANALYSIS: all_schemes_export.json")
print("=" * 80)

# Check if file exists
if not os.path.exists(file_path):
    print(f"ERROR: File not found at {file_path}")
    exit(1)

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except json.JSONDecodeError as e:
    print(f"ERROR: Invalid JSON format - {e}")
    exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    exit(1)

# Ensure we have a list
if isinstance(data, dict):
    # If it's wrapped in a key, try to find the schemes
    if 'schemes' in data:
        schemes = data['schemes']
    elif 'data' in data:
        schemes = data['data']
    else:
        schemes = [data]
else:
    schemes = data

if not isinstance(schemes, list):
    print(f"ERROR: Expected list of schemes, got {type(schemes)}")
    exit(1)

print(f"\n1. TOTAL SCHEMES: {len(schemes)}")

# Analyze field structure
all_keys = set()
fields_by_occurrence = defaultdict(int)
field_types = defaultdict(set)
field_nulls = defaultdict(int)
field_empties = defaultdict(int)
field_defaults = defaultdict(lambda: defaultdict(int))

for idx, scheme in enumerate(schemes):
    if not isinstance(scheme, dict):
        print(f"WARNING: Scheme at index {idx} is not a dict, skipping")
        continue
    
    for key, value in scheme.items():
        all_keys.add(key)
        fields_by_occurrence[key] += 1
        
        # Track type
        if value is None:
            field_types[key].add('null')
            field_nulls[key] += 1
        elif isinstance(value, bool):
            field_types[key].add('boolean')
        elif isinstance(value, int):
            field_types[key].add('integer')
        elif isinstance(value, float):
            field_types[key].add('float')
        elif isinstance(value, str):
            field_types[key].add('string')
            if value.strip() == '':
                field_empties[key] += 1
            field_defaults[key][value] += 1
        elif isinstance(value, list):
            field_types[key].add('array')
            field_defaults[key][f'[array_len={len(value)}]'] += 1
        elif isinstance(value, dict):
            field_types[key].add('object')
        else:
            field_types[key].add(str(type(value)))

print(f"\n2. DATASET STRUCTURE")
print(f"   Total unique fields: {len(all_keys)}")
print(f"\n   Field names and occurrences:")
sorted_fields = sorted(fields_by_occurrence.items(), key=lambda x: -x[1])
for field, count in sorted_fields:
    coverage = (count / len(schemes)) * 100
    print(f"   - {field}: {count}/{len(schemes)} ({coverage:.1f}%)")

print(f"\n3. FIELD DATA TYPES")
for field, types in sorted(field_types.items()):
    types_str = ", ".join(sorted(list(types)))
    print(f"   - {field}: {types_str}")

print(f"\n4. MISSING AND NULL FIELDS ANALYSIS")
print(f"\n   Fields with null/missing values:")
null_issues = []
for field in sorted(fields_by_occurrence.keys()):
    total = len(schemes)
    occurrences = fields_by_occurrence[field]
    missing = total - occurrences
    null_count = field_nulls.get(field, 0)
    empty_count = field_empties.get(field, 0)
    
    if missing > 0 or null_count > 0 or empty_count > 0:
        issue_pct = ((missing + null_count + empty_count) / total) * 100
        null_issues.append((field, missing, null_count, empty_count, issue_pct))

# Sort by severity
null_issues.sort(key=lambda x: -x[4])
for field, missing, null_count, empty_count, pct in null_issues:
    print(f"   - {field}:")
    print(f"     Missing (not in dict): {missing}")
    print(f"     Null values: {null_count}")
    print(f"     Empty strings: {empty_count}")
    print(f"     Total problematic: {missing + null_count + empty_count}/{len(schemes)} ({pct:.1f}%)")

print(f"\n5. ELIGIBILITY CRITERIA COMPLETENESS")
eligibility_fields = ['eligibility_criteria', 'eligibility', 'criteria', 'requirements']
eligibility_present = 0
eligibility_complete = 0
eligibility_samples = []

for scheme in schemes:
    has_eligibility = False
    is_complete = False
    
    for elig_field in eligibility_fields:
        if elig_field in scheme:
            has_eligibility = True
            value = scheme.get(elig_field)
            if value and value not in [None, '', []]:
                is_complete = True
            if not eligibility_samples and is_complete:
                eligibility_samples.append((elig_field, value))
            break
    
    if has_eligibility:
        eligibility_present += 1
    if is_complete:
        eligibility_complete += 1

print(f"   Schemes with eligibility field: {eligibility_present}/{len(schemes)} ({(eligibility_present/len(schemes))*100:.1f}%)")
print(f"   Schemes with complete eligibility: {eligibility_complete}/{len(schemes)} ({(eligibility_complete/len(schemes))*100:.1f}%)")
print(f"   Schemes with incomplete eligibility: {eligibility_present - eligibility_complete}/{len(schemes)} ({((eligibility_present-eligibility_complete)/len(schemes))*100:.1f}%)")

print(f"\n6. FIELD-BY-FIELD COMPLETENESS SUMMARY")
print(f"   (showing % of schemes with data in each field)\n")
completeness = []
for field, count in sorted_fields:
    pct = (count / len(schemes)) * 100
    completeness.append((field, pct, count))

# Sort by completeness
completeness.sort(key=lambda x: -x[1])
for field, pct, count in completeness:
    status = "✓" if pct >= 90 else "⚠" if pct >= 70 else "✗"
    print(f"   {status} {field}: {pct:6.1f}% ({count})")

print(f"\n7. DATA ANOMALIES & PATTERNS")

# Check for anomalies
print(f"\n   Anomaly checks:")
anomalies = []

# Check for schemes with very few fields
field_counts = [len(s) for s in schemes if isinstance(s, dict)]
empty_schemes = sum(1 for c in field_counts if c == 0)
low_field_schemes = sum(1 for c in field_counts if 0 < c < 3)
if empty_schemes > 0:
    anomalies.append(f"   - {empty_schemes} completely empty schemes")
if low_field_schemes > 0:
    anomalies.append(f"   - {low_field_schemes} schemes with fewer than 3 fields")

# Check for duplicate schemes by name
scheme_names = defaultdict(int)
duplicate_names = 0
for scheme in schemes:
    if isinstance(scheme, dict):
        name_field = scheme.get('name') or scheme.get('scheme_name') or scheme.get('title')
        if name_field:
            scheme_names[name_field] += 1

for name, count in scheme_names.items():
    if count > 1:
        duplicate_names += 1

if duplicate_names > 0:
    anomalies.append(f"   - {duplicate_names} duplicate scheme names (same name appears multiple times)")

# Check for extremely long strings
long_field_issues = defaultdict(int)
for scheme in schemes:
    if isinstance(scheme, dict):
        for key, value in scheme.items():
            if isinstance(value, str) and len(value) > 5000:
                long_field_issues[key] += 1

if long_field_issues:
    for field, count in long_field_issues.items():
        anomalies.append(f"   - {count} schemes have extremely long text in '{field}' field (>5000 chars)")

if not anomalies:
    print("   - No major anomalies detected")
else:
    for anomaly in anomalies:
        print(anomaly)

print(f"\n8. SAMPLE SCHEMES (First 5)")
print("=" * 80)
for idx, scheme in enumerate(schemes[:5], 1):
    print(f"\nSCHEME {idx}:")
    if not isinstance(scheme, dict):
        print(f"  (Not a dict: {type(scheme).__name__})")
        continue
    
    for key, value in sorted(scheme.items()):
        if isinstance(value, str):
            display_value = value[:100] + "..." if len(value) > 100 else value
        elif isinstance(value, (list, dict)):
            display_value = f"[{type(value).__name__} with {len(value)} items]"
        else:
            display_value = str(value)
        print(f"  {key}: {display_value}")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
