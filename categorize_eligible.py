import sys
sys.path.insert(0, '.')
from app import app, Scheme
from app.engine.eligibility import EligibilityEngine
from app.engine.context import ContextualReasoner
from app.engine.questions import is_user_answerable

test_profile = {
    'age': 21,
    'state': 'Karnataka',
    'gender': 'male',
    'category': 'obc',
    'occupation': 'student',
    'annual_income': 200000,
    'education_level': 'graduation (ug)',
    'residence_area_type': 'rural',
    'has_bank_account': True,
    'is_student': True,
    'is_bpl': True,
    'is_disabled': False,
    'is_senior_citizen': False,
}

with app.app_context():
    engine = EligibilityEngine()
    ctx = ContextualReasoner()
    
    all_schemes = Scheme.query.filter_by(is_active=True).all()
    
    categories = {
        'no_user_hard_conditions': [],  # ELIGIBLE because no hard user conditions
        'all_hard_pass': [],             # ELIGIBLE - all hard user pass
        'has_hard_missing': [],          # POSSIBLE - has missing
        'has_hard_fail': [],             # INELIGIBLE - has fail
    }
    
    for scheme in all_schemes:
        eo = engine.evaluate(scheme, test_profile, ctx.score(scheme, test_profile))
        
        # Categorize
        has_hard_fail = False
        has_hard_missing = False
        has_hard_conditions = False
        
        for r in eo.condition_results:
            if is_user_answerable(r.field):
                ct = getattr(r, 'condition_type', 'soft')
                if ct == 'hard':
                    has_hard_conditions = True
                    status = str(r.status).strip().lower() if r.status else 'missing'
                    if status in ['fail', 'false']:
                        has_hard_fail = True
                    if status in ['missing', 'unknown', 'none', '']:
                        has_hard_missing = True
        
        if eo.result == 'eligible':
            if not has_hard_conditions:
                categories['no_user_hard_conditions'].append(scheme.name)
            else:
                categories['all_hard_pass'].append(scheme.name)
        elif eo.result == 'possible':
            categories['has_hard_missing'].append(scheme.name)
        elif eo.result == 'ineligible':
            categories['has_hard_fail'].append(scheme.name)
    
    print('=== WHY SCHEMES ARE ELIGIBLE ===')
    print(f'\n1. No user HARD conditions at all: {len(categories["no_user_hard_conditions"])} schemes')
    for name in categories['no_user_hard_conditions'][:5]:
        print(f'   - {name}')
    
    print(f'\n2. All hard user conditions PASS: {len(categories["all_hard_pass"])} schemes')
    for name in categories['all_hard_pass'][:5]:
        print(f'   - {name}')
    
    print(f'\n3. Has hard user MISSING (should be POSSIBLE): {len(categories["has_hard_missing"])}')
    print(f'\n4. Has hard user FAIL (should be INELIGIBLE): {len(categories["has_hard_fail"])}')