import sys
sys.path.insert(0, '.')
from app import app, User, Scheme
from app.engine.eligibility import (
    EligibilityEngine, 
    get_canonical_field,
    NON_ANSWERABLE_FIELDS
)
from app.engine.questions import is_user_answerable

# Check which remaining missing fields are actually system/non-answerable
remaining_fields = [
    'class_level', 'land_ownership_or_lease_duration', 'land_lease_period_min',
    'residency_duration', 'student_class_min', 'residency_duration_years',
    'total_subsidy_vs_term_loan', 'student_class_max', 'loan_disbursement_date_min',
    'annual_family_income_max', 'continuous_membership_duration', 'training_duration_cottage_industry',
    'loan_sanction_date_min', 'research_scholar_registration_date', 'sea_fishing_experience_male_min',
    'minimum_educational_qualification', 'labour_welfare_fund_payment_duration', 'age_min_male',
    'age_min_female', 'minimum_training_duration'
]

print('Analyzing remaining missing fields:')
print('=' * 60)

for field in remaining_fields:
    is_user = is_user_answerable(field)
    is_non_answerable = field in NON_ANSWERABLE_FIELDS
    
    # Check if it's in canonical groups
    canonical = get_canonical_field(field)
    is_canonical = canonical in ['citizenship', 'bank_account', 'consent']
    
    print(f'{field}:')
    print(f'  is_user_answerable: {is_user}')
    print(f'  in NON_ANSWERABLE_FIELDS: {is_non_answerable}')
    print(f'  canonical: {canonical}')
    print()

# Check how many are truly USER-answerable
truly_user = [f for f in remaining_fields if is_user_answerable(f) and f not in NON_ANSWERABLE_FIELDS]
print(f'Truly user-answerable: {len(truly_user)}')
print(truly_user)