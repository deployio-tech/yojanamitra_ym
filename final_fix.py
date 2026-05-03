"""
FINAL FIX - Last 8 bad questions
"""
import json

with open('concept_registry.json', 'r') as f:
    registry = json.load(f)

final_fixes = {
    "education": "What is your highest education level?",
    "native": "What is your native state?",
    "family": "What is your family type?",
    "currently": "What is your current status?",
    "from": "Where are you from?",
    "involved": "Are you involved in any work?",
    "it": "Does it apply to you?",
    "gender": "What is your gender?",
}

for item in registry['concepts']:
    if item['concept'] in final_fixes:
        item['question'] = final_fixes[item['concept']]

with open('concept_registry.json', 'w') as f:
    json.dump(registry, f, indent=2, ensure_ascii=False)

print("Fixed 8 more")

# Final validation
bad = sum(1 for c in registry['concepts'] if 'What is your' in c['question'] and len(c['question'].split()) <= 6)
print(f"Remaining 'What is your': {bad}")

# Show all
print("\n" + "=" * 80)
print("ALL 108 CONCEPTS + QUESTIONS:")
print("=" * 80)
for c in registry['concepts']:
    print(f"{c['concept']}: {c['question']}")