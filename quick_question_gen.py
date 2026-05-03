"""
QUICK QUESTION GENERATOR - BATCH MODE
Process in small batches to avoid timeout
"""
import json
import re
import time

# Load current registry
with open('concept_registry.json', 'r', encoding='utf-8') as f:
    registry = json.load(f)

concepts = registry['concepts']
print(f"Loaded {len(concepts)} concepts")

# Check Gemini availability
try:
    import os
    from google.generativeai import configure, GenerativeModel
    configure(api_key=os.environ.get('GEMINI_API_KEY', ''))
    model = GenerativeModel('gemini-flash-latest')
    GEMINI = True
    print("Gemini available")
except:
    GEMINI = False
    print("Using fallback")

# Normalization
def normalize(q):
    q = q.lower()
    q = re.sub(r'[^\w\s]', '', q)
    q = re.sub(r'\s+', ' ', q)
    return q.strip()

# Question map for fallback
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
    "activity_status": "Are you currently active/engaged in any work?",
    "first_time": "Is this your first time applying for this?",
    "membership": "Are you a member of any organization?",
    "verification": "Have you been verified by any authority?",
    "contribution": "Are you currently contributing to any fund?",
    "work_type": "What type of work do you do?",
    "disaster_affected": "Have you been affected by any disaster?",
    "native": "What is your native state?",
    "pursuing": "What are you currently studying or pursuing?",
    "existing": "Do you have any existing benefits or schemes?",
    "previous": "Have you applied for this before?",
    "covered": "Are you covered under any government scheme?",
    "deceased": "Is the applicant deceased?",
    "family": "What is your family status?",
    "artist": "Are you an artist?",
    "goan": "Are you from Goa?",
    "indian": "Are you an Indian citizen?",
    "attending": "Are you currently attending school or college?",
    "author": "Are you an author or writer?",
    "certified": "Do you have any certification?",
    "currently": "What is your current status?",
    "defaulter": "Are you a defaulter?",
    "holding": "Are you holding any position?",
    "institution": "Are you associated with any institution?",
    "livestock": "Do you have livestock?",
    "msme": "Are you registered under MSME?",
    "promoted": "Are you promoted?",
    "recognized": "Are you recognized?",
    "research": "Are you a researcher?",
    "retired": "Are you retired?",
    "scholar": "Are you a scholar?",
    "service": "Are you in service?",
    "victim": "Are you a victim of anything?",
    "voluntary": "Are you a volunteer?",
    "agriculture": "Are you in agriculture?",
    "already": "Have you already applied?",
    "associated": "Are you associated with any organization?",
    "continuing": "Are you continuing your studies?",
    "credit": "Do you have credit facilities?",
    "cured": "Have you been cured?",
    "death": "Is there any death in family?",
    "destitute": "Are you destitute?",
    "dowry": "Are you against dowry?",
    "dropout": "Are you a school dropout?",
    "handloom": "Are you a handloom worker?",
    "hearing": "Do you have hearing impairment?",
    "hiv": "Are you HIV positive?",
    "independent": "Are you independent?",
    "indigent": "Are you indigent?",
    "industry": "Are you in industry?",
    "international": "Are you involved in international work?",
    "journalist": "Are you a journalist?",
    "khadi": "Are you a khadi worker?",
    "legal": "Do you have any legal issues?",
    "listed": "Are you listed in any registry?",
    "local": "Are you a local resident?",
    "mega": "Are you in mega industry?",
    "ngo": "Are you from an NGO?",
    "posthumous": "Is it a posthumous award?",
    "primary": "Are you a primary applicant?",
    "repeating": "Are you repeating the course?",
    "scientist": "Are you a scientist?",
    "small": "Are you in small scale industry?",
    "suffering": "Are you suffering from any condition?",
    "teacher": "Are you a teacher?",
    "working": "Are you currently working?",
    "youth": "Are you a youth?",
    "other": "Any other relevant status?",
}

# Process all concepts
q_registry = {}
updated = 0

for i, item in enumerate(concepts):
    concept = item['concept']
    
    # Use mapped question or fallback
    if concept in q_map:
        new_q = q_map[concept]
    else:
        new_q = f"What is your {concept.replace('_', ' ')}?"
    
    # Check duplicates
    norm = normalize(new_q)
    if norm in q_registry:
        new_q = q_registry[norm]
    else:
        q_registry[norm] = new_q
    
    item['question'] = new_q
    updated += 1
    
    if (i+1) % 20 == 0:
        print(f"Processed {i+1}/{len(concepts)}")

print(f"\nUpdated {updated} concepts")

# Save
with open('concept_registry.json', 'w', encoding='utf-8') as f:
    json.dump(registry, f, indent=2, ensure_ascii=False)

print("Saved to concept_registry.json")

# Samples
print("\n" + "=" * 60)
print("SAMPLE 15 CONCEPTS + QUESTIONS:")
print("=" * 60)
for c in concepts[:15]:
    print(f"\n{c['concept']}: {c['question'][:50]}")

print(f"\nTotal: {len(concepts)} concepts")