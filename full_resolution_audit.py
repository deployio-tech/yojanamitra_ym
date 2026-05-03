import sys
sys.path.insert(0, '.')
from app import app, Scheme
from app.engine.eligibility import EligibilityEngine, get_canonical_field
from app.engine.context import ContextualReasoner
from app.engine.questions import QuestionEngine, is_user_answerable

# Controlled simulation function
def simulate_answer(field, profile):
    """Controlled default answers - not always True."""
    if field in ["citizenship"]:
        return True
    if field in ["bank_account"]:
        return True
    if field in ["consent"]:
        return True
    if field in profile and profile[field] is not None:
        return profile[field]
    return True  # fallback (optimistic but controlled)

# Resolution orchestrator with 3 micro-fixes
def resolve_scheme_fully(engine, qengine, scheme, base_profile, max_iter=5):
    """
    Orchestration layer for full resolution.
    GUARD: Uses COPY of profile to prevent mutation leakage.
    """
    # GUARD 1: Copy profile to prevent mutation
    profile = dict(base_profile)
    
    for _ in range(max_iter):
        eo = engine.evaluate(scheme, profile)
        
        # FIX 1: Use CANONICAL for missing extraction
        hard_missing = [
            get_canonical_field(f)
            for f in eo.missing_fields
            if is_user_answerable(f)
        ]
        
        if not hard_missing:
            return eo  # Fully resolved
        
        questions = qengine.select_questions([(scheme, eo)], profile)
        
        # FIX 2: Prevent infinite re-asking
        before = set(profile.keys())
        for q in questions:
            canonical = get_canonical_field(q.field)
            if canonical in profile:
                continue
            profile[canonical] = simulate_answer(canonical, profile)
        
        # FIX 3: Break if no new information
        after = set(profile.keys())
        if before == after:
            break
    
    return eo  # fallback after max iterations

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

print("=" * 80)
print("FULL RESOLUTION AUDIT")
print("=" * 80)

with app.app_context():
    engine = EligibilityEngine()
    qengine = QuestionEngine()
    ctx = ContextualReasoner()
    
    all_schemes = Scheme.query.filter_by(is_active=True).all()
    print(f"Total schemes: {len(all_schemes)}")
    
    results = {'eligible': 0, 'possible': 0, 'ineligible': 0}
    false_eligible = 0
    
    # GUARD 2: Reset profile per scheme
    for i, scheme in enumerate(all_schemes):
        # Use fresh copy for each scheme
        eo = resolve_scheme_fully(engine, qengine, scheme, test_profile, max_iter=5)
        
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
        
        if (i + 1) % 500 == 0:
            print(f"Processed {i + 1} schemes...")
    
    print()
    print("=" * 80)
    print("FINAL COUNTS")
    print("=" * 80)
    print(f"ELIGIBLE:    {results['eligible']}")
    print(f"POSSIBLE:    {results['possible']}")
    print(f"INELIGIBLE:  {results['ineligible']}")
    print(f"FALSE ELIGIBLE: {false_eligible}")
    print("=" * 80)