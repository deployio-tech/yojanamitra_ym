"""
Eligibility Classifier Engine
Simple: All pass = ELIGIBLE, Any fail = INELIGIBLE, Any unknown = POSSIBLY
"""

import sqlite3
import json
import os

DB_PATH = os.getenv('DB_PATH', 'instance/yojanamitra.db')

# ============================================================
# QUESTION TEMPLATES (for POSSIBLY_ELIGIBLE)
# ============================================================

QUESTION_TEMPLATES = {
    'age': 'What is your age?',
    'gender': 'What is your gender?',
    'caste': 'What is your caste/category?',
    'income': 'What is your annual family income?',
    'state': 'Which state do you live in?',
    'occupation': 'What is your occupation?',
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
    'marital_status': 'What is your marital status?',
    'is_rural': 'Do you live in a rural area?',
    'is_urban': 'Do you live in an urban area?',
}

# ============================================================
# USER PROFILE FIELD MAPPING
# ============================================================

PROFILE_MAP = {
    'age': 'age',
    'gender': 'gender',
    'caste': 'caste',
    'caste_category': 'caste',
    'income': 'annual_family_income',
    'annual_family_income': 'annual_family_income',
    'income_annual_max': 'annual_family_income',
    'income_annual_min': 'annual_family_income',
    'state': 'state',
    'domicile_state': 'state',
    'district': 'district',
    'block_taluk': 'block_taluk',
    'occupation': 'occupation',
    'employment_status': 'employment_status',
    'marital_status': 'marital_status',
    
    # Booleans / Specialized
    'is_farmer': 'is_farmer',
    'is_student': 'is_student',
    'is_widow': 'is_widow_single_woman',
    'is_widow_single_woman': 'is_widow_single_woman',
    'is_disabled': 'disability',
    'is_differently_abled': 'disability',
    'is_minority': 'minority_status',
    'minority_status': 'minority_status',
    'is_bpl': 'is_bpl', # Derived
    'has_bank_account': 'has_bank_account',
    'bank_account_available': 'bank_account_available',
    'has_aadhaar': 'aadhaar_available',
    'aadhaar_available': 'aadhaar_available',
    'is_landless': 'is_landless',
    'is_rural': 'residence',
    'is_urban': 'is_urban',
    'is_pensioner': 'is_pensioner',
    'is_bocw_registered': 'is_bocw_registered',
    'is_school_dropout': 'is_school_dropout',
    'is_first_gen_student': 'is_first_gen_student',
    'is_citizen': 'is_citizen',
    'has_pucca_house': 'has_pucca_house',
    'is_tribal': 'is_tribal',
    'is_orphan': 'is_orphan',
    'is_senior_citizen': 'is_senior_citizen',
    'aadhaar_linked_bank': 'aadhaar_linked_bank',
    'mobile_linked_bank': 'mobile_linked_bank',
    'ration_card_available': 'ration_card_available',
    'income_certificate_available': 'income_certificate_available',
    'domicile_status': 'domicile_status',
    'is_tenant_farmer': 'is_tenant_farmer',
    'willing_to_submit_docs': 'willing_to_submit_docs',
    
    # Numeric/Counts
    'num_daughters': 'num_daughters',
    'total_family_members': 'total_family_members',
    'child_age': 'child_age',
    'land_size_acres': 'land_size_acres',
    'disability_percentage': 'disability_percentage',
}

# ============================================================
# MATCH FUNCTIONS
# ============================================================

