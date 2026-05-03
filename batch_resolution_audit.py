import sys
sys.path.insert(0, '.')
from app import app, Scheme
from app.engine.eligibility import EligibilityEngine, get_canonical_field
from app.engine.questions import QuestionEngine, is_user_answerable

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

# BATCH PROCESSING - Write to file in chunks
BATCH_SIZE = 500

print("Starting batch resolution audit...", flush=True)

with app.app_context():
    engine = EligibilityEngine()
    qengine = QuestionEngine()
    
    all_schemes = Scheme.query.filter_by(is_active=True).all()
    total = len(all_schemes)
    print(f"Total schemes: {total}", flush=True)
    
    results = {'eligible': 0, 'possible': 0, 'ineligible': 0}
    false_eligible = 0
    
    # Open file once
    with open('full_condition_comparison_with_resolution.txt', 'w', encoding='utf-8') as f:
        for batch_start in range(0, total, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total)
            batch = all_schemes[batch_start:batch_end]
            
            for scheme in batch:
                eo = resolve_scheme_fully(engine, qengine, scheme, test_profile, max_iter=5)
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
                
                # Write summary line
                f.write(f"{scheme.id}|{scheme.name}|{eo.result.upper()}|{eo.confidence}\n")
            
            print(f"Processed {batch_end}/{total}...", flush=True)

print()
print("=" * 60)
print("FINAL RESULTS (Test User Profile)")
print("=" * 60)
print(f"ELIGIBLE:    {results['eligible']}")
print(f"POSSIBLE:    {results['possible']}")
print(f"INELIGIBLE:  {results['ineligible']}")
print(f"FALSE ELIGIBLE: {false_eligible}")
print("=" * 60)
print(f"Full table saved to: full_condition_comparison_with_resolution.txt")