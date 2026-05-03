import sys
sys.path.insert(0, '.')
from app import app, User, Scheme
from app.engine.eligibility import EligibilityEngine
from app.engine.context import ContextualReasoner
from app.engine.questions import is_user_answerable
from app.engine_compat import get_orchestrator

# Test profile
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

def evaluate_schemes(profile, use_prefilter=False, user_obj=None):
    with app.app_context():
        engine = EligibilityEngine()
        ctx = ContextualReasoner()
        
        if use_prefilter and user_obj:
            all_schemes = Scheme.query.filter_by(is_active=True).all()
            candidates = get_orchestrator(app.config).prefilter(user_obj, all_schemes)
        else:
            candidates = Scheme.query.filter_by(is_active=True).all()
        
        results = {'eligible': 0, 'possible': 0, 'ineligible': 0}
        false_eligible = 0
        scheme_details = []
        
        for scheme in candidates:
            eo = engine.evaluate(scheme, profile, ctx.score(scheme, profile))
            results[eo.result] += 1
            
            # Check false eligible
            is_false_eligible = False
            if eo.result == 'eligible':
                for r in eo.condition_results:
                    if is_user_answerable(r.field):
                        ct = getattr(r, 'condition_type', 'soft')
                        if ct == 'hard':
                            status = str(r.status).strip().lower() if r.status else 'missing'
                            if status in ['fail', 'false', 'missing', 'unknown', 'none', '']:
                                is_false_eligible = True
                                break
                if is_false_eligible:
                    false_eligible += 1
            
            scheme_details.append({
                'name': scheme.name,
                'id': scheme.id,
                'result': eo.result,
                'confidence': eo.confidence,
                'missing_fields': eo.missing_fields,
                'false_eligible': is_false_eligible
            })
        
        return results, false_eligible, scheme_details

print("=" * 80)
print("SCHEME ELIGIBILITY COMPARISON TABLE")
print("=" * 80)
print()

# Test user results
print(">>> Evaluating with TEST USER PROFILE...")
test_results, test_false, test_details = evaluate_schemes(test_profile)
print(f"Test User Results: ELIGIBLE={test_results['eligible']}, POSSIBLE={test_results['possible']}, INELIGIBLE={test_results['ineligible']}, FALSE_ELIGIBLE={test_false}")
print()

# Original user results
print(">>> Evaluating with ORIGINAL USER (shreyas6504@gmail.com)...")
with app.app_context():
    user = User.query.filter_by(email='shreyas6504@gmail.com').first()
    if user:
        profile = user.get_profile_dict()
        print(f"Original user profile: {list(profile.keys())[:10]}...")
        orig_results, orig_false, orig_details = evaluate_schemes(profile, use_prefilter=True, user_obj=user)
        print(f"Original User Results: ELIGIBLE={orig_results['eligible']}, POSSIBLE={orig_results['possible']}, INELIGIBLE={orig_results['ineligible']}, FALSE_ELIGIBLE={orig_false}")
    else:
        print("ERROR: User not found!")
        orig_results = {'eligible': 0, 'possible': 0, 'ineligible': 0}
        orig_false = 0

print()
print("=" * 80)
print("COMPARISON SUMMARY")
print("=" * 80)
print(f"{'Metric':<25} {'Original User':<15} {'Test User':<15}")
print("-" * 60)
print(f"{'ELIGIBLE':<25} {orig_results['eligible']:<15} {test_results['eligible']:<15}")
print(f"{'POSSIBLE':<25} {orig_results['possible']:<15} {test_results['possible']:<15}")
print(f"{'INELIGIBLE':<25} {orig_results['ineligible']:<15} {test_results['ineligible']:<15}")
print(f"{'FALSE ELIGIBLE':<25} {orig_false:<15} {test_false:<15}")
print("=" * 60)

# Show some schemes that differ
print()
print("=" * 80)
print("SAMPLE SCHEMES WITH DIFFERENT RESULTS")
print("=" * 80)

# Create lookup dicts
test_lookup = {s['id']: s for s in test_details}
orig_lookup = {s['id']: s for s in orig_details if orig_results != {'eligible': 0, 'possible': 0, 'ineligible': 0}}

differ_count = 0
for s in test_details:
    sid = s['id']
    if sid in orig_lookup:
        if s['result'] != orig_lookup[sid]['result']:
            differ_count += 1
            if differ_count <= 20:
                print(f"\n{s['name'][:60]}")
                print(f"  Original: {orig_lookup[sid]['result'].upper()} (conf: {orig_lookup[sid]['confidence']})")
                print(f"  Test User: {s['result'].upper()} (conf: {s['confidence']})")
                if s['missing_fields']:
                    print(f"  Test Missing: {s['missing_fields'][:5]}")

print(f"\n... Total schemes with different results: {differ_count}")