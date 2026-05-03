"""
Classify ALL 8245 fields into 3 buckets (IMPROVED FILTERS)
"""
import json

print("=" * 80)
print("CLASSIFYING ALL 8245 FIELDS INTO 3 BUCKETS (IMPROVED)")
print("=" * 80)

# Load all fields
with open('all_question_fields.txt', 'r', encoding='utf-8') as f:
    all_fields = [line.strip() for line in f.readlines()]

print(f"Total fields: {len(all_fields)}")

# Load question set
with open('question_set_v2.json', 'r', encoding='utf-8') as f:
    question_set = json.load(f)

# Get base fields from clean questions (exclude fallback)
base_questions = question_set[:-1]
fallback_fields = question_set[-1]['fields']

base_fields = set()
for q in base_questions:
    for f in q['fields']:
        base_fields.add(f)

print(f"Base fields: {len(base_fields)}")
print(f"Fallback fields to classify: {len(fallback_fields)}")

# ============================================================
# IMPROVED FILTERS - More aggressive SYSTEM classification
# ============================================================

# More comprehensive reject list - ANY field containing these is SYSTEM
def is_likely_system_field(field):
    reject_patterns = [
        # Thresholds/limits
        "max", "min", "limit", "threshold", "cap", "ceiling",
        # Scoring/priority
        "score", "priority", "ranking", "grade", "level",
        # Eligibility checks
        "eligibility", "eligible", "qualified", "qualification",
        # Derived/computed
        "computed", "calculated", "derived", "estimated",
        # Validation/status
        "status", "verification", "validation", "verification",
        "approval", "authority", "certification", "accreditation",
        # Criteria/conditions
        "criteria", "condition", "requirement", "compliance",
        "adherence", "meets", "satisfied", "norms",
        # Internal config
        "type", "category", "classification", "component",
        "module", "internal", "config", "parameter", "setting",
        "code", "id", "no", "number", "serial",
        # Check/checks
        "check", "checklist", "scrutiny"
    ]
    field_lower = field.lower()
    for p in reject_patterns:
        if p in field_lower:
            return True
    return False

# Only true user-answerable fields are DYNAMIC
def is_truly_user_answerable(field):
    # Must be simple boolean/possession/attribute
    # Examples: has_*, is_*, owns_*, belongs_*, ...
    good_prefixes = [
        "has_", "is_", "owns_", "belongs_", "holds_",
        "has_valid_", "has_current_", "is_registered_",
        "is_engaged_", "is_employed_", "is_working_",
        "attached_", "enrolled_", "member_"
    ]
    field_lower = field.lower()
    for prefix in good_prefixes:
        if field_lower.startswith(prefix):
            return True
    
    # Also allow simple attributes
    simple_attrs = ["gender", "age", "occupation", "religion", 
                    "marital_status", "nationality", "state", "district",
                    "income", "caste"]
    for attr in simple_attrs:
        if field == attr or field == f"current_{attr}" or field == f"primary_{attr}":
            return True
    
    return False

# ============================================================
# CLASSIFY
# ============================================================
dynamic_fields = []
system_fields = []

print("\nClassifying fallback fields...")

for field in fallback_fields:
    if is_likely_system_field(field):
        system_fields.append(field)
    elif not is_truly_user_answerable(field):
        system_fields.append(field)
    else:
        dynamic_fields.append(field)

print(f"\nClassification complete!")
print(f"  BASE:    {len(base_fields)}")
print(f"  DYNAMIC: {len(dynamic_fields)}")
print(f"  SYSTEM:  {len(system_fields)}")

# Validation
total = len(base_fields) + len(dynamic_fields) + len(system_fields)
print(f"\nValidation: {total} total")

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

# Save
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