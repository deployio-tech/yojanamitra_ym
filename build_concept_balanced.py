"""
Build CONCEPT REGISTRY - BALANCED VERSION
Target: ~80-100 concepts from 679 fields
"""
import json
from collections import defaultdict

print("=" * 80)
print("BUILDING CONCEPT REGISTRY (BALANCED)")
print("=" * 80)

# Load final dynamic fields
with open('dynamic_fields_final.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

final_dynamic_fields = data['final_dynamic_fields']
print(f"Input fields: {len(final_dynamic_fields)}")

# ============================================================
# BALANCED CONCEPT MAPPING - Keep key concepts distinct
# ============================================================
# Priority 1: MUST KEEP DISTINCT (core identity/documents)
KEEP_DISTINCT = [
    "aadhaar", "bank_account", "ration_card", "pan_card",
    "disability", "farmer", "student_status", "widow", "orphan",
    "tribal", "bpl", "ews", "nri", "pensioner", "shg_member", 
    "fisherman", "land_ownership", "gender", "marital_status",
    "residence", "minority_status"
]

def get_concept(field):
    """Map field to concept - balanced approach"""
    f = field.lower()
    
    # Check distinct concepts first
    for keep in KEEP_DISTINCT:
        if keep in f:
            return keep
    
    # Group patterns for secondary concepts
    if "employed" in f or "employment" in f or "occupation" in f or "job" in f:
        return "employment"
    if "pregnant" in f or "lactating" in f:
        return "pregnancy_status"
    if "child" in f or "daughter" in f or "son" in f or "parent" in f:
        return "parent_status"
    if "member" in f or "registered" in f or "enrolled" in f:
        return "membership"
    if "beneficiary" in f or "availing" in f or "receiving" in f:
        return "benefit_recipient"
    if "certificate" in f or "license" in f or "card" in f:
        return "documents"
    if "govt" in f or "government" in f or "employee" in f:
        return "govt_employee"
    if "cancer" in f or "disease" in f or "patient" in f or "sick" in f or "illness" in f:
        return "health_condition"
    if "study" in f or "school" in f or "college" in f or "passed" in f or "fail" in f:
        return "education"
    if "land" in f or "cultivator" in f:
        return "land_ownership"
    if "disaster" in f or "calamity" in f:
        return "disaster_affected"
    if "first_time" in f or "new" in f:
        return "first_time"
    if "active" in f or "engaged" in f:
        return "activity_status"
    if "approved" in f or "verified" in f:
        return "verification"
    if "contribut" in f:
        return "contribution"
    if "full_time" in f or "part_time" in f:
        return "work_type"
    
    # Default: extract meaningful noun
    for prefix in ["is_", "has_", "holds_", "owns_"]:
        if f.startswith(prefix):
            f = f[len(prefix):]
            break
    
    words = f.split("_")
    if words:
        return words[0][:15]
    
    return "other"

# ============================================================
# Map fields
# ============================================================
field_to_concept = {}
concept_to_fields = defaultdict(list)

for field in final_dynamic_fields:
    concept = get_concept(field)
    field_to_concept[field] = concept
    concept_to_fields[concept].append(field)

print(f"\nInitial concepts: {len(concept_to_fields)}")

# ============================================================
# Second pass - merge very small concepts into related ones
# ============================================================
# Group small (<=2 fields) into related bigger concepts
small_merge = {
    "documents": ["certificate", "license", "card"],
    "employment": ["occupation", "job", "unemployed"],
    "membership": ["registered", "enrolled"],
    "benefit_recipient": ["availing", "receiving"],
    "govt_employee": ["government", "servant"],
    "health_condition": ["disease", "patient", "sick", "illness"],
    "education": ["study", "school", "passed", "fail"],
    "activity_status": ["active", "engaged"],
    "verification": ["approved", "verified"],
}

for target, patterns in small_merge.items():
    for pattern in patterns:
        for concept in list(concept_to_fields.keys()):
            if pattern in concept and concept != target and len(concept_to_fields.get(concept, [])) <= 3:
                fields = concept_to_fields.pop(concept, [])
                for f in fields:
                    field_to_concept[f] = target
                    concept_to_fields[target].append(f)

print(f"After small merge: {len(concept_to_fields)}")

# ============================================================
# Final cleanup - merge very small into "other"
# ============================================================
min_fields = 2
small = [c for c, fs in concept_to_fields.items() if len(fs) < min_fields and c not in KEEP_DISTINCT]
for s in small:
    fields = concept_to_fields.pop(s, [])
    for f in fields:
        field_to_concept[f] = "other"
        concept_to_fields["other"].append(f)

print(f"Final concepts: {len(concept_to_fields)}")

# ============================================================
# Generate questions
# ============================================================
question_map = {
    "aadhaar": "Do you have an Aadhaar card?",
    "bank_account": "Do you have a bank account?",
    "ration_card": "Do you have a ration card?",
    "pan_card": "Do you have a PAN card?",
    "disability": "Are you a person with disability?",
    "farmer": "Are you a farmer?",
    "student_status": "Are you a student?",
    "widow": "Are you a widow?",
    "orphan": "Are you an orphan?",
    "tribal": "Are you a tribal person?",
    "bpl": "Are you from a BPL family?",
    "ews": "Are you from EWS?",
    "nri": "Are you an NRI?",
    "pensioner": "Are you a pensioner?",
    "shg_member": "Are you a member of a Self Help Group?",
    "fisherman": "Are you a fisherman?",
    "land_ownership": "Do you own agricultural land?",
    "gender": "What is your gender?",
    "marital_status": "What is your marital status?",
    "residence": "What is your residence status?",
    "minority_status": "Do you belong to a minority community?",
    "employment": "Are you employed?",
    "pregnancy_status": "Are you pregnant or lactating?",
    "parent_status": "Do you have children?",
    "membership": "Are you a member of any organization?",
    "benefit_recipient": "Are you receiving any government benefits?",
    "documents": "Do you have any official documents?",
    "govt_employee": "Are you a government employee?",
    "health_condition": "Do you have any health conditions?",
    "education": "What is your education status?",
    "disaster_affected": "Are you affected by disaster?",
    "first_time": "Is this your first time?",
    "activity_status": "Are you currently active/engaged?",
    "verification": "Have you been verified/approved?",
    "contribution": "Are you contributing?",
    "work_type": "What type of work do you do?",
    "other": "Any other status?",
}

def get_question(concept):
    return question_map.get(concept, f"What is your {concept}?")

# ============================================================
# Build registry
# ============================================================
concepts = []
for concept, fields in concept_to_fields.items():
    question = get_question(concept)
    concepts.append({
        "concept": concept,
        "question": question,
        "fields": sorted(fields)
    })

concepts.sort(key=lambda x: len(x['fields']), reverse=True)

print(f"Final concepts: {len(concepts)}")

# ============================================================
# Validate
# ============================================================
mapped = set()
for c in concepts:
    for f in c['fields']:
        mapped.add(f)

print(f"\nValidation:")
print(f"  Fields mapped: {len(mapped)}")
print(f"  Match: {len(mapped) == len(final_dynamic_fields)}")

# ============================================================
# Output
# ============================================================
registry = {
    "concepts": concepts,
    "field_to_concept": field_to_concept,
    "summary": {
        "total_fields": len(final_dynamic_fields),
        "total_concepts": len(concepts),
        "validation_passed": len(mapped) == len(final_dynamic_fields)
    }
}

with open('concept_registry.json', 'w', encoding='utf-8') as f:
    json.dump(registry, f, indent=2, ensure_ascii=False)

print("\nSaved to: concept_registry.json")

# Results
print("\n" + "=" * 80)
print("RESULTS")
print("=" * 80)
print(f"FIELDS: {len(final_dynamic_fields)}")
print(f"CONCEPTS: {len(concepts)}")

print("\n" + "=" * 80)
print("ALL CONCEPTS:")
print("=" * 80)
for c in concepts:
    print(f"{c['concept']}: {len(c['fields'])} fields")