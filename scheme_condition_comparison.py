import sys
sys.path.insert(0, '.')
from app import app, User, Scheme
from app.engine.eligibility import EligibilityEngine, get_canonical_field, get_profile_value, evaluate_single, normalize_condition_value
from app.engine.questions import is_user_answerable
import json

print("=" * 80)
print("DETAILED CONDITION-TO-USER COMPARISON")
print("User: shreyas6504@gmail.com")
print("=" * 80)

with app.app_context():
    user = User.query.filter_by(email='shreyas6504@gmail.com').first()
    profile = user.get_profile_dict()
    
    # Show user profile summary
    print("\n=== USER PROFILE ===")
    for key, value in sorted(profile.items()):
        if value is not None:
            print(f"  {key}: {repr(value)[:50]}")
    
    # Get all active schemes
    all_schemes = Scheme.query.filter_by(is_active=True).all()
    
    engine = EligibilityEngine()
    
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
    
    # Evaluate ALL schemes
    print(f"\n=== EVALUATING {len(all_schemes)} SCHEMES ===\n")
    
    eligible_schemes = []
    ineligible_schemes = []
    
    for scheme in all_schemes:
        eo = engine.evaluate(scheme, strict_profile)
        
        if eo.result == 'eligible':
            eligible_schemes.append((scheme, eo))
        else:
            ineligible_schemes.append((scheme, eo))
    
    # Show ELIGIBLE schemes with condition details
    print("\n" + "=" * 80)
    print(f"✅ ELIGIBLE SCHEMES ({len(eligible_schemes)})")
    print("=" * 80)
    
    for scheme, eo in eligible_schemes[:20]:  # Show first 20
        print(f"\n--- {scheme.name[:60]} ---")
        print(f"Result: {eo.result}")
        print(f"Confidence: {eo.confidence:.2f}")
        
        # Show condition breakdown
        hard_pass = 0
        hard_fail = 0
        for cr in eo.condition_results:
            if is_user_answerable(cr.field):
                ct = getattr(cr, 'condition_type', 'soft')
                if ct == 'hard':
                    if cr.status == 'pass':
                        hard_pass += 1
                    else:
                        hard_fail += 1
        
        print(f"Hard Conditions: {hard_pass} pass, {hard_fail} fail")
    
    if len(eligible_schemes) > 20:
        print(f"\n... and {len(eligible_schemes) - 20} more eligible schemes")
    
    # Show INELIGIBLE schemes with failure reasons
    print("\n" + "=" * 80)
    print(f"❌ INELIGIBLE SCHEMES ({len(ineligible_schemes)})")
    print("=" * 80)
    
    # Group ineligible by first blocking reason
    from collections import Counter
    blocking_reasons = Counter()
    first_blockers = []
    
    for scheme, eo in ineligible_schemes:
        # Find first failing hard condition
        for cr in eo.condition_results:
            if is_user_answerable(cr.field):
                ct = getattr(cr, 'condition_type', 'soft')
                if ct == 'hard' and cr.status == 'fail':
                    first_blockers.append((scheme.name[:50], cr.field, cr.reason))
                    blocking_reasons[cr.field] += 1
                    break
    
    print("\n=== TOP FAILING CONDITIONS ===")
    for field, count in blocking_reasons.most_common(15):
        print(f"  {field}: {count} schemes")
    
    print("\n=== SAMPLE FAILURES (first 10) ===")
    for name, field, reason in first_blockers[:10]:
        print(f"\n  Scheme: {name}")
        print(f"  Field: {field}")
        print(f"  Reason: {reason[:80] if reason else 'N/A'}")
    
    # Final summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"TOTAL SCHEMES: {len(all_schemes)}")
    print(f"ELIGIBLE:      {len(eligible_schemes)}")
    print(f"INELIGIBLE:    {len(ineligible_schemes)}")
    print(f"POSSIBLE:       0")
    print("=" * 80)

print("\n✅ Comparison complete!")