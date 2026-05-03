import json
import os
import sys

# 1. SETUP PATHS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMES_PATH = os.path.join(BASE_DIR, 'all_conditions_classified.json')

try:
    from static.engine import YojanaMitraInferenceEngine
    print("✅ Engine found. Starting diagnostic...")
except ImportError:
    print("❌ Engine missing in /static/engine.py")
    sys.exit(1)

def diagnostic():
    # 2. LOAD & UNWRAP DATA
    with open(SCHEMES_PATH, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    # Force data into a clean list, even if it's a dict or nested list
    clean_schemes = []
    items = raw_data if isinstance(raw_data, list) else list(raw_data.values())
    
    for item in items:
        # THE CRITICAL FIX: Unwrap the list if the scheme is nested like [[scheme]]
        if isinstance(item, list) and len(item) > 0:
            clean_schemes.append(item[0])
        elif isinstance(item, dict):
            clean_schemes.append(item)

    print(f"📋 Total Schemes Loaded: {len(clean_schemes)}")

    # 3. THE "KID TEST" (Scenario to find the 20+ leaks)
    # If a 10-year-old matches an Adult scheme, the matching is broken.
    kid_profile = {"age": 10, "state": "Delhi", "gender": "Male", "occupation": "Student"}
    engine = YojanaMitraInferenceEngine(user_profile=kid_profile)
    
    leaks = []
    fully_eligible_count = 0

    for scheme in clean_schemes:
        result = engine.evaluate_scheme(scheme)
        
        if result.get('status') == 'FULLY_ELIGIBLE':
            fully_eligible_count += 1
            # Check requirements manually to find the leak
            reqs = scheme.get('requirements', {})
            min_age = reqs.get('min_age', 0) if isinstance(reqs, dict) else 0
            
            if min_age > 10:
                leaks.append({
                    "name": scheme.get('scheme_name'),
                    "req_age": min_age,
                    "engine_reason": result.get('reason')
                })

    # 4. REPORT
    print("\n--- 📊 MATCHING REPORT ---")
    print(f"Total 'Fully Eligible' for a 10-year-old: {fully_eligible_count}")
    
    if leaks:
        print(f"🚨 CRITICAL LEAKS FOUND: {len(leaks)} schemes matched despite failing age gate.")
        print("Top 5 Leak Examples:")
        for l in leaks[:5]:
            print(f"   - {l['name']} (Requires Age: {l['req_age']} | Engine said: {l['engine_reason']})")
    else:
        print("✅ No Hard Guard leaks detected for the Kid Test.")

if __name__ == "__main__":
    diagnostic()