"""
analyze_unmapped_conditions.py
================================
Reads scheme_conditions.json, extracts all unmapped conditions, 
sends them to Gemini 2.5 Pro in one shot, and outputs:

  new_profile_fields.json   — ranked list of new fields to add to the profile form
  
Run: python analyze_unmapped_conditions.py

Requires: scheme_conditions.json in the same directory
          GEMINI_API_KEY set in environment or .env
"""

import json
import os
import re
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "PASTE_YOUR_GEMINI_API_KEY_HERE")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-flash-latest")

# ── Load and deduplicate unmapped conditions ──────────────────────────────────
print("[1/3] Loading scheme_conditions.json...")
with open("scheme_conditions.json", encoding="utf-8") as f:
    data = json.load(f)

all_unmapped = []
for sid, v in data.items():
    for uc in v.get("unmapped_conditions", []):
        if uc and len(uc.strip()) > 10:
            all_unmapped.append(uc.strip())

seen = set()
unique = []
for u in all_unmapped:
    k = u[:80].lower()
    if k not in seen:
        seen.add(k)
        unique.append(u)

print(f"    Total unmapped: {len(all_unmapped)}, Unique: {len(unique)}")
print(f"    Estimated tokens: ~{sum(len(u) for u in unique) // 4:,}")

# ── Build prompt ──────────────────────────────────────────────────────────────
conditions_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(unique))

PROMPT = f"""You are designing a user profile form for an Indian government scheme eligibility engine called YojanaMitra.

Below are {len(unique)} unmapped eligibility conditions extracted from 4,324 Indian government schemes. These conditions CANNOT be evaluated currently because the required profile fields don't exist yet.

YOUR TASK: Design the MINIMAL set of new profile fields that covers the MAXIMUM number of these conditions.

STRICT RULES:
1. Only fields an INDIVIDUAL APPLICANT can fill about themselves (not enterprise/NGO fields)
2. Each field must be GENERIC enough to apply across many schemes
3. Group similar conditions into ONE field (e.g. "55% in graduation" + "60% in postgraduate" = one exam_percentage field)
4. Rank fields by estimated_coverage (how many of the {len(unique)} conditions each field addresses)
5. Include ONLY fields worth implementing (coverage >= 15 conditions)
6. field_name must be snake_case, suitable as a Python variable name and HTML form input name
7. For percentage/score fields: store as float 0-100
8. For boolean fields: store as Yes/No
9. For dropdown fields: list all valid options

OUTPUT ONLY VALID JSON — no markdown, no explanation outside the JSON:
{{
  "fields": [
    {{
      "field_name": "exam_percentage",
      "label": "Percentage/Grade in Highest Qualification",
      "type": "percentage",
      "description": "Marks/percentage scored in the applicant's highest completed education degree",
      "options": null,
      "form_section": "Education",
      "show_if": "education_level >= secondary",
      "example_conditions": [
        "must have scored at least 55% in graduation",
        "minimum 60% aggregate in postgraduate degree",
        "applicant must have passed with at least 50% marks"
      ],
      "estimated_coverage": 680,
      "priority": 1
    }}
  ],
  "total_conditions_coverable": 7800,
  "uncoverable_conditions_examples": [
    "Condition that is too scheme-specific to generalize"
  ],
  "notes": "Brief explanation of key design decisions"
}}

UNMAPPED CONDITIONS FROM INDIAN GOVT SCHEMES:
{conditions_text}
"""

# ── Call Gemini 2.5 Pro ───────────────────────────────────────────────────────
print(f"\n[2/3] Sending {len(unique)} conditions to Gemini 2.5 Pro...")
print("    (This may take 30-90 seconds...)")

response = model.generate_content(
    PROMPT,
    generation_config=genai.GenerationConfig(
        temperature=0.0,
    )
)

raw = response.text.strip()
print(f"    Response received. Length: {len(raw):,} chars")

# Strip markdown fences if present
raw = re.sub(r'^```(?:json)?\s*', '', raw)
raw = re.sub(r'\s*```$', '', raw)

# Save raw response for debugging
with open("field_analysis_raw.txt", "w", encoding="utf-8") as f:
    f.write(raw)

# ── Parse and save ────────────────────────────────────────────────────────────
print("\n[3/3] Parsing response and saving output...")

try:
    result = json.loads(raw)
    fields = result.get("fields", [])
    
    # Sort by coverage descending
    fields.sort(key=lambda x: x.get("estimated_coverage", 0), reverse=True)
    result["fields"] = fields
    
    with open("new_profile_fields.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Done! Found {len(fields)} new profile fields")
    print(f"   Total conditions coverable: {result.get('total_conditions_coverable', '?')}")
    print(f"\n   TOP FIELDS BY COVERAGE:")
    for field in fields[:15]:
        print(f"   [{field.get('estimated_coverage',0):4d}] {field['field_name']:<35} — {field['label']}")
    
    print(f"\n   Output saved → new_profile_fields.json")
    print(f"   Raw response → field_analysis_raw.txt")

except json.JSONDecodeError as e:
    print(f"\n❌ JSON parse error: {e}")
    print("   Raw response saved to field_analysis_raw.txt — inspect it manually")
    print("   First 500 chars of response:")
    print(raw[:500])
