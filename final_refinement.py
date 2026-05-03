"""
Final Refinement: Clean DYNAMIC_FIELDS (Target: 800-1000)
With: SYSTEM HARD BLOCK + CONTEXT-DEPENDENT FILTER + STRICT HUMAN TEST + QUESTION-FIRST MERGING
"""
import json
from collections import defaultdict

print("=" * 80)
print("FINAL REFINEMENT - TARGETING 800-1000 DYNAMIC FIELDS")
print("=" * 80)

# Load field classification
with open('field_classification.json', 'r', encoding='utf-8') as f:
    classification = json.load(f)

base_fields = set(classification['base_fields'])
original_dynamic = classification['dynamic_fields']
system_fields = set(classification['system_fields'])

print(f"Original: BASE={len(base_fields)}, DYNAMIC={len(original_dynamic)}, SYSTEM={len(system_fields)}")

# ============================================================
# STEP 1: SYSTEM HARD BLOCK (AGGRESSIVE)
# ============================================================
system_keywords = [
    "type", "category", "classification", "status", "level", "stage",
    "component", "segment", "affiliation", "recognition",
    "approval", "verification", "authority", "certification", "accreditation",
    "scheme", "eligibility", "criteria", "condition",
    "code", "number", "id", "serial", "module", "internal", "config"
]

def is_system_by_keyword(field):
    field_lower = field.lower()
    for kw in system_keywords:
        if kw in field_lower:
            return True
    return False

# ============================================================
# STEP 2: CONTEXT-DEPENDENT FILTER
# ============================================================
context_dependent_patterns = [
    "registered_with_", "approved_by_", "recognized_by_", "affiliated_to_",
    "licensed_by_", "certified_by_", "verified_by_", "authority_",
    "board_", "department_", "institution_", "government_",
    "scheme_", "program_", "policy_", "eligibility_"
]

def is_context_dependent(field):
    field_lower = field.lower()
    for pattern in context_dependent_patterns:
        if pattern in field_lower:
            return True
    return False

# ============================================================
# STEP 3: STRICT HUMAN TEST
# ============================================================
# Would a 10th pass user understand this instantly?
def is_human_understandable(field):
    field_lower = field.lower()
    
    # Multi-word technical fields (3+ underscores = technical)
    if field.count('_') >= 3:
        # Check if it's a simple concept
        simple_concepts = ["is_", "has_", "holds_", "owns_", "belongs_"]
        if any(field_lower.startswith(s) for s in simple_concepts):
            return True
        return False  # Too technical
    
    # Bad patterns
    bad = ["classification", "category_type", "status_type", "level_type", 
           "affiliation_status", "verification", "approval"]
    for b in bad:
        if b in field_lower:
            return False
    
    return True

# ============================================================
# STEP 4: QUESTION GENERATOR
# ============================================================
def generate_question(field):
    """Generate natural user question"""
    f = field.lower()
    
    # Remove prefixes
    for p in ["is_", "has_", "holds_", "owns_", "belongs_"]:
        if f.startswith(p):
            f = f[len(p):]
            break
    
    f = f.replace("_", " ").strip().title()
    
    # Common mappings
    q_map = {
        "aadhaar": "Do you have an Aadhaar card?",
        "aadhar": "Do you have an Aadhaar card?",
        "bank account": "Do you have a bank account?",
        "ration card": "Do you have a ration card?",
        "pan card": "Do you have a PAN card?",
        "disability": "Are you a person with disability?",
        "farmer": "Are you a farmer?",
        "student": "Are you a student?",
        "widow": "Are you a widow?",
        "orphan": "Are you an orphan?",
        "tribal": "Are you a tribal person?",
        "bpl": "Are you from a BPL family?",
        "ews": "Are you from EWS?",
        "nri": "Are you an NRI?",
        "pensioner": "Are you a pensioner?",
        "shg": "Are you a member of SHG?",
        "fisherman": "Are you a fisherman?",
        "land": "Do you own agricultural land?",
    }
    
    for key, q in q_map.items():
        if key in f.lower():
            return q
    
    return f"What is your {f}?"

# ============================================================
# MAIN PROCESS
# ============================================================
moved_to_system = []
moved_to_base = []
final_dynamic = []

# Process each field
for field in original_dynamic:
    # STEP 1: Keyword check
    if is_system_by_keyword(field):
        moved_to_system.append(field)
        system_fields.add(field)
        continue
    
    # STEP 2: Context dependency check
    if is_context_dependent(field):
        moved_to_system.append(field)
        system_fields.add(field)
        continue
    
    # STEP 3: Human test
    if not is_human_understandable(field):
        moved_to_system.append(field)
        system_fields.add(field)
        continue
    
    # Passed all filters - keep in dynamic
    final_dynamic.append(field)

