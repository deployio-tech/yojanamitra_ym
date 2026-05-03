"""
Eligibility Classifier Engine
Simple: All pass = ELIGIBLE, Any fail = INELIGIBLE, Any unknown = POSSIBLY
"""

# ============================================================
# FIELD MAPPING: User Profile → Condition Fields
# ============================================================
FIELD_MAP = {
    'age': 'age',
    'gender': 'gender',
    'caste': 'caste_category',
    'income': 'annual_family_income',  # or 'income'
    'state': 'domicile_state',
    'occupation': 'occupation',
    'education': 'highest_education_level',
    'is_farmer': 'is_farmer',
    'is_student': 'is_student',
    'is_widow': 'is_widow',
    'is_disabled': 'is_differently_abled',
    'is_minority': 'is_minority',
    'is_bpl': 'is_bpl',
    'has_bank_account': 'has_bank_account',
    'has_aadhaar': 'has_aadhaar',
    'employment_status': 'employment_status',
    'marital_status': 'marital_status',
    'is_rural': 'is_rural',
    'is_urban': 'is_urban',
    'is_landless': 'is_landless',
}

# ============================================================
# QUESTION TEMPLATES (for POSSIBLY_ELIGIBLE)
# ============================================================
QUESTION_TEMPLATES = {
    'is_farmer': 'Are you a farmer?',
    'is_student': 'Are you currently a student?',
    'is_widow': 'Are you a widow?',
    'is_differently_abled': 'Do you have a disability?',
    'is_minority': 'Do you belong to a minority community?',
    'is_bpl': 'Do you have a BPL card?',
    'has_bank_account': 'Do you have a bank account?',
    'has_aadhaar': 'Do you have an Aadhaar card?',
    'is_landless': 'Do you own any agricultural land?',
    'employment_status': 'What is your employment status?',
    'education': 'What is your highest education level?',
    'is_rural': 'Do you live in a rural area?',
    'is_urban': 'Do you live in an urban area?',
    'marital_status': 'What is your marital status?',
}

# ============================================================
# MATCH FUNCTIONS
# ============================================================
def match_age(user_age, min_age, max_age):
    """Check if user age falls within range."""
    if user_age is None:
        return None  # Unknown
    if min_age and user_age < min_age:
        return False  # Fail
    if max_age and user_age > max_age:
        return False  # Fail
    return True  # Pass

def match_gender(user_gender, condition):
    """Check if gender matches."""
    if condition == 'any' or condition is None:
        return True
    if user_gender is None:
        return None  # Unknown
    return user_gender.lower() == condition.lower()

def match_list(user_val, condition_list):
    """Check if user value is in condition list."""
    if not condition_list:  # Empty = universal
        return True
    if user_val is None:
        return None  # Unknown
    if isinstance(condition_list, str):
        condition_list = [condition_list]
    
    user_str = str(user_val).lower()
    for c in condition_list:
        if str(c).lower() == user_str:
            return True
    return False

def match_boolean(user_val, required):
    """Check boolean condition."""
    if required is None:  # null = no restriction
        return True
    if user_val is None:
        return None  # Unknown
    # Convert user_val to boolean
    user_bool = user_val in ['true', 'True', True, 'Yes', 'yes', 1, '1']
    req_bool = required in ['true', 'True', True, 'Yes', 'yes', 1, '1']
    return user_bool == req_bool

def match_income(user_income, max_income, min_income):
    """Check income bounds."""
    if max_income is None and min_income is None:
        return True  # No restriction
    if user_income is None:
        return None  # Unknown
    if max_income and user_income > max_income:
        return False
    if min_income and user_income < min_income:
        return False
    return True

