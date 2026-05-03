import sys
sys.path.insert(0, '.')
from app import app, User, Scheme
from app.engine.eligibility import EligibilityEngine, get_canonical_field
from app.engine.questions import is_user_answerable
from collections import Counter

print("=" * 70)
print("VALIDATE FIX - RUN ON 500 SCHEMES")
print("=" * 70)

with app.app_context():
    user = User.query.filter_by(email='shreyas6504@gmail.com').first()
    profile = user.get_profile_dict()
    
    # Build strict profile
    all_schemes = Scheme.query.filter_by(is_active=True).all()
    
    all_condition_fields = set()
    for scheme in all_schemes:
        for cond in scheme.conditions:
            if is_user_answerable(cond.field):
                if getattr(cond, 'condition_type', None) == 'hard':
                    canonical = get_canonical_field(cond.field)
                    all_condition_fields.add(canonical)
    
    strict_profile = {}
    for key, value in profile.items():
        if value is not None:
            canonical = get_canonical_field(key)
            strict_profile[canonical] = value
    
    from app.engine.eligibility import simulate_answer
    for field in all_condition_fields:
        if field not in strict_profile or strict_profile[field] is None:
            strict_profile[field] = simulate_answer(field, profile)
    
    print(f"Profile keys: {len(strict_profile)}")
    print(f"Condition fields: {len(all_condition_fields)}")
    
    # Evaluate ALL schemes
    engine = EligibilityEngine()
    
    results = {'eligible': 0, 'possible': 0, 'ineligible': 0}
    hard_missing = Counter()
    missing_reasons = Counter()
    
    for scheme in all_schemes:
        eo = engine.evaluate(scheme, strict_profile)
        results[eo.result] += 1
        
        for cr in eo.condition_results:
            if is_user_answerable(cr.field):
                ct = getattr(cr, 'condition_type', 'soft')
                if ct == 'hard':
                    status = str(cr.status).strip().lower() if cr.status else 'missing'
                    if status in ['missing', 'unknown', 'none', '']:
                        hard_missing[cr.field] += 1
                        missing_reasons[status] += 1
    
    print(f"\n=== RESULTS ===")
    print(f"ELIGIBLE:   {results['eligible']}")
    print(f"POSSIBLE:   {results['possible']}")
    print(f"INELIGIBLE: {results['ineligible']}")
    print(f"TOTAL:      {sum(results.values())}")
    
    if hard_missing:
        print(f"\n❌ Still have {sum(hard_missing.values())} missing hard conditions")
        for f, c in hard_missing.most_common(15):
            print(f"  {f}: {c}")
        
        print(f"\n=== MISSING STATUS BREAKDOWN ===")
        for status, count in missing_reasons.most_common():
            print(f"  {status}: {count}")
    else:
        print(f"\n✅ SUCCESS: ZERO missing hard conditions!")

print("=" * 70)