def normalize_bool(val):
    """Convert various boolean representations to True/False/None."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        val_lower = val.lower().strip()
        if val_lower in ['true', 'yes', '1', 'y']:
            return True
        if val_lower in ['false', 'no', '0', 'n']:
            return False
    if isinstance(val, int):
        if val == 1: return True
        if val == 0: return False
    return None


def normalize_caste(val):
    """Normalize caste to standard format."""
    if val is None:
        return None
    val = str(val).strip()
    upper = val.upper()
    
    caste_map = {
        'GENERAL': 'General',
        'GEN': 'General',
        'SC': 'SC',
        'SCHEDULED CASTE': 'SC',
        'ST': 'ST',
        'SCHEDULED TRIBE': 'ST',
        'OBC': 'OBC',
        'OTHER BACKWARD CLASS': 'OBC',
        'OBC-NCL': 'OBC',
        'OBC - NCL': 'OBC',
        'EWS': 'EWS',
        'ECONOMICALLY WEAKER SECTION': 'EWS',
        'SEBC': 'SEBC',
        'SOCIAL AND ECONOMICALLY BACKWARD': 'SEBC',
    }
    return caste_map.get(upper, val)


def normalize_gender(val):
    """Normalize gender to standard format."""
    if val is None:
        return None
    val = str(val).strip().lower()
    
    if val in ['male', 'm', 'man', 'boy']:
        return 'male'
    if val in ['female', 'f', 'woman', 'girl']:
        return 'female'
    if val in ['transgender', 'trans']:
        return 'transgender'
    return val


def normalize_income(val):
    """Normalize income to integer."""
    if val is None:
        return None
    try:
        return int(float(val))
    except:
        return None


def normalize_state(val):
    """Normalize state name."""
    if val is None:
        return None
    return str(val).strip().title()


def normalize_residence(val):
    """Check if residence is rural or urban."""
    if val is None:
        return None
    val_lower = str(val).lower()
    if 'rural' in val_lower:
        return 'rural'
    if 'urban' in val_lower:
        return 'urban'
    return val_lower


def normalize_employment(val):
    """Normalize employment status."""
    if val is None:
        return None
    val = str(val).strip().lower()
    
    if val in ['employed', 'private', 'government', 'govt', 'salaried']:
        return 'employed'
    if val in ['self employed', 'self-employed', 'selfemployed', 'business']:
        return 'self_employed'
    if val in ['unemployed', 'jobless', 'no job']:
        return 'unemployed'
    if val in ['student']:
        return 'student'
    return val


def normalize_education(val):
    """Normalize education level."""
    if val is None:
        return None
    val = str(val).strip().lower()
    
    if any(x in val for x in ['10th', 'secondary', 'matric']):
        return 'secondary'
    if any(x in val for x in ['12th', 'higher secondary', 'puc', 'inter']):
        return 'higher_secondary'
    if any(x in val for x in ['degree', 'graduation', 'graduate', 'bachelor', 'b.a', 'b.sc', 'b.com']):
        return 'graduate'
    if any(x in val for x in ['master', 'postgrad', 'pg', 'm.a', 'm.sc']):
        return 'postgraduate'
    if any(x in val for x in ['phd', 'doctorate', 'ph.d']):
        return 'phd'
    if any(x in val for x in ['none', 'no education', 'illiterate', 'primary']):
        return 'none'
    return val


# ============================================================
# MATCH FUNCTIONS
# ============================================================

def match_age(user_age, min_age, max_age):
    """Check if user age falls within range."""
    # PASS-BY-DEFAULT: If no constraints, it is a PASS regardless of user data
    if min_age is None and max_age is None:
        return True
        
    if user_age is None:
        return None  # Unknown only if there ARE constraints
    try:
        user_age = int(user_age)
    except:
        return None
    
    if min_age is not None and user_age < min_age:
        return False  # Fail
    if max_age is not None and user_age > max_age:
        return False  # Fail
    return True  # Pass


def match_gender(user_gender, condition):
    """Check if gender matches."""
    # PASS-BY-DEFAULT: If no constraints, it is a PASS regardless of user data
    if condition is None or str(condition).lower() == 'any' or condition == '':
        return True
    
    user = normalize_gender(user_gender)
    if user is None:
        return None  # Unknown only if there ARE constraints
    
    condition = str(condition).lower().strip()
    return user == condition


def match_list(user_val, condition_list):
    """Check if user value is in condition list."""
    # PASS-BY-DEFAULT: If no constraints, it is a PASS regardless of user data
    if not condition_list or condition_list == [] or condition_list == ['Any'] or condition_list == 'Any':
        return True
        
    if user_val is None:
        return None  # Unknown only if there ARE constraints
    
    if isinstance(condition_list, str):
        condition_list = [condition_list]
    
    # Normalize for comparison
    condition_list_normalized = [str(c).strip().title() for c in condition_list]
    user_str = str(user_val).strip().title()
    
    return user_str in condition_list_normalized


def match_boolean(user_val, required):
    """Check boolean condition."""
    if required is None:
        return True  # No restriction
    
    user_bool = normalize_bool(user_val)
    if user_bool is None:
        return None  # Unknown
    
    req_bool = normalize_bool(required)
    return user_bool == req_bool


def match_income(user_income, max_income, min_income):
    """Check income bounds."""
    if max_income is None and min_income is None:
        return True  # No restriction
    
    income = normalize_income(user_income)
    if income is None:
        return None  # Unknown
    
    if max_income is not None and income > max_income:
        return False
    if min_income is not None and income < min_income:
        return False
    return True


def match_residence(user_residence, is_rural_required, is_urban_required):
    """Check residence requirement."""
    if is_rural_required is None and is_urban_required is None:
        return True  # No restriction
    
    user = normalize_residence(user_residence)
    if user is None:
        return None  # Unknown
    
    if is_rural_required and user == 'rural':
        return True
    if is_urban_required and user == 'urban':
        return True
    
    # If both are set, user must match one
    if is_rural_required or is_urban_required:
        return False
    
    return True


def match_education(user_edu, min_edu):
    """Check education level meets minimum."""
    # PASS-BY-DEFAULT: If no constraints, it is a PASS regardless of user data
    if min_edu is None or str(min_edu).lower() == 'any' or min_edu == '':
        return True
    
    user = normalize_education(user_edu)
    if user is None:
        return None  # Unknown only if there ARE constraints
    
    edu_levels = {
        'none': 0,
        'primary': 1,
        'secondary': 2,
        'higher_secondary': 3,
        'graduate': 4,
        'postgraduate': 5,
        'phd': 6,
    }
    
    user_level = edu_levels.get(user, 0)
    min_level = edu_levels.get(str(min_edu).lower().strip() if isinstance(min_edu, str) else 'none', 0)
    
    return user_level >= min_level


def match_employment(user_emp, condition):
    """Check employment status."""
    if condition is None or condition == 'any':
        return True  # No restriction
    
    user = normalize_employment(user_emp)
    if user is None:
        return None  # Unknown
    
    condition = normalize_employment(condition)
    return user == condition


def match_marital(user_marital, condition):
    """Check marital status."""
    if condition is None or condition == 'any':
        return True
    
    user = str(user_marital).strip().lower() if user_marital else None
    if user is None:
        return None
    
    condition = str(condition).strip().lower()
    
    if condition == 'any':
        return True
    
    return user == condition


# ============================================================
# MAIN EVALUATION FUNCTION
# ============================================================

def evaluate_scheme(user_profile, conditions):
    """
    Evaluate a single scheme for a user.
    
    Returns:
        {
            'status': 'ELIGIBLE' | 'INELIGIBLE' | 'POSSIBLY_ELIGIBLE',
            'unknown_fields': ['is_farmer', 'has_bank_account'],
            'question_text': 'We need to know: Are you a farmer?, Do you have a bank account?'
        }
    """
    unknown_fields = []
    
    # ===== ADVERSARIAL: INSTITUTIONAL CHECK =====
    is_individual = conditions.get('is_individual_scheme')
    if is_individual is False or is_individual == 'false' or is_individual == 'False':
        return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
    
    # Pre-populate some derived defaults only if they aren't provided
    if not user_profile.get('age') and user_profile.get('dob'):
        try:
             from datetime import datetime
             dob = datetime.strptime(user_profile['dob'], '%Y-%m-%d')
             user_profile['age'] = (datetime.now() - dob).days // 365
        except: pass
    
    # ===== AGE =====
    result = match_age(
        user_profile.get('age'),
        conditions.get('min_age'),
        conditions.get('max_age')
    )
    if result is False:
        return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
    if result is None:
        unknown_fields.append('age')
    
    # ===== GENDER =====
    result = match_gender(
        user_profile.get('gender'),
        conditions.get('gender')
    )
    if result is False:
        return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
    if result is None:
        unknown_fields.append('gender')
    
    # ===== INCOME =====
    income = user_profile.get('annual_family_income') or user_profile.get('income')
    result = match_income(
        income,
        conditions.get('income_annual_max'),
        conditions.get('income_annual_min')
    )
    if result is False:
        return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
    if result is None:
        unknown_fields.append('income')
    
    # ===== CASTE =====
    result = match_list(
        user_profile.get('caste'),
        conditions.get('caste_category')
    )
    if result is False:
        return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
    if result is None:
        unknown_fields.append('caste')
    
    # ===== OCCUPATION =====
    result = match_list(
        user_profile.get('occupation'),
        conditions.get('occupation')
    )
    if result is False:
        return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
    if result is None:
        unknown_fields.append('occupation')
    
    # ===== STATE =====
    result = match_list(
        user_profile.get('state'),
        conditions.get('domicile_state')
    )
    if result is False:
        return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
    if result is None:
        unknown_fields.append('state')
    
    # ===== EDUCATION =====
    result = match_education(
        user_profile.get('highest_education_level'),
        conditions.get('min_education')
    )
    if result is False:
        return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
    if result is None:
        unknown_fields.append('education')
    
    # ===== EMPLOYMENT =====
    result = match_employment(
        user_profile.get('employment_status'),
        conditions.get('employment_status')
    )
    if result is False:
        return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
    if result is None:
        unknown_fields.append('employment_status')
    
    # ===== MARITAL STATUS =====
    result = match_marital(
        user_profile.get('marital_status'),
        conditions.get('marital_status')
    )
    if result is False:
        return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
    if result is None:
        unknown_fields.append('marital_status')
    
    # ===== RESIDENCE =====
    result = match_residence(
        user_profile.get('residence'),
        conditions.get('is_rural'),
        conditions.get('is_urban')
    )
    if result is False:
        return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
    if result is None:
        unknown_fields.append('is_rural')
    
    # ===== DYNAMIC FIELDS MATCHER (Covers 60+ fields) =====
    # We iterate over every key in the scheme conditions JSON.
    # If the key isn't already handled above, we try to match it dynamically.
    handled_keys = ['min_age', 'max_age', 'income_annual_max', 'income_annual_min', 
                    'caste_category', 'occupation', 'domicile_state', 'min_education', 
                    'employment_status', 'marital_status', 'is_rural', 'is_urban', 'gender']
    
    for cond_key, cond_val in conditions.items():
        # 0. Skip metadata and handled keys (Strict requirement focus)
        # We skip any key that isn't a real user trait (starts with metadata prefixes or ends with source hints)
        is_metadata = (
            cond_key in handled_keys or 
            cond_key.startswith('custom_') or 
            cond_key.startswith('extraction_') or 
            cond_key.endswith('_found_in') or
            cond_key in ['is_individual_scheme', 'source_text', 'confidence']
        )
        if is_metadata:
            continue
            
        # Get the profile field this condition relates to
        profile_field = PROFILE_MAP.get(cond_key, cond_key)
        user_val = user_profile.get(profile_field)
        
        # Determine how to match based on condition type
        # 1. Explicit Boolean check (True/False only, not 2, 3, etc.)
        if isinstance(cond_val, bool):
            user_bool = normalize_bool(user_val)
            if user_bool is False and cond_val is True:
                return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
            if user_bool is True and cond_val is False:
                return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
            if user_bool is None:
                unknown_fields.append(cond_key)
            continue
            
        # 2. Numeric match (Higher priority than lenient boolean)
        if isinstance(cond_val, (int, float)):
            if user_val is not None:
                try:
                    uv = float(user_val)
                    if uv < float(cond_val): # Requires at least X
                        return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
                except: 
                    unknown_fields.append(cond_key)
            else:
                unknown_fields.append(cond_key)
            continue
            
        # 3. String/List match (for categories we didn't handle explicitly)
        if isinstance(cond_val, (list, str)) and cond_val:
            result = match_list(user_val, cond_val)
            if result is False: return {'status': 'INELIGIBLE', 'unknown_fields': [], 'question_text': None}
            if result is None: unknown_fields.append(cond_key)
            continue
    # ===== CHECK UNKNOWNS =====
    if unknown_fields:
        questions = []
        for f in unknown_fields:
            if f in QUESTION_TEMPLATES:
                questions.append(QUESTION_TEMPLATES[f])
            else:
                questions.append(f)
        question_text = 'We need to know: ' + ', '.join(questions)
        return {
            'status': 'POSSIBLY_ELIGIBLE',
            'unknown_fields': unknown_fields,
            'question_text': question_text
        }
    
    return {'status': 'ELIGIBLE', 'unknown_fields': [], 'question_text': None}


# ============================================================
# DATA LOADING
# ============================================================

def load_user_profile(user_id=None, email=None):
    """Load user profile details from the user table."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if email:
        cursor.execute('SELECT * FROM user WHERE email = ?', (email,))
    elif user_id:
        cursor.execute('SELECT * FROM user WHERE id = ?', (user_id,))
    else:
        return None
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    # Convert to dict
    profile = {}
    for key in row.keys():
        profile[key] = row[key]
    
    # --- DATA NORMALIZATION & MAPPING ---
    # Ensure income is pulled correctly
    profile['annual_family_income'] = profile.get('annual_family_income') or profile.get('income')
    
    # Map legacy or slightly different field names
    profile['is_minority'] = profile.get('minority_status') or profile.get('is_minority') or profile.get('isMinority')
    profile['has_bank_account'] = profile.get('bank_account_available') or profile.get('has_bank_account') or profile.get('bankAccountAvailable')
    
    # Ration Card / BPL Inference
    ration_type = str(profile.get('ration_card_type') or profile.get('rationCardType') or '').upper()
    if ration_type in ['BPL', 'ANTYODAYA', 'AAY', 'PRIORITY HOUSEHOLD']:
        profile['is_bpl'] = 'Yes'
    else:
        profile['is_bpl'] = profile.get('is_bpl')
    
    # Occupation Inference
    occ = str(profile.get('occupation') or '').lower()
    if 'student' in occ:
        profile['is_student'] = 'Yes'
    if 'farmer' in occ or 'agriculture' in occ:
        profile['is_farmer'] = 'Yes'
    
    return profile


