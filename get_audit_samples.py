import os
import json
import sqlite3
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Config
DB_PATH = r"C:\scrollyym\yojana-mitra-backend\instance\yojanamitra.db"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "PASTE_YOUR_GEMINI_API_KEY_HERE")
TARGET_EMAIL = "shreyas6504@gmail.com"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-flash-latest")

def get_samples():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get user
    cursor.execute("SELECT * FROM user WHERE email = ?", (TARGET_EMAIL,))
    user_row = cursor.fetchone()
    user_data = dict(user_row)
    
    # Get first 5 schemes
    cursor.execute("SELECT id, name, description, eligibility FROM scheme LIMIT 5")
    schemes = cursor.fetchall()
    
    samples = []
    for s in schemes:
        scheme_json = dict(s)
        prompt = f"""You are an expert at evaluating eligibility for Indian government schemes.

USER PROFILE:
{json.dumps(user_data, indent=2)}

SCHEME CONDITIONS:
{json.dumps(scheme_json, indent=2)}

TASK:
Classify eligibility into:

* FULLY_ELIGIBLE
* POSSIBLY_ELIGIBLE
* NOT_ELIGIBLE

Rules:

* Missing data -> POSSIBLY_ELIGIBLE
* Any failed condition -> NOT_ELIGIBLE
* All satisfied -> FULLY_ELIGIBLE

Return ONLY JSON:
{{
"eligibility": "...",
"reason": "..."
}}"""
        response = model.generate_content(prompt)
        res_text = response.text.strip()
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0].strip()
        elif "```" in res_text:
            res_text = res_text.split("```")[1].split("```")[0].strip()
        
        samples.append({
            "scheme": s["name"],
            "gemini_result": json.loads(res_text)
        })
    
    print(json.dumps(samples, indent=2))
    conn.close()

if __name__ == "__main__":
    get_samples()

