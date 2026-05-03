"""
Clean and Optimize DYNAMIC_FIELDS (1812 -> 700-1100)
With SEMANTIC MERGING and QUESTION-FIRST NORMALIZATION
"""
import json
import re
from collections import defaultdict

print("=" * 80)
print("CLEANING DYNAMIC FIELDS (WITH SEMANTIC MERGING)")
print("=" * 80)

# Load field classification
with open('field_classification.json', 'r', encoding='utf-8') as f:
    classification = json.load(f)

base_fields = set(classification['base_fields'])
dynamic_fields = classification['dynamic_fields']
system_fields = set(classification['system_fields'])

print(f"Original: BASE={len(base_fields)}, DYNAMIC={len(dynamic_fields)}, SYSTEM={len(system_fields)}")

# ============================================================
# STEP 1: SYSTEM HARD FILTER
# ============================================================
def is_system_field(field):
    """Check if field represents RULE, not USER FACT"""
    rule_patterns = [
        "max", "min", "limit", "threshold", "cap", "ceiling",
        "score", "priority", "ranking", "grade",
        "eligibility", "eligible", "qualified", "qualification",
        "computed", "calculated", "derived", "estimated",
        "criteria", "condition", "requirement", "compliance",
        "status_check", "verification", "validation",
        "approval", "authority", "certification",
        "meets", "satisfied", "norms"
    ]
    field_lower = field.lower()
    for p in rule_patterns:
        if p in field_lower:
            return True
    return False

# ============================================================
# STEP 2: HUMAN ANSWER TEST
# ============================================================
def is_human_answerable(field):
    """Can a normal user answer this directly in one sentence?"""
    # Bad patterns - user can't answer directly
    bad_patterns = [
        "type", "classification", "category", "component",
        "verification", "approval", "authority", "accreditation",
        "affiliation", "recognition", "status", "check",
        "module", "internal", "config", "parameter",
        "code", "number", "id", "serial"
    ]
    field_lower = field.lower()
    for p in bad_patterns:
        if p in field_lower:
            return False
    return True

# ============================================================
# STEP 3: GENERATE QUESTION (NORMALIZE)
# ============================================================
def generate_question(field):
    """Generate natural user question from field name"""
    field = field.lower()
    
    # Remove common prefixes
    for prefix in ["has_", "is_", "holds_", "owns_"]:
        if field.startswith(prefix):
            field = field[len(prefix):]
    
    # Clean up
    field = field.replace("_", " ")
    
    # Capitalize
    field = field.strip().title()
    
    # Common question patterns
    if field in ["Aadhaar", "Aadhar"]:
        return "Do you have an Aadhaar card?"
    if field in ["Bank Account"]:
        return "Do you have a bank account?"
    if field in ["Ration Card"]:
        return "Do you have a ration card?"
    if field in ["Pan Card", "Pan"]:
        return "Do you have a PAN card?"
    if field in ["Disability Certificate"]:
        return "Do you have a disability certificate?"
    if field in ["Land", "Agricultural Land"]:
        return "Do you own agricultural land?"
    if field in ["Farmer"]:
        return "Are you a farmer?"
    if field in ["Student"]:
        return "Are you a student?"
    if field in ["Widow"]:
        return "Are you a widow?"
    if field in ["Orphan"]:
        return "Are you an orphan?"
    if field in ["Minority"]:
        return "Do you belong to a minority community?"
    if field in ["Tribal"]:
        return "Are you a tribal person?"
    if field in ["Bpl"]:
        return "Are you from a BPL family?"
    if field in ["Ews"]:
        return "Are you from Economically Weaker Section?"
    if field in ["Nri"]:
        return "Are you an NRI?"
    if field in ["Pensioner"]:
        return "Are you a pensioner?"
    if field in ["Construction Worker"]:
        return "Are you a construction worker?"
    if field in ["Shg", "Self Help Group"]:
        return "Are you a member of Self Help Group?"
    if field in ["Fisherman"]:
        return "Are you a fisherman?"
    if field in ["Handloom Worker"]:
        return "Are you a handloom worker?"
    if field in ["Disability", "Disabled"]:
        return "Are you a person with disability?"
    if "certificate" in field.lower():
        return f"Do you have a {field}?"
    if "card" in field.lower():
        return f"Do you have a {field}?"
    if "license" in field.lower():
        return f"Do you have a {field}?"
    if "membership" in field.lower():
        return f"Do you have {field}?"
    if "registration" in field.lower():
        return f"Are you registered for {field}?"
    if "member" in field.lower():
        return f"Are you a member of {field}?"
    
    return f"What is your {field}?"

# ============================================================
# PROCESS ALL DYNAMIC FIELDS
# ============================================================
moved_to_system = []
moved_to_base = []
merged_groups = {}  # key = question, value = [original fields]
final_dynamic = []

print("\n[1/5] Applying system filter...")
for field in dynamic_fields:
    if is_system_field(field):
        moved_to_system.append(field)
        system_fields.add(field)
    else:
        final_dynamic.append(field)

