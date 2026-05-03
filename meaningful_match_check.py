import json
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from static.engine import YojanaMitraInferenceEngine

def audit_meaningful_matches():
    with open('all_conditions_classified.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    schemes = []
    for sid, conds in data.items():
        if isinstance(conds, list):
            s = conds[0].copy()
            s['id'] = sid
            schemes.append(s)
        elif isinstance(conds, dict):
            s = conds.copy()
            s['id'] = sid
            schemes.append(s)

    # TEST PROFILE: A 25-year-old Male from Delhi
    user = {"age": 25, "gender": "Male", "state": "Delhi", "occupation": "Student", "is_student": True}
    engine = YojanaMitraInferenceEngine(user_profile=user)

    print(f"--- AUDITING FALSE POSITIVES ---")
    
    leaks = 0
    for s in schemes:
        res = engine.evaluate_scheme(s)
        name = s.get('scheme_name', 'Unknown')
        
        # LOGIC CHECK: If a 25-year-old is "Fully Eligible" for a 60+ scheme
        # Wait, the conditions are in classified_conditions, let's just check the age operator
        min_age = 0
        for c in s.get('classified_conditions', []):
            if c['field'] == 'age' and c['operator'] in ['>=', '>']:
                try: min_age = float(c['value'])
                except: pass
                
        if res['status'] == 'FULLY_ELIGIBLE' and min_age > 25:
            print(f"🚨 FALSE POSITIVE: Scheme ID {s['id']}")
            print(f"   -> Reason: {res['reason']}")
            print(f"   -> User Age: 25 | Scheme Min Age: {min_age}")
            print(f"   -> Engine matched this because: {res.get('confidence')} Confidence\n")
            leaks += 1
            
    print(f"Total False Positives Found: {leaks}")

if __name__ == "__main__":
    audit_meaningful_matches()
