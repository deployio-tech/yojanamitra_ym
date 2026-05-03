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

def resolve_with_iterations(engine, scheme, base_profile, max_iter=2):
    profile = dict(base_profile)
    for _ in range(max_iter):
        eo = engine.evaluate(scheme, profile)
        hard_missing = [get_canonical_field(f) for f in eo.missing_fields if is_user_answerable(f)]
        if not hard_missing:
            return eo
        # Simulate answers for missing fields
        for q in eo.missing_fields[:3]:
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
print("FULL SCHEME EVALUATION WITH RESOLUTION LOOP")
print("=" * 70)

with app.app_context():
    dummy_user = type('Dummy', (), {'id': 999, 'get_profile_dict': lambda self: test_profile})()
    
    all_schemes = Scheme.query.filter_by(is_active=True).all()
    candidates = get_orchestrator(app.config).prefilter(dummy_user, all_schemes)
    
    total_schemes = len(candidates)
    print(f"\n>>> TOTAL SCHEMES: {total_schemes}")
    
    engine = EligibilityEngine()
    
    results = {'eligible': 0, 'possible': 0, 'ineligible': 0}
    false_eligible = 0
    processed = 0
    
    print(f"\n>>> STARTING RESOLUTION EVALUATION...")
    start_time = time.time()
    
    for scheme in candidates:
        try:
            eo = resolve_with_iterations(engine, scheme, test_profile, max_iter=2)
            results[eo.result] += 1
            
            # Check false eligible
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
    print("FINAL COUNTS")
    print("=" * 70)
    print(f"ELIGIBLE:       {results['eligible']}")
    print(f"POSSIBLE:       {results['possible']}")
    print(f"INELIGIBLE:     {results['ineligible']}")
    print(f"TOTAL:          {results['eligible'] + results['possible'] + results['ineligible']}")
    print(f"FALSE ELIGIBLE: {false_eligible}")
    print("=" * 70)