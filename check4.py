import sys
sys.path.insert(0, '.')
from app import app, Scheme, User
from app.engine.eligibility import EligibilityEngine

with app.app_context():
    user = User.query.filter_by(email='shreyas6504@gmail.com').first()
    profile = user.get_profile_dict()
    engine = EligibilityEngine()
    
    for sid in [1, 528, 4337, 4339]:
        scheme = Scheme.query.get(sid)
        result = engine.evaluate(scheme, profile, 0.5)
        
        print('=== ID', sid, '===')
        print('Scheme:', scheme.name[:50])
        print('Result:', result.result)
        
        conds = list(scheme.conditions)
        for c in conds:
            field = c.field
            user_val = profile.get(field)
            print(f'  {field}: user={user_val}')
        print()
