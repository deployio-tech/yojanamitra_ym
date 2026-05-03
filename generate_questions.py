"""
Generate minimal question set from 8245 canonical fields.
Using AI-assisted semantic grouping.
"""
import sys
sys.path.insert(0, '.')
from app import app, User, Scheme
from app.engine.eligibility import get_canonical_field
from app.engine.questions import is_user_answerable
import json
import re

print("=" * 80)
print("GENERATING MINIMAL QUESTION SET")
print("=" * 80)

with app.app_context():
    # Load all fields from file
    with open('all_question_fields.txt', 'r', encoding='utf-8') as f:
        all_fields = [line.strip() for line in f.readlines()]
    
    print(f"\nTotal fields loaded: {len(all_fields)}")
    
    # Define core questions based on common eligibility patterns
    # These will be the anchors for semantic grouping
    
    # First, let's do intelligent pattern-based grouping
    questions = []
    
    # Define question templates with their field patterns
    question_templates = [
        {
            "question": "What is your age?",
            "patterns": [r'^age$', r'^age_', r'_age$', r'_age_'],
            "fields": []
        },
        {
            "question": "What is your gender?",
            "patterns": [r'^gender$', r'^is_', r'_gender$', r'_gender_', r'sex$'],
            "fields": []
        },
        {
            "question": "What is your annual family income?",
            "patterns": [r'income', r'earnings', r'salary'],
            "fields": []
        },
        {
            "question": "What is your caste category?",
            "patterns": [r'caste', r'category', r'sc_', r'st_', r'obc_', r'general'],
            "fields": []
        },
        {
            "question": "Which state do you reside in?",
            "patterns": [r'state$', r'residence', r'reside', r'state_'],
            "fields": []
        },
        {
            "question": "Do you live in a rural or urban area?",
            "patterns": [r'rural', r'urban', r'area_type', r'residence_area'],
            "fields": []
        },
        {
            "question": "What is your highest education level?",
            "patterns": [r'education', r'academic', r'qualification', r'class_', 
                         r'matriculation', r'graduation', r'post_grad', r'phd'],
            "fields": []
        },
        {
            "question": "What is your occupation?",
            "patterns": [r'occupation', r'employment', r'job', r'work_', r'worker',
                         r'student', r'farmer', r'self_employed', r'business'],
            "fields": []
        },
        {
            "question": "What is your religion?",
            "patterns": [r'religion', r'faith'],
            "fields": []
        },
        {
            "question": "Are you a person with disability?",
            "patterns": [r'disabil', r'handicap', r'physically_challenged'],
            "fields": []
        },
        {
            "question": "Do you belong to BPL (Below Poverty Line) category?",
            "patterns": [r'bpl', r'below_poverty', r'poverty'],
            "fields": []
        },
        {
            "question": "Are you a widow?",
            "patterns": [r'widow', r'widowed'],
            "fields": []
        },
        {
            "question": "Are you an orphan?",
            "patterns": [r'orphan', r'abandoned'],
            "fields": []
        },
        {
            "question": "Do you have a bank account?",
            "patterns": [r'bank_account', r'account_number', r'savings_account'],
            "fields": []
        },
        {
            "question": "Do you have an Aadhaar card?",
            "patterns": [r'aadhaar', r'aadhar'],
            "fields": []
        },
        {
            "question": "Do you have a Ration card?",
            "patterns": [r'ration'],
            "fields": []
        },
        {
            "question": "Do you have a PAN card?",
            "patterns": [r'pan_'],
            "fields": []
        },
        {
            "question": "Are you a member of any SHG (Self Help Group)?",
            "patterns": [r'shg', r'self_help_group', r'sangathan'],
            "fields": []
        },
        {
            "question": "What is your marital status?",
            "patterns": [r'marital', r'married', r'single'],
            "fields": []
        },
        {
            "question": "Do you own land?",
            "patterns": [r'land_', r'landless', r'cultivator', r'farmer'],
            "fields": []
        },
        {
            "question": "What is your family size?",
            "patterns": [r'family_size', r'household_', r'members_'],
            "fields": []
        },
        {
            "question": "How many daughters do you have?",
            "patterns": [r'daughter', r'girl_child'],
            "fields": []
        },
        {
            "question": "Are you a first-generation student?",
            "patterns": [r'first_gen', r'first_generation'],
            "fields": []
        },
        {
            "question": "Are you from a minority community?",
            "patterns": [r'minority', r'muslim', r'christian', r'sikh', r'buddist', r'parsi'],
            "fields": []
        },
        {
            "question": "Are you an EWS (Economically Weaker Section) cardholder?",
            "patterns": [r'ews', r'economically_weaker'],
            "fields": []
        },
        {
            "question": "Are you a tribal person?",
            "patterns": [r'tribal', r'st_', r'tribe'],
            "fields": []
        },
        {
            "question": "Are you an NRI (Non-Resident Indian)?",
            "patterns": [r'nri', r'non_resident', r'resident_'],
            "fields": []
        },
        {
            "question": "What is your father's name?",
            "patterns": [r'father_', r'parent_'],
            "fields": []
        },
        {
            "question": "What is your mother's name?",
            "patterns": [r'mother_'],
            "fields": []
        },
        {
            "question": "Are you a pensioner?",
            "patterns": [r'pension', r'retired'],
            "fields": []
        },
        {
            "question": "Are you a construction worker?",
            "patterns": [r'construction_worker', r'building_worker', r'mason'],
            "fields": []
        },
        {
            "question": "Do you have any existing loans?",
            "patterns": [r'loan', r'debt', r'credit', r'borrow'],
            "fields": []
        },
        {
            "question": "What is your birthplace?",
            "patterns": [r'birth_', r'dob', r'date_of_birth', r'born_'],
            "fields": []
        },
        {
            "question": "What is your nationality?",
            "patterns": [r'citizen', r'nationality', r'indian_'],
            "fields": []
        },
        {
            "question": "Are you a housewife?",
            "patterns": [r'housewife', r'homemaker'],
            "fields": []
        },
        {
            "question": "Are you a school dropout?",
            "patterns": [r'dropout', r'drop_out', r'school_'],
            "fields": []
        },
    ]
    
    # Add fallback bucket for unmapped fields
    question_templates.append({
        "question": "Additional eligibility details (if applicable)",
        "patterns": [],
        "fields": []
    })
    
    # Assign fields to questions
    assigned_fields = set()
    
    for field in all_fields:
        assigned = False
        for template in question_templates[:-1]:  # Skip fallback
            for pattern in template['patterns']:
                if re.search(pattern, field, re.IGNORECASE):
                    template['fields'].append(field)
                    assigned_fields.add(field)
                    assigned = True
                    break
            if assigned:
                break
        
        if not assigned:
            # Put in fallback bucket
            question_templates[-1]['fields'].append(field)
            assigned_fields.add(field)
    
    # Create final questions list
    final_questions = []
    for template in question_templates:
        if template['fields']:  # Only include questions with fields
            final_questions.append({
                "question": template['question'],
                "fields": template['fields']
            })
    
    separator = "=" * 80
    print(f"\n{separator}")
    print("RESULTS")
    print(separator)
    print(f"Total questions generated: {len(final_questions)}")
    print(f"Total fields assigned: {len(assigned_fields)}")
    print(f"Unmapped fields: {len(all_fields) - len(assigned_fields)}")
    
    # Validation
    all_fields_set = set(all_fields)
    mapped_fields_set = set(assigned_fields)
    missing = all_fields_set - mapped_fields_set
    extra = mapped_fields_set - all_fields_set
    
    print(f"\nValidation:")
    print(f"  Missing fields: {len(missing)}")
    print(f"  Extra fields: {len(extra)}")
    
    if len(missing) > 0:
        print(f"\n⚠️ WARNING: {len(missing)} fields not mapped!")
        # Add missing to fallback
        for f in missing:
            final_questions[-1]['fields'].append(f)
    
    # Show sample questions
    separator = "=" * 80
    print(f"\n{separator}")
    print("SAMPLE QUESTIONS (first 5):")
    print(separator)
    for i, q in enumerate(final_questions[:5]):
        print(f"\n{i+1}. {q['question']}")
        print(f"   Fields: {len(q['fields'])}")
        print(f"   Examples: {q['fields'][:3]}")
    
    # Show last question (fallback)
    print(f"\n{separator}")
    print("FALLBACK BUCKET:")
    print(separator)
    fallback = final_questions[-1]
    print(f"Question: {fallback['question']}")
    print(f"Total fields: {len(fallback['fields'])}")
    print(f"Examples: {fallback['fields'][:10]}")
    
    # Save to JSON
    output_file = "question_set.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_questions, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved to: {output_file}")

print(f"\n{separator}")
print("EXECUTION COMPLETE")
print(separator)