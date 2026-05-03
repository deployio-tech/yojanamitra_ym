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

def resolve_fast(engine, qengine, scheme, base_profile, max_iter=3):
    profile = dict(base_profile)
    for _ in range(max_iter):
        eo = engine.evaluate(scheme, profile)
        hard_missing = [get_canonical_field(f) for f in eo.missing_fields if is_user_answerable(f)]
        if not hard_missing:
            return eo
        for q in eo.missing_fields[:5]:  # Limit questions per iteration
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

print("Running fast resolution audit...", flush=True)

with app.app_context():
    engine = EligibilityEngine()
    qengine = QuestionEngine()
    schemes = Scheme.query.filter_by(is_active=True).all()
    
    results = {'eligible': 0, 'possible': 0, 'ineligible': 0}
    false_eligible = 0
    
    for i, scheme in enumerate(schemes):
        eo = resolve_fast(engine, qengine, scheme, test_profile, max_iter=3)
        results[eo.result] += 1
        
        if eo.result == 'eligible':
            for r in eo.condition_results:
                if is_user_answerable(r.field):
                    ct = getattr(r, 'condition_type', 'soft')
                    if ct == 'hard':
                        status = str(r.status).strip().lower() if r.status else 'missing'
                        if status in ['fail', 'false', 'missing', 'unknown', 'none', '']:
                            false_eligible += 1
                            break
        
        if (i + 1) % 1000 == 0:
            print(f"{i+1}/...", flush=True)

print()
print("=" * 50)
print(f"ELIGIBLE:    {results['eligible']}")
print(f"POSSIBLE:    {results['possible']}")
print(f"INELIGIBLE:  {results['ineligible']}")
print(f"FALSE ELIGIBLE: {false_eligible}")
print("=" * 50)

# Generate compact output file
with app.app_context():
    schemes = Scheme.query.filter_by(is_active=True).all()
    with open('full_condition_comparison_with_resolution.txt', 'w', encoding='utf-8') as f:
        f.write("ID|NAME|RESULT|CONFIDENCE\n")
        for scheme in schemes:
            eo = resolve_fast(engine, qengine, scheme, test_profile, max_iter=3)
            f.write(f"{scheme.id}|{scheme.name[:50]}|{eo.result.upper()}|{eo.confidence}\n")

print("Saved to full_condition_comparison_with_resolution.txt")