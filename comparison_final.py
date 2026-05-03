import sys
sys.path.insert(0, '.')
from app import app, User, Scheme
from app.engine.eligibility import EligibilityEngine, get_canonical_field, get_profile_value, evaluate_single
from app.engine.questions import is_user_answerable
from app.engine_compat import get_orchestrator
import re

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

def resolve_with_iterations(engine, scheme, base_profile, max_iter=2):
    profile = dict(base_profile)
    for _ in range(max_iter):
        eo = engine.evaluate(scheme, profile)
        hard_missing = [get_canonical_field(f) for f in eo.missing_fields if is_user_answerable(f)]
        if not hard_missing:
            return eo
        for q in eo.missing_fields[:3]:
            canonical = get_canonical_field(q)
            if canonical not in profile:
                profile[canonical] = simulate_answer(canonical, profile)
    return eo

def run_audit(profile, user_obj=None):
    with app.app_context():
        engine = EligibilityEngine()
        
        if user_obj:
            all_schemes = Scheme.query.filter_by(is_active=True).all()
            candidates = get_orchestrator(app.config).prefilter(user_obj, all_schemes)
        else:
            candidates = Scheme.query.filter_by(is_active=True).all()
        
        results = {'eligible': 0, 'possible': 0, 'ineligible': 0}
        
        for scheme in candidates:
            eo = resolve_with_iterations(engine, scheme, profile, max_iter=2)
            results[eo.result] += 1
        
        return results

# Test profile
test_profile = {
    'age': 21, 'state': 'Karnataka', 'gender': 'male', 'category': 'obc',
    'occupation': 'student', 'annual_income': 200000, 'education_level': 'graduation (ug)',
    'residence_area_type': 'rural', 'has_bank_account': True, 'is_student': True,
    'is_bpl': True, 'is_disabled': False, 'is_senior_citizen': False,
}

print("=" * 70)
print("COMPARISON TABLE - RESOLUTION AUDIT")
print("=" * 70)

# Run with test user
print("\n>>> Running with Test User Profile...")
test_results = run_audit(test_profile)
print(f"Test User: ELIGIBLE={test_results['eligible']}, POSSIBLE={test_results['possible']}, INELIGIBLE={test_results['ineligible']}")

# Run with original user
print("\n>>> Running with Original User (shreyas6504@gmail.com)...")
with app.app_context():
    user = User.query.filter_by(email='shreyas6504@gmail.com').first()
    profile = user.get_profile_dict()
    orig_results = run_audit(profile, user_obj=user)
    print(f"Original User: ELIGIBLE={orig_results['eligible']}, POSSIBLE={orig_results['possible']}, INELIGIBLE={orig_results['ineligible']}")

print()
print("=" * 70)
print("FINAL COMPARISON TABLE")
print("=" * 70)
print(f"{'Metric':<25} {'Original User':<15} {'Test User':<15}")
print("-" * 60)
print(f"{'ELIGIBLE':<25} {orig_results['eligible']:<15} {test_results['eligible']:<15}")
print(f"{'POSSIBLE':<25} {orig_results['possible']:<15} {test_results['possible']:<15}")
print(f"{'INELIGIBLE':<25} {orig_results['ineligible']:<15} {test_results['ineligible']:<15}")
print(f"{'TOTAL':<25} {orig_results['eligible']+orig_results['possible']+orig_results['ineligible']:<15} {test_results['eligible']+test_results['possible']+test_results['ineligible']:<15}")
print("=" * 70)

# Save to comparison file
with open('full_comparison_results.txt', 'w', encoding='utf-8') as f:
    f.write("=" * 70 + "\n")
    f.write("COMPARISON TABLE - RESOLUTION AUDIT\n")
    f.write("=" * 70 + "\n\n")
    f.write(f"Test User Profile: Age=21, Karnataka, Student, OBC, 2L income\n")
    f.write(f"Original User: shreyas6504@gmail.com\n\n")
    f.write(f"{'Metric':<25} {'Original User':<15} {'Test User':<15}\n")
    f.write("-" * 60 + "\n")
    f.write(f"{'ELIGIBLE':<25} {orig_results['eligible']:<15} {test_results['eligible']:<15}\n")
    f.write(f"{'POSSIBLE':<25} {orig_results['possible']:<15} {test_results['possible']:<15}\n")
    f.write(f"{'INELIGIBLE':<25} {orig_results['ineligible']:<15} {test_results['ineligible']:<15}\n")
    f.write(f"{'TOTAL':<25} {orig_results['eligible']+orig_results['possible']+orig_results['ineligible']:<15} {test_results['eligible']+test_results['possible']+test_results['ineligible']:<15}\n")
    f.write("=" * 70 + "\n")

print("\nSaved comparison to: full_comparison_results.txt")