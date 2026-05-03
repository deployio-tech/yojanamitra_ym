import sys
sys.path.insert(0, '.')
from app import app, User, Scheme
from app.engine.eligibility import EligibilityEngine
from app.engine.context import ContextualReasoner
from app.engine.questions import is_user_answerable
from app.engine_compat import get_orchestrator

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

def get_results(profile, use_prefilter=False, user_obj=None):
    with app.app_context():
        engine = EligibilityEngine()
        ctx = ContextualReasoner()
        
        if use_prefilter and user_obj:
            all_schemes = Scheme.query.filter_by(is_active=True).all()
            candidates = get_orchestrator(app.config).prefilter(user_obj, all_schemes)
        else:
            all_schemes = Scheme.query.filter_by(is_active=True).all()
            candidates = all_schemes
        
        results = {'eligible': 0, 'possible': 0, 'ineligible': 0}
        false_eligible = 0
        
        for scheme in candidates:
            eo = engine.evaluate(scheme, profile, ctx.score(scheme, profile))
            results[eo.result] += 1
            
            if eo.result == 'eligible':
                has_issue = False
                for r in eo.condition_results:
                    if is_user_answerable(r.field):
                        ct = getattr(r, 'condition_type', 'soft')
                        if ct == 'hard':
                            status = str(r.status).strip().lower() if r.status else 'missing'
                            if status in ['fail', 'false', 'missing', 'unknown', 'none', '']:
                                has_issue = True
                                break
                if has_issue:
                    false_eligible += 1
        
        return results, false_eligible

# Test user with prefilter
print('=== TEST USER (with prefilter) ===')
test_results, test_false = get_results(test_profile, use_prefilter=True)
print(f'ELIGIBLE: {test_results["eligible"]}')
print(f'POSSIBLE: {test_results["possible"]}')
print(f'INELIGIBLE: {test_results["ineligible"]}')
print(f'FALSE ELIGIBLE: {test_false}')

# Previous user
print('\n=== PREVIOUS USER (shreyas6504@gmail.com) ===')
with app.app_context():
    user = User.query.filter_by(email='shreyas6504@gmail.com').first()
    profile = user.get_profile_dict()
    prev_results, prev_false = get_results(profile, use_prefilter=True, user_obj=user)
    print(f'ELIGIBLE: {prev_results["eligible"]}')
    print(f'POSSIBLE: {prev_results["possible"]}')
    print(f'INELIGIBLE: {prev_results["ineligible"]}')
    print(f'FALSE ELIGIBLE: {prev_false}')

# Comparison table
print('\n' + '='*60)
print('COMPARISON TABLE')
print('='*60)
print(f'{"Metric":<25} {"Previous":<15} {"Test User":<15}')
print('-'*60)
print(f'{"ELIGIBLE":<25} {prev_results["eligible"]:<15} {test_results["eligible"]:<15}')
print(f'{"POSSIBLE":<25} {prev_results["possible"]:<15} {test_results["possible"]:<15}')
print(f'{"INELIGIBLE":<25} {prev_results["ineligible"]:<15} {test_results["ineligible"]:<15}')
print(f'{"FALSE ELIGIBLE":<25} {prev_false:<15} {test_false:<15}')
print('='*60)