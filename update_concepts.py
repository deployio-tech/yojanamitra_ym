import json

# Load current registry
with open('C:/yojanamitra_complete/concept_registry.json') as f:
    data = json.load(f)

# Types:
# - boolean: is_* fields (yes/no)
# - number: age, income, land, etc.
# - single_choice: one option from list
# - multi_choice: multiple options from list

# Add type info to each concept
# Most concepts are boolean (is_* fields)
# We'll also add some special concepts for BASE fields that exist in profile

for concept in data['concepts']:
    concept_name = concept['concept']
    fields = concept['fields']
    
    # Check if any field suggests number type
    has_number_field = any(f in ['age', 'annual_income', 'family_income', 'monthly_income', 
                                   'land_size_acres', 'household_count', 'child_count',
                                   'disability_percentage'] for f in fields)
    
    if has_number_field:
        concept['type'] = 'number'
        concept['options'] = None
        concept['input_hint'] = 'Enter number'
    else:
        # Default to boolean (is_* fields)
        concept['type'] = 'boolean'
        concept['options'] = ['yes', 'no']
        concept['input_hint'] = 'yes/no'

# Add BASE concepts that represent actual profile fields
# These don't come from conditions but are needed for the profile
base_concepts = [
    {"concept": "age", "question": "What is your age?", "type": "number", "options": None, "input_hint": "Enter your age in years", "fields": ["age"]},
    {"concept": "gender", "question": "What is your gender?", "type": "single_choice", "options": ["male", "female", "other", "transgender"], "input_hint": "Select gender", "fields": ["gender", "is_male", "is_female"]},
    {"concept": "category", "question": "What is your caste category?", "type": "single_choice", "options": ["general", "obc", "sc", "st", "ews"], "input_hint": "Select category", "fields": ["category", "caste_category"]},
    {"concept": "state", "question": "Which state do you reside in?", "type": "single_choice", "options": ["andhra_pradesh", "arunachal_pradesh", "assam", "bihar", "chhattisgarh", "goa", "gujarat", "haryana", "himachal_pradesh", "jharkhand", "karnataka", "kerala", "madhya_pradesh", "maharashtra", "manipur", "meghalaya", "mizoram", "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil_nadu", "telangana", "tripura", "uttar_pradesh", "uttarakhand", "west_bengal", "delhi", "jammu_kashmir", "ladakh", "puducherry"], "input_hint": "Select state", "fields": ["state", "residence_state", "domicile_state"]},
    {"concept": "annual_income", "question": "What is your annual family income?", "type": "number", "options": None, "input_hint": "Enter amount in rupees", "fields": ["annual_income", "family_income", "annual_family_income"]},
    {"concept": "residence", "question": "What is your residence type?", "type": "single_choice", "options": ["urban", "rural"], "input_hint": "urban/rural", "fields": ["residence", "residence_area_type", "residence_status"]},
    {"concept": "education_level", "question": "What is your highest education?", "type": "single_choice", "options": ["below_10th", "10th_pass", "12th_pass", "graduate", "post_graduate", "phd"], "input_hint": "Select education level", "fields": ["education_level", "current_class", "course_level"]},
    {"concept": "occupation", "question": "What is your occupation?", "type": "single_choice", "options": ["student", "farmer", "self_employed", "salaried", "unemployed", "business", "homemaker", "retired"], "input_hint": "Select occupation", "fields": ["occupation", "occupation_type", "employment_status"]},
    {"concept": "marital_status", "question": "What is your marital status?", "type": "single_choice", "options": ["single", "married", "divorced", "widowed"], "input_hint": "Select marital status", "fields": ["marital_status"]},
    {"concept": "has_aadhaar", "question": "Do you have Aadhaar card?", "type": "boolean", "options": ["yes", "no"], "input_hint": "yes/no", "fields": ["has_aadhaar", "has_aadhaar_card"]},
    {"concept": "has_bank_account", "question": "Do you have a bank account?", "type": "boolean", "options": ["yes", "no"], "input_hint": "yes/no", "fields": ["has_bank_account", "has_savings_bank_account"]},
    {"concept": "is_disabled", "question": "Do you have any disability?", "type": "boolean", "options": ["yes", "no"], "input_hint": "yes/no", "fields": ["is_disabled", "is_differently_abled"]},
    {"concept": "is_nri", "question": "Are you an NRI?", "type": "boolean", "options": ["yes", "no"], "input_hint": "yes/no", "fields": ["is_nri"]},
    {"concept": "is_citizen", "question": "Are you an Indian citizen?", "type": "boolean", "options": ["yes", "no"], "input_hint": "yes/no", "fields": ["is_citizen", "is_indian_citizen", "is_citizen_of_india"]},
]

# Add base concepts to data
data['concepts'].extend(base_concepts)

# Also add mappings for these base concepts to field_to_concept
base_mappings = {
    "age": "age",
    "gender": "gender",
    "category": "category",
    "state": "state",
    "annual_income": "annual_income",
    "residence": "residence",
    "education_level": "education_level",
    "occupation": "occupation",
    "marital_status": "marital_status",
    "has_aadhaar": "has_aadhaar",
    "has_bank_account": "has_bank_account",
    "is_disabled": "is_disabled",
    "is_nri": "is_nri",
    "is_citizen": "is_citizen",
}

data['field_to_concept'].update(base_mappings)

# Save updated registry
with open('C:/yojanamitra_complete/concept_registry.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f"Updated concepts: {len(data['concepts'])}")
print(f"Updated field mappings: {len(data['field_to_concept'])}")

# Show sample
for c in data['concepts'][-15:]:
    print(f"  {c['concept']}: type={c['type']}, fields={c['fields'][:2]}")