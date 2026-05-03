import sys
sys.path.insert(0, '.')
from app import app, User, Scheme
from app.engine.eligibility import (
    EligibilityEngine, 
    get_canonical_field,
    get_profile_value
)
from app.engine.questions import is_user_answerable
from collections import Counter

print("=" * 70)
print("STRICT CONDITION-DRIVEN INPUT SYSTEM")
print("=" * 70)

with app.app_context():
    user = User.query.filter_by(email='shreyas6504@gmail.com').first()
    profile = user.get_profile_dict()
    
    # Get schemes
    all_schemes = Scheme.query.filter_by(is_active=True).all()
    
    # Build strict profile - store CANONICAL only
    strict_profile = {}
    
    # Copy from original profile (canonical keys)
    for key, value in profile.items():
        if value is not None:
            canonical = get_canonical_field(key)
            strict_profile[canonical] = value
    
    print(f"Initial profile fields: {len(strict_profile)}")
    
    # Simulate answers for ALL possible user fields (optimized)
    # This simulates what would happen after user answers all questions
    common_user_fields = [
        'age', 'gender', 'state', 'category', 'occupation', 'annual_income',
        'education_level', 'is_student', 'is_bpl', 'has_bank_account', 'is_disabled',
        'is_rural', 'is_urban', 'residence', 'marital_status', 'religion',
        'citizenship', 'bank_account', 'consent', 'disability_percentage',
        'land_size_acres', 'num_daughters', 'family_income', 'income'
    ]
    
    for field in common_user_fields:
        if field not in strict_profile:
            if 'age' in field:
                strict_profile[field] = 25
            elif 'income' in field:
                strict_profile[field] = 150000
            else:
                strict_profile[field] = True
    
    print(f"Profile fields after simulation: {len(strict_profile)}")
    
    # Evaluate
    engine = EligibilityEngine()
    results = {'eligible': 0, 'possible': 0, 'ineligible': 0}
    missing_count = 0
    missing_fields = Counter()
    
    for scheme in all_schemes:
        eo = engine.evaluate(scheme, strict_profile)
        results[eo.result] += 1
        
        # Check hard user conditions directly in profile
        for cr in eo.condition_results:
            if is_user_answerable(cr.field):
                ct = getattr(cr, 'condition_type', 'soft')
                if ct == 'hard':
                    status = str(cr.status).strip().lower() if cr.status else 'missing'
                    if status in ['missing', 'unknown', 'none', '']:
                        canonical = get_canonical_field(cr.field)
                        if strict_profile.get(canonical) is None:
                            missing_count += 1
                            missing_fields[canonical] += 1
    
    print(f"\n=== RESULTS ===")
    print(f"ELIGIBLE:    {results['eligible']}")
    print(f"POSSIBLE:    {results['possible']}")
    print(f"INELIGIBLE:  {results['ineligible']}")
    print(f"TOTAL:       {results['eligible'] + results['possible'] + results['ineligible']}")
    print(f"\nTotal missing hard conditions: {missing_count}")
    
    if missing_fields:
        print(f"\nMost common missing fields:")
        for f, c in missing_fields.most_common(10):
            print(f"  {f}: {c}")
    else:
        print(f"\n✅ SUCCESS: ZERO missing!")

print("\n" + "=" * 70)