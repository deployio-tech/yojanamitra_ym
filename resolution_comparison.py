import sys
sys.path.insert(0, '.')
from app import app, User, Scheme
from app.engine.eligibility import EligibilityEngine, get_canonical_field
from app.engine.context import ContextualReasoner
from app.engine.questions import QuestionEngine, is_user_answerable
from app.engine_compat import get_orchestrator

# Controlled simulation function
def simulate_answer(field, profile):
    if field in ["citizenship"]:
        return True
    if field in ["bank_account"]:
        return True
    if field in ["consent"]:
        return True
    if field in profile and profile[field] is not None:
        return profile[field]
    return True

# Resolution orchestrator
def resolve_scheme_fully(engine, qengine, scheme, base_profile, max_iter=5):
    profile = dict(base_profile)
    for _ in range(max_iter):
        eo = engine.evaluate(scheme, profile)
        hard_missing = [
            get_canonical_field(f)
            for f in eo.missing_fields
            if is_user_answerable(f)
        ]
        if not hard_missing:
            return eo
        questions = qengine.select_questions([(scheme, eo)], profile)
        before = set(profile.keys())
        for q in questions:
            canonical = get_canonical_field(q.field)
            if canonical in profile:
                continue
            profile[canonical] = simulate_answer(canonical, profile)
        after = set(profile.keys())
        if before == after:
            break
    return eo

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

def run_audit(profile, use_prefilter=False, user_obj=None):
    with app.app_context():
        engine = EligibilityEngine()
        qengine = QuestionEngine()
        
        if use_prefilter and user_obj:
            all_schemes = Scheme.query.filter_by(is_active=True).all()
            candidates = get_orchestrator(app.config).prefilter(user_obj, all_schemes)
        else:
            candidates = Scheme.query.filter_by(is_active=True).all()
        
        results = {'eligible': 0, 'possible': 0, 'ineligible': 0}
        false_eligible = 0
        
        for scheme in candidates:
            eo = resolve_scheme_fully(engine, qengine, scheme, profile, max_iter=5)
            results[eo.result] += 1
            
            if eo.result == 'eligible':
                is_false = False
                for r in eo.condition_results:
                    if is_user_answerable(r.field):
                        ct = getattr(r, 'condition_type', 'soft')
                        if ct == 'hard':
                            status = str(r.status).strip().lower() if r.status else 'missing'
                            if status in ['fail', 'false', 'missing', 'unknown', 'none', '']:
                                is_false = True
                                break
                if is_false:
                    false_eligible += 1
        
        return results, false_eligible

print("=" * 80)
print("RESOLUTION AUDIT - COMPARISON")
print("=" * 80)

# Test user
print("\n>>> Running with TEST USER PROFILE...")
test_results, test_false = run_audit(test_profile)
print(f"Test User: ELIGIBLE={test_results['eligible']}, POSSIBLE={test_results['possible']}, INELIGIBLE={test_results['ineligible']}, FALSE_ELIGIBLE={test_false}")

# Original user
print("\n>>> Running with ORIGINAL USER (shreyas6504@gmail.com)...")
with app.app_context():
    user = User.query.filter_by(email='shreyas6504@gmail.com').first()
    profile = user.get_profile_dict()
    orig_results, orig_false = run_audit(profile, use_prefilter=True, user_obj=user)
    print(f"Original User: ELIGIBLE={orig_results['eligible']}, POSSIBLE={orig_results['possible']}, INELIGIBLE={orig_results['ineligible']}, FALSE_ELIGIBLE={orig_false}")

print()
print("=" * 80)
print("FINAL COMPARISON TABLE")
print("=" * 80)
print(f"{'Metric':<25} {'Original User':<15} {'Test User':<15}")
print("-" * 60)
print(f"{'ELIGIBLE':<25} {orig_results['eligible']:<15} {test_results['eligible']:<15}")
print(f"{'POSSIBLE':<25} {orig_results['possible']:<15} {test_results['possible']:<15}")
print(f"{'INELIGIBLE':<25} {orig_results['ineligible']:<15} {test_results['ineligible']:<15}")
print(f"{'FALSE ELIGIBLE':<25} {orig_false:<15} {test_false:<15}")
print("=" * 60)
print()
print("FINAL COUNTS:")
print(f"Original User: ELIGIBLE: {orig_results['eligible']} | POSSIBLE: {orig_results['possible']} | INELIGIBLE: {orig_results['ineligible']}")
print(f"Test User:      ELIGIBLE: {test_results['eligible']} | POSSIBLE: {test_results['possible']} | INELIGIBLE: {test_results['ineligible']}")