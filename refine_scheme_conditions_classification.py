"""
refine_scheme_conditions_classification.py
Automate condition classification (CORE, PROOF, SUPPORTING) using Gemini 1.5.
"""
import os, json, time
import google.generativeai as genai
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)

MODEL_NAME = 'gemini-flash-latest'
model = genai.GenerativeModel(MODEL_NAME)

PROMPT_TEMPLATE = """
Classify the following eligibility conditions for a scheme into CORE, PROOF, or SUPPORTING.

SCHEME DETAILS:
Name: {name}
Description: {description}
Current Target Group: {target_group}

CONDITIONS TO CLASSIFY:
{conditions_json}

STRICT RULES:
1. CORE (STRICT DISQUALIFIER): Mark as CORE if it defines WHO the scheme is for (age, gender, income, caste, state, occupation, category). These are hard eligibility boundaries. If this fails, the user is NOT_ELIGIBLE.
2. PROOF (DOCUMENT / VERIFICATION): Mark as PROOF if it is a document (Aadhaar, bank account, ration card, certificates, registration). If missing, user is POSSIBLY_ELIGIBLE.
3. SUPPORTING (DEFAULT SAFE CATEGORY): Mark as SUPPORTING if it is NOT a strict disqualifier, vague, process-related, or a self-declaration (e.g., is_in_good_health, willingness_to_work, application timing, achievement certificates). If missing, user is NOT REJECTED.

CRITICAL QUESTION:
If this fails, does it fundamentally mean the scheme is NOT meant for this person?
- YES -> CORE
- NO -> SUPPORTING

Return the classification in the following JSON format:
{{
    "scheme_id": "{scheme_id}",
    "classified_conditions": [
        {{
            "field": "field_name",
            "operator": "operator",
            "value": "actual_value",
            "classification": "core | proof | supporting",
            "reason": "Short explanation"
        }}
    ]
}}
"""

def load_data():
    with open('all_conditions.json', 'r', encoding='utf-8') as f:
        conditions_data = json.load(f)["schemes"]
    
    with open('all_schemes_fixed.json', 'r', encoding='utf-8') as f:
        schemes_raw = json.load(f)
        schemes_map = {str(s['id']): s for s in schemes_raw}
    
    return conditions_data, schemes_map

def classify_scheme(scheme_id, conditions, scheme_info):
    name = scheme_info.get('name', 'Unknown Scheme')
    description = scheme_info.get('description', '')
    target_group = scheme_info.get('target_group_category', '')
    
    prompt = PROMPT_TEMPLATE.format(
        name=name,
        description=description,
        target_group=target_group,
        conditions_json=json.dumps(conditions, indent=2),
        scheme_id=scheme_id
    )
    
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Error classifying scheme {scheme_id}: {e}")
        return None

def run_classification(batch_limit=5):
    conditions_data, schemes_map = load_data()
    results = {}
    
    if os.path.exists('all_conditions_classified.json'):
        with open('all_conditions_classified.json', 'r', encoding='utf-8') as f:
            results = json.load(f)
    
    processed_ids = set(results.keys())
    remaining_ids = [sid for sid in conditions_data.keys() if sid not in processed_ids]
    
    print(f"Total schemes: {len(conditions_data)}")
    print(f"Already processed: {len(processed_ids)}")
    print(f"Remaining: {len(remaining_ids)}")
    
    if not remaining_ids:
        print("All schemes already processed!")
        return

    # Process batch
    count = 0
    for sid in tqdm(remaining_ids[:batch_limit]):
        conds = conditions_data[sid].get("conditions", [])
        if not conds: continue
        
        info = schemes_map.get(sid, {})
        data = classify_scheme(sid, conds, info)
        if data:
            results[sid] = data
            count += 1
            # Save progress incrementally
            with open('all_conditions_classified.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
        
        # Avoid rate limits
        time.sleep(1)
    
    print(f"\nSuccessfully classified {count} schemes.")

if __name__ == "__main__":
    # Test batch of 5 schemes
    run_classification(batch_limit=5)
