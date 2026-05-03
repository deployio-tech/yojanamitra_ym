import sqlite3
import json
import sys

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

def log(msg):
    with open('debug_output.txt', 'a', encoding='utf-8') as f:
        f.write(str(msg) + '\n')

log("=== Starting investigation ===")

# Load conditions
log("Loading conditions...")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

placeholders = ','.join(['?'] * len(SCHEME_IDS))
cursor.execute(f'''
    SELECT scheme_id, extracted_json, confidence 
    FROM gemini_prefill 
    WHERE scheme_id IN ({placeholders}) AND status = "success"
''', SCHEME_IDS)
cond_rows = cursor.fetchall()
log(f"Found {len(cond_rows)} conditions")

conditions = {}
for row in cond_rows:
    conditions[row[0]] = json.loads(row[1])

# Load schemes
cursor.execute(f'''
    SELECT id, name, eligibility, benefits 
    FROM scheme 
    WHERE id IN ({placeholders})
''', SCHEME_IDS)
scheme_rows = cursor.fetchall()
log(f"Found {len(scheme_rows)} schemes")

schemes = {}
for row in scheme_rows:
    schemes[row[0]] = {
        'id': row[0],
        'name': row[1],
        'eligibility': row[2],
        'benefits': row[3]
    }

conn.close()

# Analyze each scheme
results = []

for scheme_id in SCHEME_IDS:
    log(f"\n=== Scheme {scheme_id} ===")
    
    scheme = schemes.get(scheme_id)
    if not scheme:
        log(f"  NOT FOUND in scheme table")
        continue
    
    log(f"  Name: {scheme['name'][:50]}")
    log(f"  Eligibility: {str(scheme['eligibility'])[:200]}...")
    
    cond = conditions.get(scheme_id)
    if not cond:
        log(f"  NO EXTRACTED CONDITIONS")
        continue
    
    log(f"  Extracted conditions: {json.dumps(cond, indent=2)[:500]}")
    
    # Check eligibility using extracted conditions
    issues = []
    
    # Gender check
    cond_gender = cond.get('gender')
    if cond_gender and str(cond_gender).lower() != 'any':
        if USER_PROFILE['gender'].lower() != str(cond_gender).lower():
            issues.append(f"Gender mismatch")
    
    # Age check
    min_age = cond.get('min_age')
    max_age = cond.get('max_age')
    if min_age and USER_PROFILE['age'] < min_age:
        issues.append(f"Age below min")
    if max_age and USER_PROFILE['age'] > max_age:
        issues.append(f"Age above max")
    
    # Income check
    max_income = cond.get('income_annual_max')
    if max_income and USER_PROFILE['annual_family_income'] > max_income:
        issues.append(f"Income exceeds max")
    
    # State check
    cond_state = cond.get('domicile_state')
    if cond_state and cond_state != []:
        if isinstance(cond_state, str):
            cond_state = [cond_state]
        if USER_PROFILE['state'].title() not in [s.title() for s in cond_state]:
            issues.append(f"State mismatch")
    
    # Caste check
    cond_caste = cond.get('caste_category')
    if cond_caste and cond_caste != []:
        if isinstance(cond_caste, str):
            cond_caste = [cond_caste]
        if USER_PROFILE['caste'].title() not in [c.title() for c in cond_caste]:
            issues.append(f"Caste mismatch")
    
    # Occupation check
    cond_occ = cond.get('occupation')
    if cond_occ and cond_occ != []:
        if isinstance(cond_occ, str):
            cond_occ = [cond_occ]
        if USER_PROFILE['occupation'].title() not in [o.title() for o in cond_occ]:
            issues.append(f"Occupation mismatch")
    
    # Education check
    min_edu = cond.get('min_education')
    if min_edu:
        edu_levels = {'none': 0, 'primary': 1, 'secondary': 2, 'higher_secondary': 3, 'graduate': 4, 'postgraduate': 5}
        user_edu = USER_PROFILE['highest_education_level'].lower()
        user_level = 4 if 'grad' in user_edu else 0
        min_level = edu_levels.get(str(min_edu).lower(), 0)
        if user_level < min_level:
            issues.append(f"Education below min")
    
    # Check for bank account requirement
    if cond.get('has_bank_account') is True:
        if USER_PROFILE.get('has_bank_account') is None:
            issues.append("Bank account required but unknown")
        elif USER_PROFILE.get('has_bank_account') is False:
            issues.append("Bank account required but user has None")
    
    log(f"  Classifier issues: {issues if issues else 'NONE - ELIGIBLE'}")
    
    # Check actual eligibility for false positive detection
    text_issues = []
    if scheme['eligibility']:
        text = scheme['eligibility'].lower()
        
        # State restrictions
        state_restrictions = ['karnataka', 'maharashtra', 'delhi', 'tamil nadu', 'kerala', 'gujarat', 'west bengal', 'rajasthan', 'punjab', 'haryana']
        for state in state_restrictions:
            if state in text and USER_PROFILE['state'].lower() != state:
                text_issues.append(f"State restriction: requires {state}")
                break
        
        # Women-only
        if ('women' in text or 'female' in text) and ('only' in text or 'exclusively' in text):
            if USER_PROFILE['gender'].lower() != 'female':
                text_issues.append("Women-only scheme")
        
        # Students specifically excluded
        if 'student' in text:
            if 'not eligible' in text or 'excluded' in text:
                if 'student' in text:
                    text_issues.append("Students excluded")
    
    log(f"  Text issues: {text_issues if text_issues else 'NONE'}")
    
    # Determine false positive
    is_fp = False
    fp_reason = ""
    
    if not issues:
        # Check if real eligibility has hidden restrictions
        if text_issues:
            is_fp = True
            fp_reason = "; ".join(text_issues)
            log(f"  FALSE POSITIVE: {fp_reason}")
        else:
            log(f"  TRUE POSITIVE")
    
    results.append({
        'scheme_id': scheme_id,
        'name': scheme['name'],
        'eligibility': scheme['eligibility'],
        'extracted_conditions': cond,
        'classifier_issues': issues,
        'text_issues': text_issues,
        'is_false_positive': is_fp,
        'fp_reason': fp_reason
    })

log("\n=== SUMMARY ===")
for r in results:
    log(f"Scheme {r['scheme_id']}: {r['name'][:40]}")
    if r['is_false_positive']:
        log(f"  FALSE POSITIVE - {r['fp_reason']}")
    elif not r['classifier_issues']:
        log(f"  TRUE POSITIVE")
    else:
        log(f"  INELIGIBLE")

log("=== Done ===")