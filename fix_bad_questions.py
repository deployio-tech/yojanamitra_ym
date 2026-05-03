"""
FIX REMAINING BAD QUESTIONS
"""
import json

with open('concept_registry.json', 'r') as f:
    registry = json.load(f)

# Fix bad questions
fix_map = {
    "in": "Are you involved in any activity?",
    "national": "Are you involved in national work?",
    "family": "What is your family status?",
    "private": "Are you from private sector?",
    "undergoing": "Are you undergoing any training?",
    "first": "Is this your first attempt?",
    "accredited": "Are you accredited?",
    "certified": "Are you certified?",
    "attending": "Are you attending school or college?",
    "author": "Are you an author or writer?",
    "holding": "Are you holding any position?",
    "institution": "Are you affiliated with any institution?",
    "livestock": "Do you have livestock?",
    "msme": "Are you registered under MSME?",
    "promoted": "Are you a promoted candidate?",
    "recognized": "Are you recognized by government?",
    "research": "Are you a researcher?",
    "retired": "Are you retired?",
    "scholar": "Are you a scholar?",
    "service": "Are you in government service?",
    "victim": "Are you a victim of any crime or disaster?",
    "voluntary": "Are you a volunteer?",
    "agriculture": "Are you involved in agriculture?",
    "already": "Have you already applied for this?",
    "associated": "Are you associated with any organization?",
    "continuing": "Are you continuing your studies?",
    "credit": "Do you have credit/loan?",
    "cured": "Have you been cured of any disease?",
    "death": "Has any family member passed away?",
    "destitute": "Are you destitute?",
    "dowry": "Are you from a family that practices dowry?",
    "dropout": "Are you a school dropout?",
    "handloom": "Are you a handloom weaver?",
    "hearing": "Do you have hearing impairment?",
    "hiv": "Are you HIV positive?",
    "independent": "Are you self-employed?",
    "indigent": "Are you from an indigent family?",
    "industry": "Are you in manufacturing industry?",
    "international": "Are you involved in international work?",
    "journalist": "Are you a journalist?",
    "khadi": "Are you a khadi worker?",
    "legal": "Do you have any legal cases?",
    "listed": "Are you listed in any official record?",
    "local": "Are you a local resident?",
    "located": "Are you located in a specific area?",
    "mass": "Are you involved in mass programs?",
    "mega": "Are you from mega enterprise?",
    "mp": "Are you an MP?",
    "ngo": "Are you from an NGO?",
    "posthumous": "Is it a posthumous award?",
    "primary": "Are you the primary applicant?",
    "repeating": "Are you repeating the course?",
    "scientist": "Are you a scientist?",
    "small": "Are you from small scale industry?",
    "suffering": "Are you suffering from any disease?",
    "sugar": "Are you in sugar industry?",
    "tea": "Are you a tea worker?",
    "teacher": "Are you a teacher?",
    "youth": "Are you a youth?",
    "existing": "Do you have existing benefits?",
    "previous": "Have you received this before?",
    "covered": "Are you covered under any scheme?",
    "deceased": "Is the applicant deceased?",
    "goan": "Are you from Goa?",
    "indian": "Are you an Indian citizen?",
    "direct": "Are you a direct applicant?",
    "dpiit": "Are you DPIIT registered?",
    "general": "Are you from general category?",
    "listed": "Are you listed in any registry?",
    "original": "Is this an original work?",
    "physically": "Do you have physical disability?",
    "political": "Are you politically affiliated?",
    "poor": "Are you from a poor family?",
    "public": "Are you from public sector?",
    "second": "Is this your second application?",
    "working": "Are you currently working?",
    "writer": "Are you a writer?",
    "under": "Are you under any scheme?",
    "only": "Are you the only applicant?",
    "local": "Are you a local person?",
}

# Apply fixes
fixed = 0
for item in registry['concepts']:
    concept = item['concept']
    if concept in fix_map:
        item['question'] = fix_map[concept]
        fixed += 1

print(f"Fixed {fixed} questions")

# Save
with open('concept_registry.json', 'w', encoding='utf-8') as f:
    json.dump(registry, f, indent=2, ensure_ascii=False)

# Final check
print("\n" + "=" * 60)
print("FINAL SAMPLE 20:")
print("=" * 60)
for c in registry['concepts'][:20]:
    print(f"{c['concept']}: {c['question']}")

# Count bad
bad = sum(1 for c in registry['concepts'] if 'What is your' in c['question'] and len(c['question'].split()) <= 5)
print(f"\nRemaining 'What is your' questions: {bad}")