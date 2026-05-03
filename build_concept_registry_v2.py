"""
Build CONCEPT REGISTRY - FIXED VERSION
More aggressive deduplication to get ~70-100 concepts
"""
import json
from collections import defaultdict

print("=" * 80)
print("BUILDING CONCEPT REGISTRY (FIXED)")
print("=" * 80)

# Load final dynamic fields
with open('dynamic_fields_final.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

final_dynamic_fields = data['final_dynamic_fields']
print(f"Input fields: {len(final_dynamic_fields)}")

# ============================================================
# AGGRESSIVE CONCEPT MAPPING
# ============================================================
def get_concept(field):
    """Map field to core concept - aggressive consolidation"""
    f = field.lower()
    
    # Very specific mappings first
    if "aadhaar" in f or "aadhar" in f:
        return "aadhaar"
    if "bank" in f and "account" in f:
        return "bank_account"
    if "ration" in f:
        return "ration_card"
    if "pan" in f:
        return "pan_card"
    if "disability" in f or "disabled" in f or "divyang" in f:
        return "disability"
    if "farmer" in f or "cultivator" in f or "agriculture" in f:
        return "farmer"
    if f == "is_student" or "student" in f:
        return "student_status"
    if "widow" in f:
        return "widow"
    if "orphan" in f:
        return "orphan"
    if "tribal" in f or f.endswith("_st"):
        return "tribal"
    if "bpl" in f:
        return "bpl_status"
    if "ews" in f:
        return "ews_status"
    if "nri" in f:
        return "nri_status"
    if "pensioner" in f or "pension" in f:
        return "pensioner"
    if "shg" in f or "self_help" in f:
        return "shg_member"
    if "fisherman" in f or "fisher" in f:
        return "fisherman"
    if "land" in f or "cultivator" in f:
        return "land_ownership"
    
    # Employment/occupation
    if "employed" in f or "employment" in f or "job" in f or "occupation" in f:
        return "occupation"
    if "unemployed" in f:
        return "unemployed"
    if "worker" in f or "labourer" in f or "labour" in f:
        return "worker"
    
    # Family status
    if "married" in f or "marital" in f:
        return "marital_status"
    if "pregnant" in f or "lactating" in f:
        return "pregnancy_status"
    if "child" in f or "daughter" in f or "son" in f:
        return "parent_status"
    
    # Identity
    if "minority" in f:
        return "minority_status"
    if "citizen" in f or "nationality" in f:
        return "citizenship"
    if "domicile" in f or "resident" in f:
        return "residence"
    if "gender" in f or "girl" in f or "boy" in f or "woman" in f or "man" in f or "female" in f or "male" in f:
        return "gender"
    
    # Documents
    if "certificate" in f or "license" in f or "card" in f:
        return "documents"
    
    # Catch-all for clearly valid boolean fields
    if f.startswith("is_") or f.startswith("has_") or f.startswith("holds_"):
        # Keep as individual - these are scheme-specific status questions
        return f.split("_", 1)[1][:20]  # Take second part, truncate
    
    return "other"

# ============================================================
# Map all fields
# ============================================================
field_to_concept = {}
concept_to_fields = defaultdict(list)

for field in final_dynamic_fields:
    concept = get_concept(field)
    field_to_concept[field] = concept
    concept_to_fields[concept].append(field)

print(f"\nInitial concepts: {len(concept_to_fields)}")

# ============================================================
# AGGRESSIVE DEDUPLICATION - MERGE SIMILAR CONCEPTS
# ============================================================
# Merge small concepts into related bigger ones
merge_rules = {
    # Documents merge
    "documents": ["license", "certificate", "card"],
    # Worker merge  
    "occupation": ["unemployed", "worker"],
    # Family merge
    "marital_status": ["parent_status"],
    # Gender merge (already consolidated)
    # Residences merge
    "residence": ["domicile", "citizenship"],
}

for target, sources in merge_rules.items():
    for source in sources:
        if source in concept_to_fields:
            fields = concept_to_fields.pop(source, [])
            for f in fields:
                field_to_concept[f] = target
                concept_to_fields[target].append(f)

print(f"After deduplication: {len(concept_to_fields)}")

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
    "bpl_status": "Are you from a BPL family?",
    "ews_status": "Are you from EWS?",
    "nri_status": "Are you an NRI?",
    "pensioner": "Are you a pensioner?",
    "shg_member": "Are you a member of a Self Help Group?",
    "fisherman": "Are you a fisherman?",
    "land_ownership": "Do you own agricultural land?",
    "occupation": "What is your occupation?",
    "marital_status": "What is your marital status?",
    "pregnancy_status": "Are you pregnant or lactating?",
    "parent_status": "Do you have children?",
    "minority_status": "Do you belong to a minority community?",
    "residence": "What is your current residence status?",
    "gender": "What is your gender?",
    "documents": "Do you have any official documents/certificates?",
    "other": "Additional status",
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

# Sort by field count
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
print(f"  Expected: {len(final_dynamic_fields)}")
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
print("SAMPLE 15 CONCEPTS:")
print("=" * 80)
for c in concepts[:15]:
    print(f"\n{c['concept']}:")
    print(f"  Question: {c['question']}")
    print(f"  Fields: {len(c['fields'])}")