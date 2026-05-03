"""
Generate MINIMAL question set with IMPROVED pattern matching.
More specific patterns for better quality.
"""
import json
import re

print("=" * 80)
print("GENERATING MINIMAL QUESTION SET (IMPROVED)")
print("=" * 80)

# Load all fields
with open('all_question_fields.txt', 'r', encoding='utf-8') as f:
    all_fields = [line.strip() for line in f.readlines()]

print(f"Total fields loaded: {len(all_fields)}")

# Define MORE SPECIFIC questions with stricter patterns
# Order matters - more specific first
questions = [
    # AGE - specific patterns
    {
        "question": "What is your age?",
        "fields": [],
        "patterns": [
            r'^age$', r'^age_', r'_age$', r'_age_', 
            r'^age_min\b', r'^age_max\b', 
            r'age_group', r'age_limit', r'age_bracket'
        ]
    },
    # GENDER - more specific
    {
        "question": "What is your gender?",
        "fields": [],
        "patterns": [
            r'^gender$', r'^gender_', r'beneficiary_gender', 
            r'applicant_gender', r'_gender$', r'gender_category'
        ]
    },
    # INCOME - specific
    {
        "question": "What is your annual family income?",
        "fields": [],
        "patterns": [
            r'income', r'earnings', r'salary', r'wage',
            r'annual_.*income', r'family_income', r'monthly_income',
            r'income_limit', r'income_max', r'income_min',
            r'net_annual', r'gross_income'
        ]
    },
    # CASTE/CATEGORY - specific
    {
        "question": "What is your caste category?",
        "fields": [],
        "patterns": [
            r'^caste_category', r'^category$', r'^category_',
            r'_category$', r'_caste', r'caste_',
            r'\bcategory\b.*sc', r'\bcategory\b.*st', r'\bcategory\b.*obc'
        ]
    },
    # STATE - specific
    {
        "question": "Which state do you reside in?",
        "fields": [],
        "patterns": [
            r'^state$', r'^state_', r'residing_state', 
            r'domicile_state', r'native_state', r'permanent_state'
        ]
    },
    # RESIDENCE TYPE - specific
    {
        "question": "Do you live in a rural or urban area?",
        "fields": [],
        "patterns": [
            r'^is_rural', r'^is_urban', r'^residence$', 
            r'^residence_', r'^residence_type', r'area_type',
            r'locality', r'village', r'city'
        ]
    },
    # EDUCATION - specific
    {
        "question": "What is your highest education level?",
        "fields": [],
        "patterns": [
            r'^education_level', r'^education_', r'^qualification$',
            r'^qualification_', r'academic_qualification',
            r'class_10', r'class_12', r'matric', r'intermediate',
            r'graduate', r'post_graduate', r'phd', r'mPhil',
            r'degree', r'diploma', r'certificate_course'
        ]
    },
    # OCCUPATION - specific
    {
        "question": "What is your current occupation?",
        "fields": [],
        "patterns": [
            r'^occupation$', r'^occupation_', r'job_type',
            r'employment_status', r'work_status', r'professional',
            r'profession', r'vocational'
        ]
    },
    # RELIGION
    {
        "question": "What is your religion?",
        "fields": [],
        "patterns": [
            r'^religion$', r'^religion_', r'faith'
        ]
    },
    # DISABILITY
    {
        "question": "Are you a person with disability?",
        "fields": [],
        "patterns": [
            r'^is_disabled', r'^disability', r'^disabled',
            r'handicap', r'physically_challenged', r'pwd'
        ]
    },
    # BPL
    {
        "question": "Are you from a BPL (Below Poverty Line) family?",
        "fields": [],
        "patterns": [
            r'^is_bpl', r'^bpl', r'poverty_line'
        ]
    },
    # WIDOW
    {
        "question": "Are you a widow?",
        "fields": [],
        "patterns": [
            r'^is_widow', r'^widow', r'^widowed'
        ]
    },
    # ORPHAN
    {
        "question": "Are you an orphan?",
        "fields": [],
        "patterns": [
            r'^is_orphan', r'^orphan', r'abandoned'
        ]
    },
    # BANK ACCOUNT
    {
        "question": "Do you have a bank account?",
        "fields": [],
        "patterns": [
            r'bank_account', r'savings_account', r'account_number',
            r'account_holder', r'bank_name', r'ifsc'
        ]
    },
    # AADHAAR
    {
        "question": "Do you have an Aadhaar card?",
        "fields": [],
        "patterns": [
            r'aadhaar', r'aadhar', r'aadhar_number'
        ]
    },
    # RATION CARD
    {
        "question": "Do you have a Ration card?",
        "fields": [],
        "patterns": [
            r'ration_card', r'ration'
        ]
    },
    # PAN CARD
    {
        "question": "Do you have a PAN card?",
        "fields": [],
        "patterns": [
            r'^pan_', r'^pancard', r'pan_number'
        ]
    },
    # SHG MEMBER
    {
        "question": "Are you a member of a Self Help Group (SHG)?",
        "fields": [],
        "patterns": [
            r'shg', r'self_help', r'sangathan'
        ]
    },
    # MARITAL STATUS
    {
        "question": "What is your marital status?",
        "fields": [],
        "patterns": [
            r'^marital', r'^married', r'^single', r'spouse'
        ]
    },
    # LAND OWNERSHIP
    {
        "question": "Do you own agricultural land?",
        "fields": [],
        "patterns": [
            r'^land_', r'^is_landless', r'cultivator', r'farmer',
            r'agri_land', r'farm_size', r'land_holding'
        ]
    },
    # FAMILY SIZE
    {
        "question": "What is your family size?",
        "fields": [],
        "patterns": [
            r'family_size', r'household', r'family_members',
            r'no_of_members'
        ]
    },
    # MINORITY
    {
        "question": "Do you belong to a minority community?",
        "fields": [],
        "patterns": [
            r'^is_minority', r'^minority'
        ]
    },
    # EWS
    {
        "question": "Are you from Economically Weaker Section (EWS)?",
        "fields": [],
        "patterns": [
            r'^is_ews', r'^ews'
        ]
    },
    # TRIBAL
    {
        "question": "Are you a tribal person?",
        "fields": [],
        "patterns": [
            r'^is_tribal', r'^tribal', r'\bst\b'
        ]
    },
    # NRI
    {
        "question": "Are you an NRI (Non-Resident Indian)?",
        "fields": [],
        "patterns": [
            r'^is_nri', r'^nri', r'non_resident'
        ]
    },
    # PENSIONER
    {
        "question": "Are you a pensioner?",
        "fields": [],
        "patterns": [
            r'^is_pensioner', r'^pension'
        ]
    },
    # CONSTRUCTION WORKER
    {
        "question": "Are you a construction worker?",
        "fields": [],
        "patterns": [
            r'construction_worker', r'building_worker', r'mason'
        ]
    },
    # STUDENT
    {
        "question": "Are you a student?",
        "fields": [],
        "patterns": [
            r'^is_student', r'^student', r'enrolled', r'studying'
        ]
    },
    # FARMER
    {
        "question": "Are you a farmer?",
        "fields": [],
        "patterns": [
            r'^is_farmer', r'^farmer'
        ]
    },
    # FIRST GEN STUDENT
    {
        "question": "Are you a first-generation student?",
        "fields": [],
        "patterns": [
            r'first_gen', r'first_generation'
        ]
    },
    # DOCUMENTS - common
    {
        "question": "Which identity/documents do you have?",
        "fields": [],
        "patterns": [
            r'^has_', r'certificate', r'document', r'card',
            r'passport', r'driving_license', r'voter'
        ]
    },
    # NATIONALITY
    {
        "question": "What is your nationality?",
        "fields": [],
        "patterns": [
            r'citizen', r'nationality', r'indian$', r'citizenship'
        ]
    },
    # BIRTHPLACE/DOB
    {
        "question": "What is your date of birth?",
        "fields": [],
        "patterns": [
            r'dob', r'date_of_birth', r'^birth_'
        ]
    },
]

