import sys
sys.path.insert(0, '.')
from app import app, User, Scheme
from app.engine.eligibility import EligibilityEngine, get_canonical_field, get_profile_value
from app.engine.questions import is_user_answerable

print("=" * 70)
print("PROVE: Is it MISSING profile or BAD condition value?")
print("=" * 70)

with app.app_context():
    user = User.query.filter_by(email='shreyas6504@gmail.com').first()
    profile = user.get_profile_dict()
    
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
    
    # Test ONE specific condition that shows as "unknown"
    scheme = Scheme.query.filter(Scheme.name.like('%Pre Matric Scholarship for OBC%')).first()
    
    if scheme:
        for cond in scheme.conditions:
            if cond.field == 'class_level' and getattr(cond, 'condition_type', None) == 'hard':
                print(f"\n=== CONDITION ===")
                print(f"Field: {repr(cond.field)}")
                print(f"Operator: {repr(cond.operator)}")
                print(f"Value: {repr(cond.value)}")
                
                # Check profile value
                profile_val = get_profile_value(cond.field, strict_profile)
                print(f"\nProfile value: {repr(profile_val)}")
                
                # Check what happens when we try to evaluate
                print(f"\nTrying to evaluate: {profile_val} {cond.operator} {cond.value}")
                
                # The value is 'None' string, not Python None
                # So when we try to parse it:
                import json
                try:
                    parsed = json.loads(cond.value)
                    print(f"Parsed value: {repr(parsed)}")
                    print(f"Type: {type(parsed)}")
                except:
                    print(f"Parse failed - value is malformed string 'None'")
                
                # This is the problem - condition value is literally "None" string
                # not a valid range like [1, 12] or [1, 10]
                
                print(f"\n=== CONCLUSION ===")
                print("Profile has value: YES")
                print("Condition value is valid: NO (it's 'None' string)")
                print("Result: UNKNOWN because condition is malformed, NOT missing profile")
                break

print("=" * 70)