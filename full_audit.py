import sys
sys.path.insert(0, '.')
from app import app, Scheme, User
from app.engine.eligibility import EligibilityEngine, ELIGIBLE, POSSIBLE, INELIGIBLE

with app.app_context():
    user = User.query.filter_by(email='shreyas6504@gmail.com').first()
    profile = user.get_profile_dict()
    engine = EligibilityEngine()
    
    all_schemes = Scheme.query.filter_by(is_active=True).all()
    
    print('=== FULL AUDIT: ALL SCHEMES ===')
    print('Processing', len(all_schemes), 'schemes...')
    
    stats = {'ELIGIBLE': 0, 'POSSIBLE': 0, 'INELIGIBLE': 0}
    eligible_list = []
    
    for i, scheme in enumerate(all_schemes):
        result = engine.evaluate(scheme, profile, 0.5)
        status = result.result
        
        if status == ELIGIBLE:
            stats['ELIGIBLE'] += 1
            eligible_list.append((scheme.id, scheme.name))
        elif status == INELIGIBLE:
            stats['INELIGIBLE'] += 1
        else:
            stats['POSSIBLE'] += 1
        
        if (i + 1) % 500 == 0:
            print(f'Processed {i+1}/{len(all_schemes)}')
    
    print()
    print('=== FINAL RESULTS ===')
    print('Total schemes:', len(all_schemes))
    print('ELIGIBLE:', stats['ELIGIBLE'])
    print('POSSIBLE:', stats['POSSIBLE'])
    print('INELIGIBLE:', stats['INELIGIBLE'])
    print()
    print('ELIGIBLE schemes:')
    for sid, name in eligible_list:
        print(f'  ID {sid}: {name[:70]}')
