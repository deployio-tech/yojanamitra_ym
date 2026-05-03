"""
Investigate False Positives in Eligibility Classifier
Compares extracted conditions vs actual eligibility text for schemes
"""

import sqlite3
import json

DB_PATH = 'instance/yojanamitra.db'

SCHEME_IDS = [1, 14, 21, 43, 101, 211, 618, 619]

USER_PROFILE = {
    'name': 'Shreyas',
    'age': 21,
    'gender': 'Male',
    'caste': 'OBC',
    'state': 'Karnataka',
    'occupation': 'Student',
    'annual_family_income': 200000,
    'highest_education_level': 'Graduation',
    'employment_status': 'Student',
    'residence': 'Rural',
    'is_farmer': False,
    'has_bank_account': None,
}


def load_conditions(scheme_ids):
    """Load extracted conditions from gemini_prefill table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    placeholders = ','.join(['?'] * len(scheme_ids))
    cursor.execute(f'''
        SELECT scheme_id, extracted_json, confidence 
        FROM gemini_prefill 
        WHERE scheme_id IN ({placeholders}) AND status = "success"
    ''', scheme_ids)
    
    rows = cursor.fetchall()
    conn.close()
    
    conditions = {}
    for row in rows:
        conditions[row[0]] = json.loads(row[1])
    
    return conditions


def load_schemes(scheme_ids):
    """Load actual scheme data from scheme table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    placeholders = ','.join(['?'] * len(scheme_ids))
    cursor.execute(f'''
        SELECT id, name, eligibility, benefits 
        FROM scheme 
        WHERE id IN ({placeholders})
    ''', scheme_ids)
    
    rows = cursor.fetchall()
    conn.close()
    
    schemes = {}
    for row in rows:
        schemes[row[0]] = {
            'id': row[0],
            'name': row[1],
            'eligibility': row[2],
            'benefits': row[3]
        }
    
    return schemes


def evaluate_scheme(user_profile, conditions):
    """Simulate the classifier logic."""
    issues = []
    
    # Check gender
    cond_gender = conditions.get('gender')
    if cond_gender and str(cond_gender).lower() != 'any':
        user_gender = str(user_profile.get('gender', '')).lower()
        if user_gender not in [str(cond_gender).lower(), 'any']:
            issues.append(f"Gender mismatch: user={user_gender}, required={cond_gender}")
    
    # Check age
    min_age = conditions.get('min_age')
    max_age = conditions.get('max_age')
    user_age = user_profile.get('age')
    if min_age and user_age < min_age:
        issues.append(f"Age below minimum: user={user_age}, min={min_age}")
    if max_age and user_age > max_age:
        issues.append(f"Age above maximum: user={user_age}, max={max_age}")
    
    # Check income
    max_income = conditions.get('income_annual_max')
    user_income = user_profile.get('annual_family_income')
    if max_income and user_income > max_income:
        issues.append(f"Income exceeds max: user={user_income}, max={max_income}")
    
    # Check caste
    cond_caste = conditions.get('caste_category')
    if cond_caste and cond_caste != []:
        if isinstance(cond_caste, str):
            cond_caste = [cond_caste]
        user_caste = str(user_profile.get('caste', '')).title()
        if user_caste not in [str(c).title() for c in cond_caste]:
            issues.append(f"Caste mismatch: user={user_caste}, required={cond_caste}")
    
    # Check state
    cond_state = conditions.get('domicile_state')
    if cond_state and cond_state != []:
        if isinstance(cond_state, str):
            cond_state = [cond_state]
        user_state = str(user_profile.get('state', '')).title()
        if user_state not in [str(s).title() for s in cond_state]:
            issues.append(f"State mismatch: user={user_state}, required={cond_state}")
    
    # Check occupation
    cond_occ = conditions.get('occupation')
    if cond_occ and cond_occ != []:
        if isinstance(cond_occ, str):
            cond_occ = [cond_occ]
        user_occ = str(user_profile.get('occupation', '')).title()
        if user_occ not in [str(o).title() for o in cond_occ]:
            issues.append(f"Occupation mismatch: user={user_occ}, required={cond_occ}")
    
    # Check education
    min_edu = conditions.get('min_education')
    edu_map = {'none': 0, 'primary': 1, 'secondary': 2, 'higher_secondary': 3, 'graduate': 4, 'postgraduate': 5}
    if min_edu:
        user_edu = str(user_profile.get('highest_education_level', '')).lower()
        user_level = 0
        for k, v in edu_map.items():
            if k in user_edu:
                user_level = max(user_level, v)
        min_level = edu_map.get(str(min_edu).lower(), 4)
        if user_level < min_level:
            issues.append(f"Education below minimum: user={user_edu}, min={min_edu}")
    
    # Check employment
    cond_emp = conditions.get('employment_status')
    if cond_emp and str(cond_emp).lower() != 'any':
        user_emp = str(user_profile.get('employment_status', '')).lower()
        if user_emp != str(cond_emp).lower():
            issues.append(f"Employment mismatch: user={user_emp}, required={cond_emp}")
    
    # Check residence
    is_rural = conditions.get('is_rural')
    is_urban = conditions.get('is_urban')
    if is_rural and str(user_profile.get('residence', '')).lower() != 'rural':
        issues.append(f"Not rural: user={user_profile.get('residence')}, required_rural=True")
    if is_urban and str(user_profile.get('residence', '')).lower() != 'urban':
        issues.append(f"Not urban: user={user_profile.get('residence')}, required_urban=True")
    
    # Check boolean fields
    bool_fields = [
        ('is_farmer', 'is_farmer'),
        ('is_student', 'is_student'),
        ('has_bank_account', 'has_bank_account'),
    ]
    for cond_field, profile_field in bool_fields:
        cond_val = conditions.get(cond_field)
        if cond_val is True:
            user_val = user_profile.get(profile_field)
            if user_val is None:
                issues.append(f"Missing required field: {cond_field}")
            elif user_val is False:
                issues.append(f"Boolean mismatch: {cond_field} required=True but user=False")
    
    return issues


