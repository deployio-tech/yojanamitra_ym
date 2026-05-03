import sys
sys.path.insert(0, '.')
from app import app, User, Scheme
from app.engine.eligibility import EligibilityEngine, get_canonical_field
from app.engine.questions import is_user_answerable, QUESTION_TEMPLATES
from collections import Counter
import time

# Simulate answers for any field
def simulate(field):
    if field in ['citizenship', 'consent', 'bank_account']:
        return True
    if 'age' in field:
        return 25
    if 'income' in field:
        return 150000
    return "test_value"

print("Testing strict system with full simulation...")

with app.app_context():
    user = User.query.filter_by(email='shreyas6504@gmail.com').first()
    profile = user.get_profile_dict()
    
    # Build profile with simulated answers for ALL common fields
    strict_profile = {}
    
    # Copy original
    for k, v in profile.items():
        if v is not None:
            strict_profile[get_canonical_field(k)] = v
    
    # Add simulated answers for common fields
    common = ['age', 'gender', 'category', 'occupation', 'state', 'residence',
              'education_level', 'is_student', 'is_bpl', 'has_bank_account',
              'annual_income', 'income', 'family_income', 'is_rural', 'is_urban',
              'is_disabled', 'disability_percentage', 'marital_status', 'religion',
              'citizenship', 'bank_account', 'consent', 'land_size_acres', 'num_daughters']
    
    for f in common:
        if f not in strict_profile:
            if 'age' in f or 'percentage' in f or 'income' in f:
                strict_profile[f] = 25 if 'age' in f else 150000
            else:
                strict_profile[f] = True
    
    print(f"Profile size: {len(strict_profile)}")
    
    # Evaluate all schemes
    engine = EligibilityEngine()
    schemes = Scheme.query.filter_by(is_active=True).all()
    
    results = {'eligible': 0, 'possible': 0, 'ineligible': 0}
    hard_missing = Counter()
    
    start = time.time()
    for scheme in schemes:
        eo = engine.evaluate(scheme, strict_profile)
        results[eo.result] += 1
        
        for cr in eo.condition_results:
            if is_user_answerable(cr.field):
                ct = getattr(cr, 'condition_type', 'soft')
                if ct == 'hard':
                    status = str(cr.status).strip().lower() if cr.status else 'missing'
                    missing_statuses = ['missing', 'unknown', 'none', '']
                    if status in missing_statuses:
                        hard_missing[get_canonical_field(cr.field)] += 1
    
    print(f"Time: {time.time()-start:.1f}s")
    print(f"\nRESULTS:")
    print(f"  ELIGIBLE:   {results['eligible']}")
    print(f"  POSSIBLE:   {results['possible']}")
    print(f"  INELIGIBLE: {results['ineligible']}")
    
    print(f"\nHard missing count: {sum(hard_missing.values())}")
    print(f"Top missing: {hard_missing.most_common(10)}")