# Assign fields to questions
assigned_fields = set()

for field in all_fields:
    assigned = False
    
    for q in questions:
        for pattern in q['patterns']:
            if re.search(pattern, field, re.IGNORECASE):
                q['fields'].append(field)
                assigned_fields.add(field)
                assigned = True
                break
        if assigned:
            break

# Remaining fields go to fallback
fallback_fields = [f for f in all_fields if f not in assigned_fields]

print(f"\n{'='*80}")
print("RESULTS")
print("="*80)
print(f"Total fields: {len(all_fields)}")
print(f"Fields assigned: {len(assigned_fields)}")
print(f"Fallback fields: {len(fallback_fields)}")

# Create final questions list (only those with fields)
final_questions = []
for q in questions:
    if q['fields']:
        final_questions.append({
            "question": q['question'],
            "fields": q['fields']
        })

# Add fallback if needed
if fallback_fields:
    final_questions.append({
        "question": "Additional eligibility details (for specific schemes)",
        "fields": fallback_fields
    })

# Validation
all_fields_set = set(all_fields)
mapped_set = set(assigned_fields) | set(fallback_fields)
missing = all_fields_set - mapped_set
duplicates = len(assigned_fields) + len(fallback_fields) - len(all_fields_set)

print(f"\nValidation:")
print(f"  Missing fields: {len(missing)}")
print(f"  Duplicate fields: {duplicates}")

# Show stats
print(f"\n{'='*80}")
print(f"QUESTION STATISTICS:")
print("="*80)
for i, q in enumerate(final_questions):
    print(f"{i+1}. {q['question'][:50]:50} -> {len(q['fields'])} fields")

# Show sample
print(f"\n{'='*80}")
print("SAMPLE MAPPINGS (first 5):")
print("="*80)
for i, q in enumerate(final_questions[:5]):
    print(f"\n{i+1}. {q['question']}")
    print(f"   Fields ({len(q['fields'])}): {q['fields'][:3]}")

# Save
output_file = "question_set_v2.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(final_questions, f, indent=2, ensure_ascii=False)

print(f"\n✅ Saved to: {output_file}")
print(f"\n{'='*80}")
print("EXECUTION COMPLETE")
print("="*80)