print(f"  After system filter: {len(final_dynamic)} fields")

print("\n[2/5] Applying human answer test...")
remaining = []
for field in final_dynamic:
    if not is_human_answerable(field):
        moved_to_system.append(field)
        system_fields.add(field)
    else:
        remaining.append(field)

print(f"  After human answer test: {len(remaining)} fields")

print("\n[3/5] Generating questions for each field...")
field_to_question = {}
question_to_fields = defaultdict(list)

for field in remaining:
    question = generate_question(field)
    field_to_question[field] = question
    question_to_fields[question].append(field)

print(f"  Generated {len(question_to_fields)} unique questions")

print("\n[4/5] Merging duplicates by question...")
# Keep one representative field per question
for question, fields in question_to_fields.items():
    # Pick the most basic field as representative
    # Prefer: has_*, is_*, holds_*
    representative = fields[0]
    for f in fields:
        if f.startswith("has_") and not representative.startswith("has_"):
            representative = f
        elif f == "is_disabled" and representative != "is_disabled":
            representative = f
    
    merged_groups[question] = fields
    final_dynamic.append(representative)

print(f"  After merging: {len(final_dynamic)} unique fields")

print("\n[5/5] Checking base overlap...")
to_move_to_base = []
for field in final_dynamic:
    # Check if field maps to universal base concepts
    universal_concepts = ["age", "gender", "income", "caste", "category", 
                         "state", "residence", "occupation", "religion",
                         "education", "marital", "nationality", "citizen"]
    field_lower = field.lower()
    for concept in universal_concepts:
        if field_lower == concept or field_lower.startswith(concept + "_"):
            # Could be base - check if it's really a universal field
            if field in base_fields or field_lower in ["age", "gender", "income", 
                                                       "caste", "category", "state",
                                                       "occupation", "religion", "education",
                                                       "marital_status", "nationality"]:
                to_move_to_base.append(field)
                break

for field in to_move_to_base:
    final_dynamic.remove(field)
    moved_to_base.append(field)
    base_fields.add(field)

print(f"  Moved to base: {len(to_move_to_base)} fields")

# ============================================================
# VALIDATION
# ============================================================
print("\n" + "=" * 80)
print("VALIDATION")
print("=" * 80)

# Remove duplicates from final_dynamic
final_dynamic_unique = list(set(final_dynamic))
duplicates_removed = len(final_dynamic) - len(final_dynamic_unique)
print(f"Duplicates removed: {duplicates_removed}")

total_accounted = len(final_dynamic_unique) + len(moved_to_system) + len(moved_to_base)
print(f"Total accounted: {total_accounted} (expected {len(dynamic_fields)})")

if total_accounted != len(dynamic_fields):
    print("ERROR: Field count mismatch!")
else:
    print("Validation: PASSED")

# Sanity checks
print(f"\nFinal counts:")
print(f"  BASE: {len(base_fields)}")
print(f"  DYNAMIC: {len(final_dynamic_unique)}")
print(f"  SYSTEM: {len(system_fields)}")

if len(final_dynamic_unique) > 1200:
    print("WARNING: DYNAMIC > 1200")
elif len(final_dynamic_unique) < 600:
    print("WARNING: DYNAMIC < 600")
else:
    print("DYNAMIC in target range: 600-1200")

# Show sample merged groups
print("\n" + "=" * 80)
print("SAMPLE MERGED GROUPS (first 10):")
print("=" * 80)
for i, (q, fields) in enumerate(list(merged_groups.items())[:10]):
    print(f"\n{i+1}. Question: {q}")
    print(f"   Fields merged: {len(fields)}")
    print(f"   Examples: {fields[:3]}")

# Show sample final dynamic
print("\n" + "=" * 80)
print("SAMPLE FINAL DYNAMIC FIELDS (first 20):")
print("=" * 80)
for f in sorted(final_dynamic_unique)[:20]:
    print(f"  {f}")

# Save outputs
output = {
    "final_dynamic_fields": sorted(final_dynamic_unique),
    "moved_to_system": sorted(moved_to_system),
    "moved_to_base": sorted(moved_to_base),
    "merged_groups": {k: v for k, v in list(merged_groups.items())[:50]},  # First 50 for brevity
    "summary": {
        "original_dynamic": len(dynamic_fields),
        "final_dynamic": len(final_dynamic_unique),
        "moved_to_system": len(moved_to_system),
        "moved_to_base": len(moved_to_base),
        "duplicates_removed": duplicates_removed,
        "total_check": total_accounted
    }
}

with open('dynamic_fields_cleaned.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("\nSaved to: dynamic_fields_cleaned.json")

print("\n" + "=" * 80)
print("FINAL RESULTS")
print("=" * 80)
print(f"DYNAMIC: {len(final_dynamic_unique)}")
print(f"SYSTEM: {len(system_fields)}")
print(f"BASE: {len(base_fields)}")