print(f"\n[1] After system filters: {len(final_dynamic)} fields")
print(f"    Moved to SYSTEM: {len(moved_to_system)}")

# ============================================================
# STEP 5: MERGE BY QUESTION (SEMANTIC)
# ============================================================
question_to_fields = defaultdict(list)
field_to_question = {}

for field in final_dynamic:
    q = generate_question(field)
    field_to_question[field] = q
    question_to_fields[q].append(field)

# Create merged groups
merged_groups = {}
unique_dynamic = []

for question, fields in question_to_fields.items():
    # Pick representative field (prefer has_/is_ prefix)
    rep = fields[0]
    for f in fields:
        if f.startswith("has_") and not rep.startswith("has_"):
            rep = f
        elif f == "is_disabled" and rep != "is_disabled":
            rep = f
    
    merged_groups[question] = fields
    unique_dynamic.append(rep)

print(f"\n[2] After question-based merging: {len(unique_dynamic)} unique fields")

# ============================================================
# STEP 6: BASE OVERLAP CHECK
# ============================================================
to_move_to_base = []
final_list = []

for field in unique_dynamic:
    # Check if maps to universal base concept
    field_lower = field.lower()
    universal = ["age", "gender", "income", "caste", "category", "state", 
                 "residence", "occupation", "religion", "education", 
                 "marital", "nationality", "citizen"]
    
    is_universal = any(field_lower == u or field_lower.startswith(u + "_") 
                       for u in universal)
    
    if is_universal and field in base_fields:
        to_move_to_base.append(field)
        base_fields.add(field)
    else:
        final_list.append(field)

print(f"\n[3] After base overlap check: {len(final_list)} final dynamic fields")
print(f"    Moved to BASE: {len(to_move_to_base)}")

# ============================================================
# VALIDATION
# ============================================================
print("\n" + "=" * 80)
print("VALIDATION")
print("=" * 80)

# Remove duplicates
final_unique = list(set(final_list))
dupes_removed = len(final_list) - len(final_unique)

total = len(final_unique) + len(moved_to_system) + len(to_move_to_base)
print(f"Total accounted: {total} (expected {len(original_dynamic)})")

print(f"\nFinal counts:")
print(f"  BASE: {len(base_fields)}")
print(f"  DYNAMIC: {len(final_unique)}")
print(f"  SYSTEM: {len(system_fields)}")

# Check target
if len(final_unique) > 1200:
    print(f"\nWARNING: DYNAMIC ({len(final_unique)}) > 1200")
elif len(final_unique) < 600:
    print(f"\nWARNING: DYNAMIC ({len(final_unique)}) < 600")
else:
    print(f"\nDYNAMIC in target range: 600-1200")

# ============================================================
# SAMPLES
# ============================================================
print("\n" + "=" * 80)
print("10 FIELDS MOVED TO SYSTEM (sample):")
print("=" * 80)
for f in moved_to_system[:10]:
    print(f"  {f}")

print("\n" + "=" * 80)
print("10 MERGED GROUPS (before -> after):")
print("=" * 80)
for i, (q, fields) in enumerate(list(merged_groups.items())[:10]):
    print(f"\n{i+1}. Question: {q}")
    print(f"   Fields merged: {len(fields)}")
    if len(fields) > 1:
        print(f"   Example: {fields[0]} -> {fields[-1]}")

print("\n" + "=" * 80)
print("10 SAMPLE GENERATED QUESTIONS:")
print("=" * 80)
sample_qs = list(set(field_to_question.values()))[:10]
for q in sample_qs:
    print(f"  {q}")

# ============================================================
# SAVE OUTPUT
# ============================================================
output = {
    "final_dynamic_fields": sorted(final_unique),
    "moved_to_system": sorted(moved_to_system),
    "moved_to_base": sorted(to_move_to_base),
    "merged_groups": {k: v for k, v in list(merged_groups.items())[:50]},
    "summary": {
        "original_dynamic": len(original_dynamic),
        "final_dynamic": len(final_unique),
        "moved_to_system": len(moved_to_system),
        "moved_to_base": len(to_move_to_base),
        "duplicates_removed": dupes_removed
    }
}

with open('dynamic_fields_final.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("\nSaved to: dynamic_fields_final.json")

print("\n" + "=" * 80)
print("FINAL RESULTS")
print("=" * 80)
print(f"DYNAMIC: {len(final_unique)}")
print(f"SYSTEM: {len(system_fields)}")
print(f"BASE: {len(base_fields)}")