import sys
sys.path.insert(0, '.')
from app import app, User, Scheme
from app.engine.eligibility import EligibilityEngine, get_canonical_field, get_profile_value, evaluate_single
from app.engine.questions import is_user_answerable

print("=" * 100)
print("INVESTIGATING FALSE ELIGIBLE - WHY ARE THEY ELIGIBLE WITH HARD FAILS?")
print("=" * 100)

with app.app_context():
    user = User.query.filter_by(email='shreyas6504@gmail.com').first()
    profile = user.get_profile_dict()
    
    all_schemes = Scheme.query.filter_by(is_active=True).all()
    
    # Build strict profile
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
    
    engine = EligibilityEngine()
    
    # Find a false eligible example and investigate
    false_eligible_examples = []
    
    for scheme in all_schemes:
        eo = engine.evaluate(scheme, strict_profile)
        conditions = list(scheme.condition_rows)
        
        hard_fails = []
        for cond in conditions:
            cond_type = getattr(cond, 'condition_type', 'soft')
            cr = evaluate_single(cond, strict_profile)
            if cond_type == 'hard' and cr.status == 'fail':
                hard_fails.append((cond.field, cr.reason))
        
        if eo.result == 'eligible' and len(hard_fails) > 0:
            false_eligible_examples.append((scheme, eo, hard_fails))
            if len(false_eligible_examples) >= 3:
                break
    
    # Print detailed investigation
    for scheme, eo, hard_fails in false_eligible_examples:
        print(f"\n{'='*100}")
        print(f"SCHEME: {scheme.name[:80]}")
        print(f"FINAL RESULT: {eo.result}")
        print(f"HARD FAILS: {len(hard_fails)}")
        
        print(f"\n--- CONDITIONS ---")
        for cond in conditions:
            cond_type = getattr(cond, 'condition_type', 'soft')
            cr = evaluate_single(cond, strict_profile)
            status = cr.status.upper()
            print(f"  {cond.field:<40} | {cond_type:<6} | {status}")
        
        print(f"\n--- FAILING HARD CONDITIONS ---")
        for field, reason in hard_fails:
            print(f"  {field}: {reason[:60] if reason else 'N/A'}")
        
        print(f"\n--- ELIGIBILITY OUTPUT ---")
        print(f"  result: {eo.result}")
        print(f"  confidence: {eo.confidence}")
        print(f"  hard_score: {eo.hard_score}")
        print(f"  soft_score: {eo.soft_score}")
        print(f"  blocking_field: {eo.blocking_field}")
        print(f"  blocking_reason: {eo.blocking_reason[:60] if eo.blocking_reason else 'None'}")
        print(f"  missing_fields: {eo.missing_fields}")

print("\n" + "=" * 100)