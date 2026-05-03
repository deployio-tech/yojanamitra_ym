"""
Build CONCEPT REGISTRY System
FIELD → CONCEPT → QUESTION
From 679 dynamic fields to ~70-100 clean concepts
"""
import json
from collections import defaultdict

print("=" * 80)
print("BUILDING CONCEPT REGISTRY")
print("=" * 80)

# Load final dynamic fields
with open('dynamic_fields_final.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

final_dynamic_fields = data['final_dynamic_fields']
merged_groups = data.get('merged_groups', {})

print(f"Input fields: {len(final_dynamic_fields)}")

# ============================================================
# STEP 1: Analyze fields and create initial concepts
# ============================================================
def extract_concept_key(field):
    """Extract core concept from field name"""
    f = field.lower()
    
    # Remove common prefixes
    for p in ["is_", "has_", "holds_", "owns_", "belongs_"]:
        if f.startswith(p):
            f = f[len(p):]
            break
    
    # Map to core concepts
    concept_map = {
        "aadhaar": "aadhaar",
        "aadhar": "aadhaar",
        "bank_account": "bank_account",
        "bank": "bank_account",
        "ration_card": "ration_card",
        "ration": "ration_card",
        "pan": "pan_card",
        "disability": "disability",
        "disabled": "disability",
        "farmer": "farmer",
        "student": "student_status",
        "widow": "widow",
        "orphan": "orphan",
        "tribal": "tribal",
        "bpl": "bpl_status",
        "ews": "ews_status",
        "nri": "nri_status",
        "pensioner": "pensioner",
        "shg": "shg_member",
        "self_help": "shg_member",
        "fisherman": "fisherman",
        "fisher": "fisherman",
        "land": "land_ownership",
        "cultivator": "land_ownership",
        "member": "membership",
        "registered": "registration",
        "employed": "employment_status",
        "unemployed": "employment_status",
        "occupation": "occupation",
        "married": "marital_status",
        "marital": "marital_status",
        "pregnant": "pregnancy_status",
        "lactating": "pregnancy_status",
        "child": "parent_status",
        "daughter": "daughter_status",
        "son": "son_status",
        "minority": "minority_status",
        "worker": "worker_status",
        "laborer": "worker_status",
        "labourer": "worker_status",
        "resident": "residence_status",
        "domicile": "domicile",
        "citizen": "citizenship",
        "nationality": "citizenship",
        "gender": "gender",
        "girl": "gender",
        "boy": "gender",
        "woman": "gender",
        "man": "gender",
        "female": "gender",
        "male": "gender",
        "age": "age",
        "income": "income",
        "caste": "caste_category",
        "category": "caste_category",
        "religion": "religion",
        "state": "state",
        "rural": "residence_type",
        "urban": "residence_type",
    }
    
    for key, concept in concept_map.items():
        if key in f:
            return concept
    
    # Default: clean up the remaining
    return f.replace("_", " ").strip()[:30]

# ============================================================
# STEP 2: Create initial concepts from fields
# ============================================================
field_to_concept = {}
concept_to_fields = defaultdict(list)

for field in final_dynamic_fields:
    concept = extract_concept_key(field)
    field_to_concept[field] = concept
    concept_to_fields[concept].append(field)

print(f"\nInitial concepts: {len(concept_to_fields)}")

# ============================================================
# STEP 2.5: CONCEPT DEDUPLICATION (CRITICAL)
# ============================================================
# Merge similar concepts
deduplication_map = {
    # Aadhaar variations
    "aadhaar": ["aadhaar_availability", "aadhaar_status", "aadhaar_card"],
    # Bank variations
    "bank_account": ["bank_account_status", "bank_account_availability"],
    # Land variations
    "land_ownership": ["owns_land", "land_holder", "agricultural_land"],
    # Student variations
    "student_status": ["is_student", "studying", "enrolled"],
    # Worker variations
    "worker_status": ["worker", "laborer", "labourer", "employment_status"],
    # Membership variations
    "membership": ["member", "member_of", "registered_member"],
    # Registration variations
    "registration": ["registered", "enrolled"],
    # Disability variations
    "disability": ["disabled", "differently_abled", "handicap"],
    # Gender variations  
    "gender": ["girl", "boy", "woman", "man", "female", "male"],
    # Parent variations
    "parent_status": ["child", "daughter", "son", "parent"],
    # Pregnancy variations
    "pregnancy_status": ["pregnant", "lactating", "expectant"],
}

# Apply deduplication
for target, sources in deduplication_map.items():
    for source in sources:
        if source in concept_to_fields and source != target:
            # Move fields from source to target
            fields = concept_to_fields.pop(source, [])
            for f in fields:
                field_to_concept[f] = target
                concept_to_fields[target].append(f)

print(f"After deduplication: {len(concept_to_fields)} concepts")

# ============================================================
# STEP 3: Generate questions for each concept
# ============================================================
concept_questions = {
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
    "ews_status": "Are you from Economically Weaker Section (EWS)?",
    "nri_status": "Are you an NRI (Non-Resident Indian)?",
    "pensioner": "Are you a pensioner?",
    "shg_member": "Are you a member of a Self Help Group?",
    "fisherman": "Are you a fisherman?",
    "land_ownership": "Do you own agricultural land?",
    "membership": "Are you a member of any organization?",
    "registration": "Are you registered with any authority?",
    "occupation": "What is your occupation?",
    "marital_status": "What is your marital status?",
    "pregnancy_status": "Are you pregnant or lactating?",
    "parent_status": "Do you have children?",
    "minority_status": "Do you belong to a minority community?",
    "worker_status": "Are you a worker/labourer?",
    "residence_status": "What is your current residence?",
    "domicile": "What is your state of domicile?",
    "citizenship": "Are you an Indian citizen?",
    "gender": "What is your gender?",
    "age": "What is your age?",
    "income": "What is your annual family income?",
    "caste_category": "What is your caste category?",
    "religion": "What is your religion?",
    "state": "Which state do you reside in?",
    "residence_type": "Do you live in a rural or urban area?",
}

# Generate default questions for unmapped concepts
def generate_question(concept):
    if concept in concept_questions:
        return concept_questions[concept]
    # Default generation
    return f"What is your {concept.replace('_', ' ')}?"

# ============================================================
# STEP 4: Build final registry
# ============================================================
concepts = []

for concept, fields in concept_to_fields.items():
    question = generate_question(concept)
    concepts.append({
        "concept": concept,
        "question": question,
        "fields": sorted(fields)
    })

# Sort by number of fields (descending)
concepts.sort(key=lambda x: len(x['fields']), reverse=True)

print(f"\nFinal concepts: {len(concepts)}")

# ============================================================
# STEP 5: Validate
# ============================================================
print("\n" + "=" * 80)
print("VALIDATION")
print("=" * 80)

# Count mapped fields
mapped_fields = set()
for c in concepts:
    for f in c['fields']:
        mapped_fields.add(f)

print(f"Total fields in registry: {len(mapped_fields)}")
print(f"Expected: {len(final_dynamic_fields)}")

# Check for duplicates
all_fields = []
for c in concepts:
    all_fields.extend(c['fields'])
duplicates = len(all_fields) - len(set(all_fields))

print(f"Duplicates: {duplicates}")

if len(mapped_fields) == len(final_dynamic_fields) and duplicates == 0:
    print("VALIDATION: PASSED")
else:
    print("VALIDATION: ISSUES FOUND")

# ============================================================
# STEP 6: Create field_to_concept mapping
# ============================================================
field_to_concept_final = {}
for c in concepts:
    for f in c['fields']:
        field_to_concept_final[f] = c['concept']

# ============================================================
# OUTPUT
# ============================================================
registry = {
    "concepts": concepts,
    "field_to_concept": field_to_concept_final,
    "summary": {
        "total_fields": len(final_dynamic_fields),
        "total_concepts": len(concepts),
        "validation_passed": len(mapped_fields) == len(final_dynamic_fields) and duplicates == 0
    }
}

with open('concept_registry.json', 'w', encoding='utf-8') as f:
    json.dump(registry, f, indent=2, ensure_ascii=False)

print("\nSaved to: concept_registry.json")

# Show results
print("\n" + "=" * 80)
print("RESULTS")
print("=" * 80)
print(f"FIELDS: {len(final_dynamic_fields)}")
print(f"CONCEPTS: {len(concepts)}")

print("\n" + "=" * 80)
print("SAMPLE 10 CONCEPTS:")
print("=" * 80)
for c in concepts[:10]:
    print(f"\n{c['concept']}:")
    print(f"  Question: {c['question']}")
    print(f"  Fields ({len(c['fields'])}): {c['fields'][:3]}")