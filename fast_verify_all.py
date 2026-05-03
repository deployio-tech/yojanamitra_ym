import sys
sys.path.insert(0, '.')
from app import app, Scheme
from app.engine.eligibility import EligibilityEngine, get_canonical_field
from app.engine.questions import QuestionEngine, is_user_answerable
from app.engine_compat import get_orchestrator
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

# Fast resolution - reduced iterations
def resolve_fast(engine, scheme, base_profile, max_iter=1):
    profile = dict(base_profile)
    for _ in range(max_iter):
        eo = engine.evaluate(scheme, profile)
        if not eo.missing_fields:
            return eo
        for q in eo.missing_fields[:2]:
            canonical = get_canonical_field(q)
            if canonical not in profile:
                profile[canonical] = simulate_answer(canonical, profile)
    return eo

test_profile = {
    'age': 21, 'state': 'Karnataka', 'gender': 'male', 'category': 'obc',
    'occupation': 'student', 'annual_income': 200000, 'education_level': 'graduation (ug)',
    'residence_area_type': 'rural', 'has_bank_account': True, 'is_student': True,
    'is_bpl': True, 'is_disabled': False, 'is_senior_citizen': False,
}

print("=" * 70)
print("FULL SCHEME EVALUATION - OPTIMIZED")
print("=" * 70)

with app.app_context():
    # Create dummy user for prefilter
    dummy_user = type('Dummy', (), {'id': 999, 'get_profile_dict': lambda self: test_profile})()
    
    # Get active schemes via prefilter
    all_schemes = Scheme.query.filter_by(is_active=True).all()
    candidates = get_orchestrator(app.config).prefilter(dummy_user, all_schemes)
    
    total_schemes = len(candidates)
    print(f"\n>>> TOTAL SCHEMES (active, prefiltered): {total_schemes}")
    
    engine = EligibilityEngine()
    
    results = {'eligible': 0, 'possible': 0, 'ineligible': 0}
    processed = 0
    
    print(f"\n>>> STARTING EVALUATION...")
    start_time = time.time()
    
    for scheme in candidates:
        try:
            eo = resolve_fast(engine, scheme, test_profile, max_iter=1)
            results[eo.result] += 1
            processed += 1
            
            if processed % 500 == 0:
                print(f"  Processed: {processed}/{total_schemes}")
                
        except Exception as e:
            results['ineligible'] += 1
            processed += 1
    
    elapsed = time.time() - start_time
    
    print(f"\n>>> COMPLETED: {processed}/{total_schemes} in {elapsed:.1f}s")
    
    print()
    print("=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    print(f"ELIGIBLE:    {results['eligible']}")
    print(f"POSSIBLE:    {results['possible']}")
    print(f"INELIGIBLE:  {results['ineligible']}")
    print(f"TOTAL:       {results['eligible'] + results['possible'] + results['ineligible']}")
    print("=" * 70)