def load_conditions(scheme_id=None):
    """Load extracted conditions from gemini_prefill table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if scheme_id:
        cursor.execute(
            'SELECT scheme_id, extracted_json, confidence FROM gemini_prefill WHERE scheme_id = ? AND status = "success"',
            (scheme_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {row[0]: json.loads(row[1])}
        return {}
    
    cursor.execute('SELECT scheme_id, extracted_json, confidence FROM gemini_prefill WHERE status = "success"')
    rows = cursor.fetchall()
    conn.close()
    
    conditions = {}
    for row in rows:
        conditions[str(row[0])] = json.loads(row[1])
    
    return conditions


def load_scheme_names(scheme_ids):
    """Load scheme names for given IDs."""
    if not scheme_ids:
        return {}
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    placeholders = ','.join(['?'] * len(scheme_ids))
    cursor.execute(f'SELECT id, name FROM scheme WHERE id IN ({placeholders})', scheme_ids)
    rows = cursor.fetchall()
    conn.close()
    
    return {str(row[0]): row[1] for row in rows}


# ============================================================
# BATCH EVALUATION
# ============================================================

def evaluate_all_schemes(user_profile, all_conditions=None):
    """
    Evaluate all schemes for a user.
    Returns grouped results.
    """
    if all_conditions is None:
        all_conditions = load_conditions()
    
    eligible = []
    possibly = []
    
    for scheme_id, conditions in all_conditions.items():
        result = evaluate_scheme(user_profile, conditions)
        
        if result['status'] == 'ELIGIBLE':
            eligible.append({
                'scheme_id': int(scheme_id),
                **result
            })
        elif result['status'] == 'POSSIBLY_ELIGIBLE':
            possibly.append({
                'scheme_id': int(scheme_id),
                **result
            })
        # INELIGIBLE: Don't include
    
    # Add scheme names
    all_ids = [e['scheme_id'] for e in eligible] + [p['scheme_id'] for p in possibly]
    names = load_scheme_names(all_ids)
    
    for e in eligible:
        e['scheme_name'] = names.get(str(e['scheme_id']), 'Unknown')
    
    for p in possibly:
        p['scheme_name'] = names.get(str(p['scheme_id']), 'Unknown')
    
    return {
        'eligible': eligible,
        'possibly_eligible': possibly,
        'summary': {
            'total_schemes': len(all_conditions),
            'eligible_count': len(eligible),
            'possibly_count': len(possibly),
            'hidden_ineligible': len(all_conditions) - len(eligible) - len(possibly)
        }
    }


# ============================================================
# MAIN TEST
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("ELIGIBILITY CLASSIFIER TEST")
    print("=" * 60)
    
    # Load user profile (Shreyas)
    user = load_user_profile(email='shreyas6504@gmail.com')
    
    if not user:
        print("User not found!")
    else:
        print(f"\nUser: {user.get('name', 'Unknown')}")
        print(f"Profile summary:")
        print(f"  Age: {user.get('age')}")
        print(f"  Gender: {user.get('gender')}")
        print(f"  Caste: {user.get('caste')}")
        print(f"  State: {user.get('state')}")
        print(f"  Occupation: {user.get('occupation')}")
        print(f"  Income: {user.get('annual_family_income')}")
        print(f"  Education: {user.get('highest_education_level')}")
        print(f"  Employment: {user.get('employment_status')}")
        print(f"  Residence: {user.get('residence')}")
        print(f"  Is Farmer: {user.get('is_farmer')}")
        print(f"  Has Bank: {user.get('has_bank_account')}")
        
        print("\nLoading conditions...")
        conditions = load_conditions()
        print(f"Loaded {len(conditions)} schemes with conditions")
        
        print("\nEvaluating all schemes...")
        results = evaluate_all_schemes(user, conditions)
        
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        
        print(f"\nTotal schemes evaluated: {results['summary']['total_schemes']}")
        print(f"ELIGIBLE: {results['summary']['eligible_count']}")
        print(f"POSSIBLY ELIGIBLE: {results['summary']['possibly_count']}")
        print(f"HIDDEN (INELIGIBLE): {results['summary']['hidden_ineligible']}")
        
        print("\n--- ELIGIBLE SCHEMES ---")
        for s in results['eligible'][:20]:
            print(f"  {s['scheme_id']}: {s['scheme_name'][:50]}")
        
        if len(results['eligible']) > 20:
            print(f"  ... and {len(results['eligible']) - 20} more")
        
        print("\n--- POSSIBLY ELIGIBLE (first 10) ---")
        for s in results['possibly_eligible'][:10]:
            print(f"  {s['scheme_id']}: {s['scheme_name'][:40]}")
            print(f"    Questions: {s['question_text'][:80]}...")
        
        if len(results['possibly_eligible']) > 10:
            print(f"  ... and {len(results['possibly_eligible']) - 10} more")
