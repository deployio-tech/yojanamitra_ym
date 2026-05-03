import os
import time
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

def monitor():
    print("--- YOJANAMITRA: QUOTA RESET MONITOR ---")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set.")
        return

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-flash-latest")
    
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        print(f"[{time.strftime('%H:%M:%S')}] Checking API status... (Elapsed: {int(elapsed)}s)")
        
        try:
            response = model.generate_content("Ping")
            print("\n>>> SUCCESS! The API is now accepting requests.")
            print(">>> You can restart your extraction script now.")
            break
        except ResourceExhausted as e:
            err_msg = str(e).lower()
            if "limit: 0" in err_msg:
                print("  STATUS: Blocked (Limit is still 0). Project is likely still propagating.")
            else:
                print(f"  STATUS: Rate Limited. Details: {e}")
            
            # Look for retry delay in the error
            if hasattr(e, 'retry_delay') and e.retry_delay:
                print(f"  RETRY SUGGESTED IN: {e.retry_delay} seconds")
        except Exception as e:
            print(f"  ERROR: {e}")
            
        print("  Waiting 30 seconds before next check...\n")
        time.sleep(30)

if __name__ == "__main__":
    monitor()
