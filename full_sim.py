import sys
sys.path.insert(0, '.')
from app import app, User, Scheme
from app.engine.eligibility import EligibilityEngine, get_canonical_field
from app.engine.questions import is_user_answerable
from collections import Counter
import time

print("Testing with FULL field population...")

with app.app_context():
    user = User.query.filter_by(email='shreyas6504@gmail.com').first()
    profile = user.get_profile_dict()
    
    # Step 1: Extract ALL condition fields (HARD only)
    all_schemes = Scheme.query.filter_by(is_active=True).all()
    
    all_condition_fields = set()
    for scheme in all_schemes:
        for cond in scheme.conditions:
            if is_user_answerable(cond.field):
                if getattr(cond, 'condition_type', None) == 'hard':
                    all_condition_fields.add(get_canonical_field(cond.field))
    
    print(f"Total HARD condition fields: {len(all_condition_fields)}")
    
    # Step 2: Build FULL profile with simulated answers for ALL
    full_profile = {}
    
    # Copy original profile
    for k, v in profile.items():
        if v is not None:
            full_profile[get_canonical_field(k)] = v
    
    # Add simulated answers for ALL extracted fields
    for field in all_condition_fields:
        if field not in full_profile:
            # Simulate reasonable answers
            if field in ['citizenship', 'consent', 'bank_account', 'is_nri']:
                full_profile[field] = True
            elif 'age' in field:
                full_profile[field] = 25
            elif 'income' in field:
                full_profile[field] = 200000
            elif 'category' in field or 'caste' in field:
                full_profile[field] = 'OBC'
            elif 'state' in field or 'residence' in field or 'domicile' in field:
                full_profile[field] = 'Karnataka'
            elif 'gender' in field:
                full_profile[field] = 'male'
            elif 'education' in field or 'class' in field:
                full_profile[field] = 'Graduation'
            elif 'occupation' in field or 'employment' in field:
                full_profile[field] = 'student'
            elif 'land' in field or 'lease' in field:
                full_profile[field] = 1.0
            elif 'duration' in field or 'period' in field:
                full_profile[field] = 12
            else:
                full_profile[field] = True
    
    print(f"Profile size after simulation: {len(full_profile)}")
    
    # Step 3: Evaluate
    engine = EligibilityEngine()
    
    results = {'eligible': 0, 'possible': 0, 'ineligible': 0}
    hard_missing = Counter()
    schemes_with_missing = 0
    
    start = time.time()
    for scheme in all_schemes:
        eo = engine.evaluate(scheme, full_profile)
        results[eo.result] += 1
        
        has_missing = False
        for cr in eo.condition_results:
            if is_user_answerable(cr.field):
                ct = getattr(cr, 'condition_type', 'soft')
                if ct == 'hard':
                    status = str(cr.status).strip().lower() if cr.status else 'missing'
                    missing_list = ['missing', 'unknown', 'none', '']
                    if status in missing_list:
                        hard_missing[get_canonical_field(cr.field)] += 1
                        has_missing = True
        
        if has_missing:
            schemes_with_missing += 1
    
    print(f"Time: {time.time()-start:.1f}s")
    print(f"\n=== RESULTS ===")
    print(f"ELIGIBLE:   {results['eligible']}")
    print(f"POSSIBLE:   {results['possible']}")
    print(f"INELIGIBLE: {results['ineligible']}")
    print(f"\nSchemes with HARD missing: {schemes_with_missing}")
    print(f"Total hard missing conditions: {sum(hard_missing.values())}")
    
    if hard_missing:
        print(f"\nTop missing fields:")
        for f, c in hard_missing.most_common(10):
            print(f"  {f}: {c}")
    else:
        print(f"\n✅ SUCCESS: ZERO missing!")

print("\n" + "=" * 70)