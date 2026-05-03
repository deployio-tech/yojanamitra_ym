"""
Classify ALL 8245 fields into 3 buckets:
1. BASE_FIELDS - Core questions (from clean question mappings)
2. DYNAMIC_FIELDS - User-answerable, scheme-specific
3. SYSTEM_FIELDS - Internal logic, derived, config
"""
import json

print("=" * 80)
print("CLASSIFYING ALL 8245 FIELDS INTO 3 BUCKETS")
print("=" * 80)

# Load all fields
with open('all_question_fields.txt', 'r', encoding='utf-8') as f:
    all_fields = [line.strip() for line in f.readlines()]

print(f"Total fields: {len(all_fields)}")

# Load question set and separate base from fallback
with open('question_set_v2.json', 'r', encoding='utf-8') as f:
    question_set = json.load(f)

# Last question is fallback - exclude it
base_questions = question_set[:-1]
fallback_fields = question_set[-1]['fields'] if question_set else []

print(f"Base questions (excluding fallback): {len(base_questions)}")
print(f"Fallback fields: {len(fallback_fields)}")

# Get base fields from clean questions only
base_fields = set()
for q in base_questions:
    for f in q['fields']:
        base_fields.add(f)

print(f"Base fields (from clean questions): {len(base_fields)}")

# ============================================================
# STEP 1: Hard rejection (SYSTEM)
# ============================================================
def is_likely_system_field(field):
    reject_keywords = [
        "max", "min", "limit", "threshold", "score",
        "eligibility", "priority", "relaxation",
        "calculated", "computed", "derived",
        "status_check", "validation", "criteria",
        "qualification_met", "satisfied", "meets",
        "requirement", "compliance", "adherence"
    ]
    field_lower = field.lower()
    for k in reject_keywords:
        if k in field_lower:
            return True
    return False

# ============================================================
# STEP 2: Human answerability test
# ============================================================
def is_human_answerable(field):
    bad_patterns = [
        "type", "category", "classification",
        "status", "condition", "criteria",
        "verification", "approval", "authority",
        "component", "module", "internal",
        "config", "parameter", "setting"
    ]
    field_lower = field.lower()
    for p in bad_patterns:
        if p in field_lower:
            return False
    return True

# ============================================================
# CLASSIFY REMAINING FIELDS (from fallback)
# ============================================================
dynamic_fields = []
system_fields = []

print("\nClassifying fallback fields...")

for field in fallback_fields:
    # Step 1: Check hard rejection
    if is_likely_system_field(field):
        system_fields.append(field)
    # Step 2: Check human answerability
    elif not is_human_answerable(field):
        system_fields.append(field)
    # Otherwise -> DYNAMIC
    else:
        dynamic_fields.append(field)

print(f"\nClassification complete!")
print(f"  BASE:    {len(base_fields)}")
print(f"  DYNAMIC: {len(dynamic_fields)}")
print(f"  SYSTEM:  {len(system_fields)}")

# Validation
total = len(base_fields) + len(dynamic_fields) + len(system_fields)
print(f"\nValidation: {total} total (expected {len(all_fields)})")

# Sanity checks
print("\n" + "=" * 80)
print("SANITY CHECKS:")
print("=" * 80)

if len(dynamic_fields) > 2000:
    print("WARNING: DYNAMIC > 2000")
else:
    print(f"OK - DYNAMIC count: {len(dynamic_fields)}")

if len(system_fields) < 3000:
    print("WARNING: SYSTEM < 3000")
else:
    print(f"OK - SYSTEM count: {len(system_fields)}")

# Show samples
print("\n" + "=" * 80)
print("SAMPLE DYNAMIC FIELDS (first 15):")
print("=" * 80)
for f in dynamic_fields[:15]:
    print(f"  {f}")

print("\n" + "=" * 80)
print("SAMPLE SYSTEM FIELDS (first 15):")
print("=" * 80)
for f in system_fields[:15]:
    print(f"  {f}")

# Save outputs
output = {
    "base_fields": sorted(list(base_fields)),
    "dynamic_fields": sorted(dynamic_fields),
    "system_fields": sorted(system_fields),
    "summary": {
        "total": len(all_fields),
        "base": len(base_fields),
        "dynamic": len(dynamic_fields),
        "system": len(system_fields)
    }
}

with open('field_classification.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("\nSaved to: field_classification.json")

print("\n" + "=" * 80)
print("FINAL RESULTS")
print("=" * 80)
print(f"BASE:    {len(base_fields)}")
print(f"DYNAMIC: {len(dynamic_fields)}")
print(f"SYSTEM:  {len(system_fields)}")
print(f"TOTAL:   {total}")