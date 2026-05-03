import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMES_PATH = os.path.join(BASE_DIR, 'all_conditions_classified.json')

try:
    from static.engine import YojanaMitraInferenceEngine
    print(f"✅ Data found at: {SCHEMES_PATH}")
except ImportError:
    print("❌ Engine missing.")
    sys.exit(1)

def analyze_matching():
    with open(SCHEMES_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle both formats: List of dicts OR Dict of dicts
    if isinstance(data, list):
        all_schemes = data
    elif isinstance(data, dict):
        all_schemes = list(data.values())
    else:
        print("❌ Data is not a list or dictionary.")
        return

    test_profile = {"age": 10, "state": "Delhi", "gender": "Male", "occupation": "Student"}
    engine = YojanaMitraInferenceEngine(user_profile=test_profile)
    
    print(f"--- 🧪 ANALYZING {len(all_schemes)} SCHEMES ---")
    
    leaks = 0
    for scheme in all_schemes:
        # Check if the item is a string (ID) or a dictionary (Full Data)
        if isinstance(scheme, str):
            print(f"🚨 DATA ERROR: Scheme '{scheme}' is just a string ID, not a full data object.")
            continue
            
        result = engine.evaluate_scheme(scheme)
        
        # Checking for the "20+ Leaks" you saw earlier
        if result['status'] == 'FULLY_ELIGIBLE':
            reqs = scheme.get('requirements', {})
            min_age = reqs.get('min_age', 0) if isinstance(reqs, dict) else 0
            if min_age > 10:
                leaks += 1
                if leaks <= 3:
                    print(f"🚨 LEAK: {scheme.get('scheme_name')} matched for 10-year-old (Req: {min_age})")

    print(f"\n📊 Total Leaks Found: {leaks}")
    print("✅ Analysis Complete.")

if __name__ == "__main__":
    analyze_matching()