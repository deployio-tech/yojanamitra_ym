"""
Gemini client for concept generation.
Contains prompt builder, API call, and strict JSON parser.
"""
import json
import os
import sys
import google.generativeai as genai

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure Gemini
API_KEY = os.environ.get('GEMINI_API_KEY', 'PASTE_YOUR_GEMINI_API_KEY_HERE')
genai.configure(api_key=API_KEY)

try:
    MODEL = genai.GenerativeModel('gemini-flash-latest')
    HAS_GEMINI = True
    print("Gemini client configured successfully")
except Exception as e:
    HAS_GEMINI = False
    MODEL = None
    print(f"Warning: Could not configure Gemini: {e}")


# ── GEMINI PROMPT (PRODUCTION-GRADE) ──────────────────────────────────────────
GEMINI_PROMPT_TEMPLATE = """You are designing a user-facing eligibility question system.

Input:
A list of field names representing eligibility conditions.

Your task:
For EACH field, generate:

A clean concept name (snake_case, 1–3 words)
A natural, human-friendly question

RULES:

CONCEPT:

Must be generalizable (not scheme-specific)
Must be 1–3 words max
Use snake_case
Avoid: status, type, classification, indicator, metadata, flag
Examples:
has_aadhaar_card → aadhaar
owns_agricultural_land → land_ownership
is_student → student_status

QUESTION:

Must be simple, spoken English
Must be understandable by a normal person
Prefer yes/no questions
Must NOT repeat field name
Must NOT sound technical

GOOD:
"Do you have an Aadhaar card?"
"Are you a student?"
"Do you own agricultural land?"

BAD:
"What is your aadhaar_status?"
"What is your classification type?"
"What is your engaged_in?"

OUTPUT FORMAT (STRICT JSON ONLY):

[
{
"field": "has_aadhaar_card",
"concept": "aadhaar",
"question": "Do you have an Aadhaar card?"
}
]

DO NOT add explanations.
DO NOT return anything outside JSON.
"""


def build_prompt(fields, batch_size=30):
    """
    Build the Gemini prompt with a list of fields.
    
    Args:
        fields: List of field names to generate concepts for
        batch_size: Maximum fields to include (quality control)
    
    Returns:
        Complete prompt string
    """
    # Enforce batch size limit for quality
    fields = fields[:batch_size]
    
    # Build field list
    field_list = "\n".join([f"- {f}" for f in fields])
    
    prompt = f"""Input fields:
{field_list}

{GEMINI_PROMPT_TEMPLATE}"""
    
    return prompt


def call_gemini(prompt, max_retries=3):
    """
    Call Gemini API with retry logic.
    
    Args:
        prompt: The prompt to send
        max_retries: Number of retry attempts
    
    Returns:
        Raw response text from Gemini
    """
    if not HAS_GEMINI or MODEL is None:
        # Mock response for testing
        return "[]"
    
    for attempt in range(max_retries):
        try:
            response = MODEL.generate_content(prompt)
            if response and hasattr(response, 'text'):
                return response.text
        except Exception as e:
            print(f"Gemini call attempt {attempt + 1} failed: {e}")
            continue
    
    print("⚠️ Gemini call failed after all retries")
    return "[]"


def parse_gemini_response(text):
    """
    Strict JSON parser for Gemini response.
    Enforces structure and filters invalid entries.
    
    Args:
        text: Raw response from Gemini
    
    Returns:
        List of valid concept objects: [{"field": "...", "concept": "...", "question": "..."}]
    """
    if not text:
        return []
    
    try:
        # Find JSON array boundaries
        start = text.find("[")
        end = text.rfind("]")
        
        if start == -1 or end == -1:
            print("⚠️ No JSON array found in response")
            return []
        
        json_str = text[start:end+1]
        data = json.loads(json_str)
        
        # Enforce structure
        valid = []
        for item in data:
            if (
                isinstance(item, dict)
                and "field" in item
                and "concept" in item
                and "question" in item
            ):
                # Clean up the entry
                valid.append({
                    "field": str(item["field"]).strip(),
                    "concept": str(item["concept"]).strip().lower(),
                    "question": str(item["question"]).strip()
                })
        
        return valid
    
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parse error: {e}")
        return []
    except Exception as e:
        print(f"⚠️ Parse error: {e}")
        return []


def generate_concepts(fields, batch_size=30):
    """
    Main function: Generate concepts for a list of fields.
    
    Args:
        fields: List of field names
        batch_size: Maximum fields per batch
    
    Returns:
        List of parsed concept objects
    """
    # Enforce batch size
    fields = fields[:batch_size]
    
    # Build prompt
    prompt = build_prompt(fields, batch_size)
    
    # Call Gemini
    print(f"Calling Gemini with {len(fields)} fields...")
    response = call_gemini(prompt)
    
    # Parse response
    parsed = parse_gemini_response(response)
    print(f"Parsed {len(parsed)} valid concepts")
    
    return parsed


if __name__ == "__main__":
    # Test
    test_fields = [
        "has_goat_farming_license",
        "is_active_fisherman", 
        "owns_cattle_herd",
        "is_rural_entrepreneur"
    ]
    
    results = generate_concepts(test_fields)
    print(f"\nGenerated {len(results)} concepts:")
    for r in results:
        print(f"  {r}")
