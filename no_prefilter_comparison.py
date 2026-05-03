import sys
sys.path.insert(0, '.')
from app import app, User, Scheme
from app.engine.eligibility import EligibilityEngine, get_canonical_field
from app.engine.questions import QuestionEngine, is_user_answerable
import time

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

def resolve_with_iterations(engine, qengine, scheme, base_profile, max_iter=2):
    # CRITICAL: Use copy per scheme to prevent cross-contamination
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

def run_audit(profile):
    with app.app_context():
        engine = EligibilityEngine()
        qengine = QuestionEngine()
        
        # CRITICAL: NO PREFILTER - use ALL active schemes directly
        all_schemes = Scheme.query.filter_by(is_active=True).all()
        
        print(f"TOTAL SCHEMES FROM DB: {len(all_schemes)}")
        
        results = []
        processed = 0
        
        for scheme in all_schemes:
            try:
                # Use copy of profile per scheme (isolation)
                eo = resolve_with_iterations(engine, qengine, scheme, profile, max_iter=2)
                results.append(eo)
                processed += 1
            except Exception as e:
                # On error, count as ineligible
                from app.engine.eligibility import EligibilityOutput
                eo = EligibilityOutput(
                    result="ineligible",
                    confidence=0.0,
                    hard_score=0.0,
                    soft_score=0.0,
                    context_score=0.0,
                    coverage_penalty=0.0,
                )
                results.append(eo)
                processed += 1
        
        print(f"TOTAL RESULTS GENERATED: {len(results)}")
        
        # Calculate counts
        eligible = sum(1 for r in results if r.result == "eligible")
        possible = sum(1 for r in results if r.result == "possible")
        ineligible = sum(1 for r in results if r.result == "ineligible")
        
        print(f"ELIGIBLE: {eligible}")
        print(f"POSSIBLE: {possible}")
        print(f"INELIGIBLE: {ineligible}")
        print(f"SUM: {eligible + possible + ineligible}")
        
        return {
            'eligible': eligible,
            'possible': possible,
            'ineligible': ineligible
        }

# Test profile
test_profile = {
    'age': 21, 'state': 'Karnataka', 'gender': 'male', 'category': 'obc',
    'occupation': 'student', 'annual_income': 200000, 'education_level': 'graduation (ug)',
    'residence_area_type': 'rural', 'has_bank_account': True, 'is_student': True,
    'is_bpl': True, 'is_disabled': False, 'is_senior_citizen': False,
}

print("=" * 70)
print("FULL COMPARISON - NO PREFILTER - ALL SCHEMES EVALUATED")
print("=" * 70)

# Run with test user
print("\n>>> TEST USER PROFILE")
print("-" * 40)
start = time.time()
test_results = run_audit(test_profile)
print(f"Time: {time.time() - start:.1f}s")

# Run with original user
print("\n>>> ORIGINAL USER (shreyas6504@gmail.com)")
print("-" * 40)
with app.app_context():
    user = User.query.filter_by(email='shreyas6504@gmail.com').first()
    profile = user.get_profile_dict()
    start = time.time()
    orig_results = run_audit(profile)
    print(f"Time: {time.time() - start:.1f}s")

# Final comparison
print()
print("=" * 70)
print("FINAL COMPARISON TABLE (NO PREFILTER)")
print("=" * 70)
print(f"{'Metric':<25} {'Original User':<15} {'Test User':<15}")
print("-" * 60)
print(f"{'ELIGIBLE':<25} {orig_results['eligible']:<15} {test_results['eligible']:<15}")
print(f"{'POSSIBLE':<25} {orig_results['possible']:<15} {test_results['possible']:<15}")
print(f"{'INELIGIBLE':<25} {orig_results['ineligible']:<15} {test_results['ineligible']:<15}")
total_orig = orig_results['eligible'] + orig_results['possible'] + orig_results['ineligible']
total_test = test_results['eligible'] + test_results['possible'] + test_results['ineligible']
print(f"{'TOTAL':<25} {total_orig:<15} {total_test:<15}")
print("=" * 70)

# Verify success condition
print()
print("VALIDATION:")
print(f"  Original User TOTAL = 4212? {'✅ YES' if total_orig == 4212 else '❌ NO'}")
print(f"  Test User TOTAL = 4212? {'✅ YES' if total_test == 4212 else '❌ NO'}")