def analyze_eligibility_text(eligibility_text, user_profile):
    """Check if user actually meets the real eligibility criteria."""
    issues = []
    
    if not eligibility_text:
        return ["No eligibility text found"]
    
    text = eligibility_text.lower()
    
    # Check for state restrictions
    states = ['karnataka', 'maharashtra', 'delhi', 'tamil nadu', 'kerala', 'west bengal', 'gujarat', 'rajasthan', 'uttar pradesh', 'bihar', 'madhya pradesh', 'andhra pradesh', 'telangana', 'punjab', 'haryana', 'odisha', 'jharkhand', 'chhattisgarh', 'uttarakhand', 'himachal pradesh', 'goa', 'sikkim', 'arunachal pradesh', 'nagaland', 'manipur', 'mizoram', 'tripura', 'meghalaya']
    
    for state in states:
        if state in text:
            user_state = str(user_profile.get('state', '')).lower()
            if state not in user_state:
                issues.append(f"State restriction in eligibility: requires {state}")
                break
    
    # Check for income limits
    if 'income' in text:
        import re
        income_matches = re.findall(r'(\d+)[,\s]*(\d+)*\s*(lakh|lacs?|rs\.?|rupees)', text, re.IGNORECASE)
        if income_matches:
            for match in income_matches:
                if len(match) >= 2 and match[1]:
                    limit = int(match[0] + match[1])
                    if 'lakh' in text or 'lac' in text:
                        limit *= 100000
                    if user_profile.get('annual_family_income', 0) > limit:
                        issues.append(f"Income exceeds actual limit: {limit}")
    
    # Check for specific occupation requirements
    occ_keywords = ['farmer', 'agricultural worker', 'weaver', ' artisan', 'small business', 'vendor', 'driver', 'teacher', 'engineer', 'doctor']
    for occ in occ_keywords:
        if occ in text:
            user_occ = str(user_profile.get('occupation', '')).lower()
            if occ not in user_occ:
                # Check if it's a requirement (not just mention)
                if f'must be {occ}' in text or f'for {occ}' in text or f'{occ} are eligible' in text:
                    issues.append(f"Occupation requirement in text: {occ}")
    
    # Check for gender-specific schemes
    if 'women only' in text or 'female only' in text or 'for women' in text:
        if user_profile.get('gender', '').lower() != 'female':
            issues.append("Women-only scheme in eligibility text")
    
    # Check for caste restrictions (non-OBC)
    if 'general' in text and 'obc' not in text:
        # Could be general category only
        pass  # OBC might still be eligible
    
    return issues


