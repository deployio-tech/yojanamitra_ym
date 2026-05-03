import json
import os
from static.engine import YojanaMitraInferenceEngine

def inspect_bridge():
    # 1. Check the User Profile the website is actually using
    # (Assuming your app stores the active session/profile in a JSON or DB)
    # For now, let's simulate the 'Empty Profile' bug
    website_profile = {} # If the website sends this, everything returns 0
    
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

    engine = YojanaMitraInferenceEngine(user_profile=website_profile)
    
    results = [engine.evaluate_scheme(s) for s in schemes]
    fully = len([r for r in results if r['status'] == 'FULLY_ELIGIBLE'])
    possibly = len([r for r in results if r['status'] == 'POSSIBLY_ELIGIBLE'])

    print(f"--- BRIDGE INSPECTOR ---")
    print(f"Profile sent by Website: {website_profile}")
    print(f"Fully Eligible: {fully} | Possibly Eligible: {possibly}")
    
    if fully == 0 and possibly == 0:
        print("DISCONNECT FOUND: The engine is too strict for an empty profile.")
        print("SOLUTION: We must allow 'Possibly Eligible' if fields are NULL.")

if __name__ == "__main__":
    inspect_bridge()