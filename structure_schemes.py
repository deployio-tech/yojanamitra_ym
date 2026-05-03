
import os
import json
import time
from app import app, db, Scheme
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = 'gemini-flash-latest'
model = genai.GenerativeModel(gemini_model)

STRUCTURING_PROMPT = """
You are a PRODUCTION-GRADE data extractor for Indian government schemes. Precision is life-changing for the users. 
I will provide you with the name and eligibility/description text. 
Your task is to extract exact, strict criteria into JSON.

SCHEME NAME: {name}
TEXT: {eligibility}

Return ONLY valid JSON with these keys. USE null/[] IF NOT EXPLICITLY FOUND.
{{
    "min_age": int | null,
    "max_age": int | null,
    "allowed_genders": ["Male", "Female", "Transgender"],
    "max_income": int | null,
    "allowed_states": ["Karnataka", "Arunachal Pradesh", "All India", etc.],
    "allowed_castes": ["SC", "ST", "OBC", "General", "EWS"],
    "allowed_ration_card_types": ["BPL", "Antyodaya", "APL"],
    "disability_requirement": "Yes" | "No" | "Any",
    "minority_requirement": "Yes" | "No" | "Any",
    "senior_citizen_requirement": "Yes" | "No" | "Any",
    "widow_requirement": "Yes" | "No" | "Any"
}}

PRODUCTION RULES for Strictness:
1. RESIDENCY: If the name or text implies a state (e.g., "Chief Minister of Karnataka", "launched by Haryana Gov"), list ONLY that state in allowed_states. DO NOT default to All India if a state is mentioned.
2. EXCLUSIONARY LOGIC (DISABILITY/SENIOR/etc):
   - "Yes": Mandatory trait (e.g., Scholarship for Disabled).
   - "No": Absolute disqualifier. For all Military/Defense/Force schemes, disability_requirement MUST be "No".
   - "Any": Not a factor.
3. RATION CARD: Match "BPL" to "Below Poverty Line" or "PHH". Match "Antyodaya" to "AAY".
4. INCOME: If it says "not exceeding 2 Lakh", set max_income to 200000.
"""

def structure_all_schemes():
    with app.app_context():
        schemes = Scheme.query.all()
        print(f"Structuring {len(schemes)} schemes...")
        for s in schemes:
            try:
                # Only structure if not already heavily structured OR if force is wanted
                # For this task, we want to ensure ALL are "real"
                print(f"Structuring '{s.name}' (ID: {s.id})...")
                prompt = STRUCTURING_PROMPT.format(name=s.name, eligibility=s.eligibility or s.description)
                
                # Use a slower rate for safety if many schemes
                response = model.generate_content(prompt)
                
                text = response.text.strip()
                if text.startswith("```json"): text = text[7:-3].strip()
                elif text.startswith("```"): text = text[3:-3].strip()
                
                data = json.loads(text)
                
                # Update fields
                s.min_age = data.get('min_age')
                s.max_age = data.get('max_age')
                s.allowed_genders = json.dumps(data.get('allowed_genders', []))
                s.max_income = data.get('max_income')
                s.allowed_states = json.dumps(data.get('allowed_states', []))
                s.allowed_castes = json.dumps(data.get('allowed_castes', []))
                s.allowed_ration_card_types = json.dumps(data.get('allowed_ration_card_types', []))
                s.disability_requirement = data.get('disability_requirement', 'Any')
                s.minority_requirement = data.get('minority_requirement', 'Any')
                s.senior_citizen_requirement = data.get('senior_citizen_requirement', 'Any')
                s.widow_requirement = data.get('widow_requirement', 'Any')
                
                db.session.commit()
                print(f"Successfully structured '{s.name}'")
                time.sleep(0.5) # Slight delay
            except Exception as e:
                print(f"Error structuring {s.id}: {e}")
                db.session.rollback()

def structure_scheme_by_id(scheme_id):
    with app.app_context():
        s = Scheme.query.get(scheme_id)
        if not s:
            print(f"Scheme {scheme_id} not found.")
            return
        
        print(f"Structuring '{s.name}' (ID: {s.id})...")
        prompt = STRUCTURING_PROMPT.format(name=s.name, eligibility=s.eligibility or s.description)
        response = model.generate_content(prompt)
        
        text = response.text.strip()
        if text.startswith("```json"): text = text[7:-3].strip()
        elif text.startswith("```"): text = text[3:-3].strip()
        
        data = json.loads(text)
        
        # Update fields
        s.min_age = data.get('min_age')
        s.max_age = data.get('max_age')
        s.allowed_genders = json.dumps(data.get('allowed_genders', []))
        s.max_income = data.get('max_income')
        s.allowed_states = json.dumps(data.get('allowed_states', []))
        s.allowed_castes = json.dumps(data.get('allowed_castes', []))
        s.allowed_ration_card_types = json.dumps(data.get('allowed_ration_card_types', []))
        s.disability_requirement = data.get('disability_requirement', 'Any')
        s.minority_requirement = data.get('minority_requirement', 'Any')
        s.senior_citizen_requirement = data.get('senior_citizen_requirement', 'Any')
        s.widow_requirement = data.get('widow_requirement', 'Any')
        
        db.session.commit()
        print(f"Successfully structured '{s.name}'")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # Structure specific scheme
        scheme_id = int(sys.argv[1])
        structure_scheme_by_id(scheme_id)
    else:
        # Structure all
        structure_all_schemes()
