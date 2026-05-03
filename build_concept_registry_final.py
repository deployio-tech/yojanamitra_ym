"""
Build CONCEPT REGISTRY - FINAL VERSION
More aggressive grouping to get ~80-120 concepts
"""
import json
from collections import defaultdict
import re

print("=" * 80)
print("BUILDING CONCEPT REGISTRY (FINAL)")
print("=" * 80)

# Load final dynamic fields
with open('dynamic_fields_final.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

final_dynamic_fields = data['final_dynamic_fields']
print(f"Input fields: {len(final_dynamic_fields)}")

# ============================================================
# ULTRA AGGRESSIVE CONCEPT MAPPING
# ============================================================
def get_core_concept(field):
    """Map field to core concept with aggressive grouping"""
    f = field.lower()
    
    # Priority 1: Major identity/documents (keep distinct)
    if "aadhaar" in f or "aadhar" in f:
        return "aadhaar"
    if "bank" in f and "account" in f:
        return "bank_account"
    if "ration" in f:
        return "ration_card"
    if "pan" in f:
        return "pan_card"
    
    # Priority 2: Socio-economic status (keep distinct)
    if "disability" in f or "disabled" in f or "divyang" in f:
        return "disability"
    if "farmer" in f or "cultivator" in f or "agriculture" in f:
        return "farmer"
    if "student" in f:
        return "student_status"
    if "pensioner" in f or "pension" in f:
        return "pensioner"
    if "worker" in f or "labourer" in f or "labour" in f:
        return "employment"
    if "employed" in f or "employment" in f or "job" in f or "occupation" in f:
        return "employment"
    
    # Priority 3: Social categories (keep distinct)
    if "widow" in f:
        return "widow"
    if "orphan" in f:
        return "orphan"
    if "tribal" in f or "_st" in f:
        return "tribal"
    if "bpl" in f:
        return "bpl"
    if "ews" in f:
        return "ews"
    if "nri" in f:
        return "nri"
    if "minority" in f:
        return "minority"
    if "shg" in f or "self_help" in f:
        return "shg_member"
    if "fisherman" in f or "fisher" in f:
        return "fisherman"
    
    # Priority 4: Family/Personal
    if "married" in f or "marital" in f:
        return "marital_status"
    if "pregnant" in f or "lactating" in f:
        return "pregnancy_status"
    if "child" in f or "daughter" in f or "son" in f:
        return "parent_status"
    if "gender" in f or "girl" in f or "boy" in f or "woman" in f or "man" in f:
        return "gender"
    
    # Priority 5: Location/Residence
    if "resident" in f or "domicile" in f:
        return "residence"
    if "state" in f:
        return "residence"
    
    # Priority 6: Documents/Status (group together)
    if "certificate" in f or "license" in f or "card" in f or "registration" in f or "member" in f:
        return "membership_status"
    
    # Priority 7: Common boolean patterns - group by theme
    # Benefit recipient
    if "beneficiary" in f or "availing" in f or "receiving" in f:
        return "benefit_status"
    
    # Government relation
    if "govt" in f or "government" in f or "employee" in f:
        return "govt_relation"
    
    # Health conditions
    if "cancer" in f or "disease" in f or "patient" in f or "illness" in f:
        return "health_status"
    
    # Education related
    if "study" in f or "study" in f or "class" in f or "passed" in f or "fail" in f:
        return "education_status"
    
    # Default - extract key noun
    # Remove is_/has_/holds_/owns_ prefix
    for prefix in ["is_", "has_", "holds_", "owns_", "belongs_"]:
        if f.startswith(prefix):
            f = f[len(prefix):]
            break
    
    # Get the core word
    words = f.split("_")
    if len(words) >= 1:
        # Take first 1-2 meaningful words
        core = "_".join(words[:2]) if len(words) > 1 else words[0]
        # Truncate to avoid too many unique concepts
        return core[:20]
    
    return "other"

# ============================================================
# Map all fields
# ============================================================
field_to_concept = {}
concept_to_fields = defaultdict(list)

for field in final_dynamic_fields:
    concept = get_core_concept(field)
    field_to_concept[field] = concept
    concept_to_fields[concept].append(field)

print(f"\nAfter initial mapping: {len(concept_to_fields)} concepts")

# ============================================================
# FINAL DEDUPLICATION PASS
# ============================================================
# Group very similar concepts together
final_merge = {
    "benefit_status": ["availing", "receiving", "beneficiary"],
    "membership_status": ["registered", "member", "enrolled"],
    "health_status": ["sick", "disease", "patient", "ill"],
    "education_status": ["study", "school", "college", "passed", "fail"],
    "govt_relation": ["government", "employee", "servant"],
}

for target, patterns in final_merge.items():
    for pattern in patterns:
        # Find concepts containing this pattern
        to_merge = [c for c in concept_to_fields.keys() if pattern in c and c != target]
        for src in to_merge:
            if src in concept_to_fields:
                fields = concept_to_fields.pop(src)
                for f in fields:
                    field_to_concept[f] = target
                    concept_to_fields[target].append(f)

# Merge very small concepts (1-2 fields) into "other"
small_concepts = [c for c, fs in concept_to_fields.items() if len(fs) <= 2 and c != "aadhaar" and c != "bank_account"]
for small in small_concepts:
    fields = concept_to_fields.pop(small, [])
    for f in fields:
        field_to_concept[f] = "other"
        concept_to_fields["other"].append(f)

print(f"After final deduplication: {len(concept_to_fields)} concepts")

# ============================================================
# Generate proper questions
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
    "employment": "Are you employed?",
    "marital_status": "What is your marital status?",
    "pregnancy_status": "Are you pregnant or lactating?",
    "parent_status": "Do you have children?",
    "gender": "What is your gender?",
    "residence": "What is your residence status?",
    "membership_status": "Do you have membership or registration?",
    "benefit_status": "Are you receiving any government benefits?",
    "govt_relation": "Are you a government employee?",
    "health_status": "Do you have any health conditions?",
    "education_status": "What is your education status?",
    "land_ownership": "Do you own land?",
    "other": "Additional eligibility status",
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
print("ALL CONCEPTS:")
print("=" * 80)
for c in concepts:
    print(f"{c['concept']}: {len(c['fields'])} fields - {c['question']}")