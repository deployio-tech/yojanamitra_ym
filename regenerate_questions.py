"""
GEMINI-BASED QUESTION GENERATION PIPELINE
With fixes:
1. Better normalization (remove punctuation)
2. Store question not concept
3. Similarity check
"""
import json
import re
import os

# Load current registry
with open('concept_registry.json', 'r', encoding='utf-8') as f:
    registry = json.load(f)

concepts = registry['concepts']
print(f"Loaded {len(concepts)} concepts")

# ============================================================
# NORMALIZATION FUNCTION (FIX 1)
# ============================================================
def normalize_question(q: str) -> str:
    q = q.lower()
    q = re.sub(r'[^\w\s]', '', q)  # remove punctuation
    q = re.sub(r'\s+', ' ', q)     # normalize spaces
    return q.strip()

# ============================================================
# QUESTION REGISTRY (FIX 2 & 3)
# ============================================================
question_registry = {}  # normalized_question -> original_question
concept_to_new_question = {}  # concept -> new_question

# Gemini prompt
gemini_prompt_template = """You are generating a user-facing eligibility question.

Input: A concept name representing a real-world attribute.

Your job: Convert it into a clean, natural, human-friendly question.

Rules:
1. Instantly understandable by normal person
2. Avoid technical words
3. Use natural spoken English
4. Prefer yes/no when possible
5. If unclear, infer intelligently
6. DO NOT repeat concept literally
7. DO NOT use underscores

Examples:
aadhaar -> Do you have an Aadhaar card?
land_ownership -> Do you own agricultural land?
student_status -> Are you a student?

Output: ONLY the final question. No explanation."""

# Check if Gemini is available
try:
    from google.generativeai import configure, GenerativeModel
    GEMINI_AVAILABLE = True
    configure(api_key=os.environ.get('GEMINI_API_KEY', ''))
    model = GenerativeModel('gemini-flash-latest')
    print("Gemini API configured")
except Exception as e:
    GEMINI_AVAILABLE = False
    print(f"Gemini not available: {e}")

# Fallback question generator
def generate_question_fallback(concept: str) -> str:
    """Fallback when Gemini not available"""
    # Manual mapping for common concepts
    q_map = {
        "aadhaar": "Do you have an Aadhaar card?",
        "bank_account": "Do you have a bank account?",
        "ration_card": "Do you have a ration card?",
        "pan_card": "Do you have a PAN card?",
        "disability": "Are you a person with disability?",
        "farmer": "Are you a farmer?",
        "student_status": "Are you a student?",
        "widow": "Are you a widow?",
        "orphan": "Are you an orphan?",
        "tribal": "Are you a tribal person?",
        "bpl": "Are you from a BPL family?",
        "ews": "Are you from EWS?",
        "nri": "Are you an NRI?",
        "pensioner": "Are you a pensioner?",
        "shg_member": "Are you a member of a Self Help Group?",
        "fisherman": "Are you a fisherman?",
        "land_ownership": "Do you own agricultural land?",
        "gender": "What is your gender?",
        "marital_status": "What is your marital status?",
        "residence": "What is your current residence?",
        "minority_status": "Do you belong to a minority community?",
        "employment": "Are you employed?",
        "pregnancy_status": "Are you pregnant or lactating?",
        "parent_status": "Do you have children?",
        "benefit_recipient": "Are you receiving any government benefits?",
        "govt_employee": "Are you a government employee?",
        "health_condition": "Do you have any health conditions?",
        "education": "What is your education status?",
    }
    
    if concept in q_map:
        return q_map[concept]
    
    # Generic fallback
    return f"What is your {concept.replace('_', ' ')}?"

def generate_question_gemini(concept: str) -> str:
    """Generate question using Gemini"""
    try:
        response = model.generate_content(f"{gemini_prompt_template}\n\nConcept: {concept}")
        return response.text.strip()
    except Exception as e:
        print(f"Gemini error for {concept}: {e}")
        return generate_question_fallback(concept)

# ============================================================
# PROCESS ALL CONCEPTS
# ============================================================
print("\nProcessing concepts...")

for i, item in enumerate(concepts):
    concept = item['concept']
    
    # Generate question
    if GEMINI_AVAILABLE:
        new_question = generate_question_gemini(concept)
    else:
        new_question = generate_question_fallback(concept)
    
    # Normalize and check registry
    normalized = normalize_question(new_question)
    
    if normalized in question_registry:
        # Reuse existing question
        new_question = question_registry[normalized]
        print(f"  [{i+1}] {concept} -> REUSED: {new_question}")
    else:
        # Store new
        question_registry[normalized] = new_question
        print(f"  [{i+1}] {concept} -> {new_question}")
    
    # Save to mapping
    concept_to_new_question[concept] = new_question

# ============================================================
# UPDATE REGISTRY
# ============================================================
for item in concepts:
    concept = item['concept']
    item['question'] = concept_to_new_question[concept]

# Save updated registry
with open('concept_registry.json', 'w', encoding='utf-8') as f:
    json.dump(registry, f, indent=2, ensure_ascii=False)

print(f"\nSaved to: concept_registry.json")

# ============================================================
# VALIDATION
# ============================================================
print("\n" + "=" * 80)
print("VALIDATION")
print("=" * 80)

# Check all have questions
empty = sum(1 for c in concepts if not c.get('question'))
print(f"Empty questions: {empty}")

# Check duplicates
all_questions = [normalize_question(c['question']) for c in concepts]
unique_questions = set(all_questions)
print(f"Total questions: {len(all_questions)}")
print(f"Unique questions: {len(unique_questions)}")
print(f"Duplicates: {len(all_questions) - len(unique_questions)}")

if empty == 0 and len(unique_questions) == len(all_questions):
    print("\nVALIDATION: PASSED")

# ============================================================
# SAMPLES
# ============================================================
print("\n" + "=" * 80)
print("SAMPLE 10 CONCEPTS + QUESTIONS:")
print("=" * 80)
for c in concepts[:10]:
    print(f"\n{c['concept']}:")
    print(f"  {c['question']}")

print("\n" + "=" * 80)
print(f"TOTAL CONCEPTS: {len(concepts)}")
print("=" * 80)