def main():
    print("=" * 70)
    print("FALSE POSITIVE INVESTIGATION - Eligibility Classifier")
    print("=" * 70)
    print(f"\nUser Profile: {USER_PROFILE['name']}")
    print(f"  Age: {USER_PROFILE['age']}, Gender: {USER_PROFILE['gender']}")
    print(f"  Caste: {USER_PROFILE['caste']}, State: {USER_PROFILE['state']}")
    print(f"  Occupation: {USER_PROFILE['occupation']}, Income: {USER_PROFILE['annual_family_income']}")
    print(f"  Education: {USER_PROFILE['highest_education_level']}, Residence: {USER_PROFILE['residence']}")
    print(f"  Is Farmer: {USER_PROFILE['is_farmer']}, Has Bank: {USER_PROFILE['has_bank_account']}")
    
    print("\n" + "-" * 70)
    print("Loading data...")
    
    conditions = load_conditions(SCHEME_IDS)
    schemes = load_schemes(SCHEME_IDS)
    
    print(f"Loaded {len(conditions)} scheme conditions from gemini_prefill")
    print(f"Loaded {len(schemes)} schemes from scheme table")
    
    print("\n" + "=" * 70)
    print("SCHEME-BY-SCHEME ANALYSIS")
    print("=" * 70)
    
    false_positives = []
    
    for scheme_id in SCHEME_IDS:
        print(f"\n{'='*70}")
        print(f"SCHEME ID: {scheme_id}")
        print("=" * 70)
        
        # Get scheme info
        scheme = schemes.get(scheme_id)
        if not scheme:
            print(f"  [NOT FOUND in scheme table]")
            continue
        
        print(f"  Name: {scheme['name'][:60]}...")
        print(f"\n  ACTUAL ELIGIBILITY TEXT:")
        print(f"  {scheme['eligibility'][:300]}...")
        
        # Get extracted conditions
        cond = conditions.get(scheme_id)
        if not cond:
            print(f"\n  [NO EXTRACTED CONDITIONS in gemini_prefill]")
            print(f"  Issue: Missing data in extracted conditions")
            continue
        
        print(f"\n  EXTRACTED CONDITIONS:")
        for key, val in cond.items():
            if val is not None and val != []:
                print(f"    {key}: {val}")
        
        # Evaluate with classifier logic
        classifier_issues = evaluate_scheme(USER_PROFILE, cond)
        
        print(f"\n  CLASSIFIER CHECK:")
        if not classifier_issues:
            print(f"    RESULT: ELIGIBLE (no conditions failed)")
        else:
            print(f"    RESULT: INELIGIBLE due to:")
            for issue in classifier_issues:
                print(f"      - {issue}")
        
        # Check actual eligibility text
        text_issues = analyze_eligibility_text(scheme['eligibility'], USER_PROFILE)
        
        print(f"\n  ACTUAL ELIGIBILITY CHECK:")
        if not text_issues:
            print(f"    No obvious conflicts found in eligibility text")
        else:
            print(f"    Potential conflicts:")
            for issue in text_issues:
                print(f"      - {issue}")
        
        # Determine false positive
        if not classifier_issues:
            # Check if there's a hidden conflict in the text
            has_fp = False
            fp_reason = ""
            
            # Common patterns that could cause FP
            if scheme['eligibility']:
                text = scheme['eligibility'].lower()
                
                # Check state
                for state in ['karnataka', 'maharashtra', 'delhi', 'tamil nadu', 'kerala']:
                    if state in text and USER_PROFILE['state'].lower() != state:
                        has_fp = True
                        fp_reason = f"State restriction: requires {state}, user is in {USER_PROFILE['state']}"
                        break
                
                # Check women-only
                if 'women' in text and 'female' in text and USER_PROFILE['gender'].lower() != 'female':
                    if 'only' in text or 'exclusively' in text:
                        has_fp = True
                        fp_reason = "Women-only scheme"
                        break
                
                # Check specific occupation
                if 'student' not in text and USER_PROFILE['occupation'] == 'Student':
                    if 'not applicable for students' in text or 'students not eligible' in text:
                        has_fp = True
                        fp_reason = "Students not eligible"
                        break
            
            if has_fp:
                false_positives.append({
                    'scheme_id': scheme_id,
                    'name': scheme['name'],
                    'reason': fp_reason,
                    'extracted_conditions': cond
                })
                print(f"\n  *** FALSE POSITIVE DETECTED ***")
                print(f"  Reason: {fp_reason}")
                print(f"  Root Cause: Likely misaligned condition extraction")
            else:
                print(f"\n  => This appears to be a TRUE POSITIVE (correctly marked ELIGIBLE)")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    if false_positives:
        print(f"\nFound {len(false_positives)} FALSE POSITIVES:")
        for fp in false_positives:
            print(f"  - Scheme {fp['scheme_id']}: {fp['name'][:40]}")
            print(f"    Reason: {fp['reason']}")
    else:
        print("\nNo false positives found in the tested schemes.")


if __name__ == '__main__':
    import sys
    output_buffer = []
    
    class OutputCapture:
        def write(self, text):
            output_buffer.append(text)
        def flush(self):
            pass
    
    sys.stdout = OutputCapture()
    main()
    sys.stdout = sys.__stdout__
    
    # Write output to file
    output = ''.join(output_buffer)
    with open('investigate_fp_output.txt', 'w', encoding='utf-8') as f:
        f.write(output)
    
    print("Output written to investigate_fp_output.txt")
    print(output[:500])