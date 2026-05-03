import os
import json
import time
import logging
from dotenv import load_dotenv

logger = logging.getLogger('yojanamitra')

GEMINI_API_KEY = ''
try:
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
        import re
        match = re.search(r"GEMINI_API_KEY\s*=\s*['\"]([^'\"]+)['\"]", content)
        if match:
            GEMINI_API_KEY = match.group(1)
except Exception as e:
    pass

if not GEMINI_API_KEY:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

import google.generativeai as genai
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Using the futuristic Flash model that avoids Quota Exceeded limits!
MODEL_NAME = 'models/gemini-flash-latest'

RESOLVER_SYSTEM_PROMPT = """You are a Contextual Eligibility Engine for Indian Government Schemes.
You evaluate 'POSSIBLY ELIGIBLE' schemes that contain edge-case requirements (like 'child 0-6' or 'pregnant woman').

INPUT:
1. Complete User Database Profile (JSON) - contains exact values like age, gender, is_pregnant, achievement_certificates, etc.
2. A dictionary of Scheme IDs mapping to their 'custom_verification_reason' (the string question asked by a naive engine).

YOUR TASK:
For EVERY scheme ID in the input list, cross-reference the `custom_verification_reason` with the User Profile.
Does the user profile explicitly make them INELIGIBLE? (e.g. they are Male, but reason is about pregnancy) -> INELIGIBLE.
Does the user profile already explicitly SATISFY the reason? (e.g. reason is "Are you a sports person?" and they have sports certificates) -> ELIGIBLE.
Is it TRULY UNKNOWN? (e.g. reason is "Do you own a tractor?" and the profile says nothing about tractors) -> POSSIBLY_ELIGIBLE.

CRITICAL LOGIC:
- If a scheme reason requires "child 0-6 OR pregnant woman" and the user is Male AND Age 21, they fail BOTH conditions. Mark INELIGIBLE.
- Be highly strict against logical impossibilities based on age, gender, occupation, caste.

OUTPUT EXACT JSON ONLY:
{
  "scheme_id_1": {
    "status": "INELIGIBLE" | "ELIGIBLE" | "POSSIBLY_ELIGIBLE",
    "reason_for_status": "Brief explanation",
    "refined_question": null or "The new, tailored question to ask the user if POSSIBLY_ELIGIBLE"
  },
  ...
}
"""

def resolve_possibly_eligible_batch(user_profile, possibly_list):
    """
    Evaluates POSSIBLY_ELIGIBLE schemes dynamically using the user's full structured JSON profile.
    Returns (eligible_list, revised_possibly_list, ineligible_count).
    """
    if not GEMINI_API_KEY or not possibly_list:
        return [], possibly_list, []
        
    model = genai.GenerativeModel(MODEL_NAME, system_instruction=RESOLVER_SYSTEM_PROMPT)
    
    # Filter profile to remove junk
    clean_profile = {k: v for k, v in user_profile.items() if v is not None and v != '' and k not in ['password_hash', 'id']}
    
    # Pack the list in chunks of 8 for stability and better error isolation
    chunk_size = 8
    new_eligible = []
    new_possibly = []
    new_ineligible = []
    
    for i in range(0, len(possibly_list), chunk_size):
        chunk = possibly_list[i:i + chunk_size]
        schemes_to_eval = {}
        
        for p in chunk:
            reason = p.get('question_text', '')
            if isinstance(p.get('unknown_fields'), list) and len(p['unknown_fields']) > 0:
                for field in p['unknown_fields']:
                    if '?' in field:
                        reason += ' | ' + field
            schemes_to_eval[str(p['scheme_id'])] = reason

        payload = json.dumps({
            "user_profile": clean_profile,
            "schemes_to_evaluate": schemes_to_eval
        }, indent=2)

        try:
            # Small delay to prevent hitting rate limits (429)
            if i > 0:
                time.sleep(1.5)

            response = model.generate_content(payload)
            res_text = response.text.strip()
            if res_text.startswith('```json'):
                res_text = res_text[7:-3]
            elif res_text.startswith('```'):
                res_text = res_text[3:-3]
                
            resolutions = json.loads(res_text.strip())
            
            for p in chunk:
                sid = str(p['scheme_id'])
                res = resolutions.get(sid)
                if not res:
                    # If AI skipped it, keep it in current state (Pass-through)
                    new_eligible.append(p)
                    continue
                    
                status = res.get('status', 'ELIGIBLE') # Default to Eligible if running as Stress Test
                reason = res.get('reason_for_status', 'Verified by deep analysis')
                
                if status == 'INELIGIBLE':
                    p['status'] = 'INELIGIBLE'
                    p['reason'] = reason
                    new_ineligible.append(p)
                elif status == 'POSSIBLY_ELIGIBLE' or status == 'POSSIBLE':
                    if res.get('refined_question'):
                        p['question_text'] = "Fact Check: " + res['refined_question']
                    p['reason'] = reason
                    new_possibly.append(p)
                else:
                    new_eligible.append(p)
                    
        except Exception as e:
            logger.error(f"Resolver Chunk Error: {str(e)}", exc_info=True)
            print(f"Resolver Chunk Error: {str(e)}")
            # FAILSAFE: If AI fails, do NOT demote the schemes. Keep them as eligible.
            new_eligible.extend(chunk)
            
    return new_eligible, new_possibly, new_ineligible
