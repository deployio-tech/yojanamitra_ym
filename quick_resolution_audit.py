import sys
sys.path.insert(0, '.')
from app import app, Scheme
from app.engine.eligibility import EligibilityEngine, get_canonical_field
from app.engine.questions import QuestionEngine, is_user_answerable
import re

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

print("Running resolution audit...", flush=True)

with app.app_context():
    engine = EligibilityEngine()
    qengine = QuestionEngine()
    
    all_schemes = Scheme.query.filter_by(is_active=True).all()
    print(f"Total schemes: {len(all_schemes)}", flush=True)
    
    results = {'eligible': 0, 'possible': 0, 'ineligible': 0}
    false_eligible = 0
    
    output = []
    
    for i, scheme in enumerate(all_schemes):
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
        
        # Write to file incrementally
        output.append(f"RESULT: {eo.result.upper()} | {scheme.name} (ID: {scheme.id}) | CONF: {eo.confidence}")
        
        if (i + 1) % 500 == 0:
            print(f"Processed {i + 1} schemes...", flush=True)
    
    with open('full_condition_comparison_with_resolution.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    
    print()
    print("=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"ELIGIBLE: {results['eligible']}")
    print(f"POSSIBLE: {results['possible']}")
    print(f"INELIGIBLE: {results['ineligible']}")
    print(f"FALSE ELIGIBLE: {false_eligible}")
    print("=" * 60)
    print(f"Results saved to: full_condition_comparison_with_resolution.txt")