# ============================================================
# MAIN EVALUATION FUNCTION
# ============================================================
def evaluate_scheme(user_profile, conditions):
    """
    Evaluate a single scheme for a user.
    """
    unknown_fields = []
    
    # Adversarial Block: Is this even for individuals?
    is_individual = conditions.get('is_individual_scheme')
    if is_individual is False or is_individual == 'false' or is_individual == 'False':
        return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
    
    # Age
    result = match_age(
        user_profile.get('age'),
        conditions.get('min_age'),
        conditions.get('max_age')
    )
    if result is False:
        return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
    if result is None:
        unknown_fields.append('age')
    
    # Gender
    result = match_gender(
        user_profile.get('gender'),
        conditions.get('gender')
    )
    if result is False:
        return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
    if result is None:
        unknown_fields.append('gender')
    
    # Income
    income = user_profile.get('annual_family_income') or user_profile.get('income')
    try:
        income = float(income) if income is not None else None
    except ValueError:
        income = None
        
    result = match_income(
        income,
        conditions.get('income_annual_max'),
        conditions.get('income_annual_min')
    )
    if result is False:
        return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
    if result is None:
        unknown_fields.append('income')
    
    # Caste
    result = match_list(
        user_profile.get('caste'),
        conditions.get('caste_category')
    )
    if result is False:
        return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
    if result is None:
        unknown_fields.append('caste')
    
    # Occupation
    result = match_list(
        user_profile.get('occupation'),
        conditions.get('occupation')
    )
    if result is False:
        return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
    if result is None:
        unknown_fields.append('occupation')
    
    # State
    result = match_list(
        user_profile.get('state'),
        conditions.get('domicile_state')
    )
    if result is False:
        return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
    if result is None:
        unknown_fields.append('state')
    
    # Boolean fields
    boolean_fields = [
        'is_farmer', 'is_student', 'is_widow', 'is_differently_abled',
        'is_minority', 'is_bpl', 'has_bank_account', 'has_aadhaar',
        'is_landless', 'is_rural', 'is_urban'
    ]
    
    for field in boolean_fields:
        condition_val = conditions.get(field)
        if condition_val is None:
            continue  # No restriction
        user_val = user_profile.get(field)
        result = match_boolean(user_val, condition_val)
        if result is False:
            return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
        if result is None:
            unknown_fields.append(field)
            
    # String / List fields
    string_fields = {
        'marital_status': 'marital_status',
        'employment_status': 'employment_status',
        'min_education': 'education'
    }
    
    for cond_key, prof_key in string_fields.items():
        cond_val = conditions.get(cond_key)
        if cond_val is None or cond_val == 'any' or cond_val == 'none':
            continue
        user_val = user_profile.get(prof_key)
        result = match_list(user_val, cond_val)
        if result is False:
            return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
        if result is None:
            unknown_fields.append(prof_key)
            
    # Adversarial Block: Hyper-specific constraints (e.g. Bravery awards, Disease types)
    custom_required = conditions.get('custom_verification_required')
    if custom_required in [True, 'true', 'True']:
        reason = conditions.get('custom_verification_reason') or "Are you eligible for the specific special criteria of this scheme?"
        # Force into possibly eligible by adding to unknown fields
        unknown_fields.append(reason)
    
    # Check unknowns
    if unknown_fields:
        questions = []
        for f in unknown_fields:
            if f in QUESTION_TEMPLATES:
                questions.append(QUESTION_TEMPLATES[f])
            else:
                # If it's a custom adversarial verification string, append it directly
                questions.append(f)
                
        question_text = 'We need to know: ' + ', '.join(questions)
        return {
            'status': 'POSSIBLY_ELIGIBLE',
            'unknown_fields': unknown_fields,
            'question_text': question_text
        }
    
    return {'status': 'ELIGIBLE', 'unknown_fields': [], 'question_text': None}

# ============================================================
# BATCH EVALUATION
# ============================================================
def evaluate_all_schemes(user_profile, all_conditions, db_schemes_map=None):
    """
    Evaluate all schemes for a user.
    Returns grouped results.
    """
    eligible = []
    possibly = []
    
    for scheme_id, conditions in all_conditions.items():
        result = evaluate_scheme(user_profile, conditions)
        
        scheme_name = db_schemes_map.get(scheme_id, "Unknown Scheme") if db_schemes_map else "Unknown Scheme"
        
        if result['status'] == 'ELIGIBLE':
            eligible.append({
                'scheme_id': scheme_id,
                'scheme_name': scheme_name,
                **result
            })
        elif result['status'] == 'POSSIBLY_ELIGIBLE':
            possibly.append({
                'scheme_id': scheme_id,
                'scheme_name': scheme_name,
                **result
            })
        # INELIGIBLE: Don't include
    
    return {
        'eligible': eligible,
        'possibly_eligible': possibly,
        'summary': {
            'total_schemes': len(all_conditions),
            'shown_to_user': len(eligible) + len(possibly),
            'hidden': len(all_conditions) - len(eligible) - len(possibly)
        }
    }
