import os
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

def find_model():
    print("--- YOJANAMITRA: SEARCHING FOR WORKING MODEL ---")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set.")
        return

    genai.configure(api_key=api_key)
    
    print("Fetching models...")
    try:
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    except Exception as e:
        print(f"FAILED to list models: {e}")
        return

    working_models = []
    
    for model_name in all_models:
        clean_name = model_name.replace("models/", "")
        print(f"Testing {clean_name}...", end=" ", flush=True)
        try:
            model = genai.GenerativeModel(clean_name)
            response = model.generate_content("Ping", generation_config={"max_output_tokens": 5})
            print("DONE! [WORKING]")
            working_models.append(clean_name)
        except ResourceExhausted as e:
            if "limit: 0" in str(e).lower():
                print("LOCKED (Limit 0)")
            else:
                print("RATE LIMITED")
        except Exception as e:
            print(f"ERROR: {str(e)[:50]}")

    print("\n--- RESULTS ---")
    if working_models:
        print("The following models are ACTIVE and have quota:")
        for wm in working_models:
            print(f"  - {wm}")
        print(f"\nRecommended command:")
        print(f"python extract_conditions_v4.py --slow --resume --model \"{working_models[0]}\"")
    else:
        print("CRITICAL: All models returned 'Limit 0' or 'Rate Limited'.")
        print("Your account is fully blocked on the Free Tier for today.")
        print("You MUST upgrade to 'Pay-as-you-go' in AI Studio Settings to proceed now.")

if __name__ == "__main__":
    find_model()
