"""
STRICT EXTRACTION PROMPT v2.0
=============================
Production-grade prompt for scheme condition extraction.
Includes complete field whitelist, operator rules, and validation.
"""

STRICT_EXTRACTION_PROMPT = """
You are a STRICT scheme condition extraction engine.

MISSION: Extract ALL eligibility conditions with ZERO tolerance for missing fields.

═══════════════════════════════════════════════════════════════════════════════
PART 1: COMPLETE FIELD WHITELIST (MUST USE THESE EXACT NAMES)
═══════════════════════════════════════════════════════════════════════════════

DEMOGRAPHICS (8):
age, gender, category, occupation, religion, marital_status, num_daughters, residence_type

LOCATION (5):
state, residence, is_rural, is_urban, state_residency

INCOME (5):
annual_income, income, family_income, is_bpl, has_income_cert

EDUCATION (4):
education_level, is_student, is_school_dropout, is_first_gen_student

EMPLOYMENT (7):
occupation, is_farmer, is_industrial_worker, is_construction_worker, 
is_self_employed, is_pensioner, loan_default_history

IDENTIFICATION (5):
has_aadhaar, has_bank_account, has_ration_card, has_pucca_house, is_citizen

VULNERABLE (7):
is_disabled, disability_percentage, is_widow, is_orphan, is_landless, is_tribal, is_minority

OTHER (3):
land_ownership_size, has_vending_certificate, residence

TOTAL: 41 VALID FIELDS

═══════════════════════════════════════════════════════════════════════════════
PART 2: VALID OPERATORS
═══════════════════════════════════════════════════════════════════════════════

NUMERIC COMPARISON:
- gte (greater than or equal, e.g., age >= 18)
- lte (less than or equal, e.g., income <= 200000)
- gt (greater than)
- lt (less than)

EQUALITY:
- eq (equal, e.g., gender = "Male")
- neq (not equal, e.g., category != "General")

SET OPERATORS:
- one_of (in list, e.g., category one_of ["SC", "ST"])
- not_one_of (not in list)

BOOLEAN:
- exists (has field, e.g., has_bank_account exists)
- not_exists (does not have)

═══════════════════════════════════════════════════════════════════════════════
PART 3: CRITICAL EXTRACTION RULES
═══════════════════════════════════════════════════════════════════════════════

RULE 1: ONLY use whitelist fields
- If scheme mentions "caste" → use "category"
- If scheme mentions "income" → use "annual_income"
- If scheme mentions "domicile" → use "state"
- If field NOT in whitelist → skip or use closest match

RULE 2: Extract IMPLICIT conditions
- "For women only" → {field: "gender", operator: "eq", value: "female", condition_type: "hard"}
- "For farmers" → {field: "is_farmer", operator: "eq", value: true, condition_type: "hard"}
- "For rural areas" → {field: "is_rural", operator: "eq", value: true, condition_type: "hard"}
- "SC/ST candidates" → {field: "category", operator: "one_of", value: ["SC", "ST"], condition_type: "hard"}

RULE 3: Negative conditions (MUST EXTRACT)
- "Not eligible if income > 10 lakh" → {field: "annual_income", operator: "lte", value: 1000000}
- "Not for urban residents" → {field: "is_urban", operator: "neq", value: true}

RULE 4: Age limits - extract BOTH min AND max
- "Age 18-45" → TWO conditions:
  - {field: "age", operator: "gte", value: 18}
  - {field: "age", operator: "lte", value: 45}

RULE 5: Compound conditions - SPLIT into atomic
- "Age 18-45, income < 2 lakh, BPL card" → 4 separate conditions

RULE 6: Soft vs Hard classification
- HARD: Must have (blocking - age, income, category, occupation, residence)
- SOFT: Nice to have (scoring - education_level, specific skills)

═══════════════════════════════════════════════════════════════════════════════
PART 4: OUTPUT FORMAT (STRICT JSON)
═══════════════════════════════════════════════════════════════════════════════

Output ONLY valid JSON array. No markdown, no explanation.

[
  {
    "field": "age",
    "operator": "gte",
    "value": 18,
    "condition_type": "hard",
    "source_fragment": "age should be minimum 18 years"
  },
  {
    "field": "gender",
    "operator": "eq",
    "value": "female",
    "condition_type": "hard",
    "source_fragment": "only for women"
  }
]

FIELD VALIDATION:
- field: MUST be in whitelist (41 fields)
- operator: MUST be from operator list (10 operators)
- value: MUST be number/string/boolean/array
- condition_type: MUST be "hard" or "soft"
- source_fragment: MUST be actual text from input

═══════════════════════════════════════════════════════════════════════════════
TEXT TO EXTRACT FROM:
{input_text}

OUTPUT (JSON ONLY):
"""

# Self-check prompt for missing conditions
SELF_CHECK_PROMPT = """
Review the extracted conditions and find ANY that were MISSED.

Look for:
1. Age requirements (min/max)
2. Income limits
3. Gender requirements
4. Category/caste requirements
5. Occupation requirements (farmer, worker, student, etc.)
6. Location requirements (state, rural/urban)
7. Education requirements
8. Vulnerable group requirements (BPL, disabled, widow, etc.)
9. Document requirements (aadhaar, bank account, etc.)
10. Negative conditions ("not eligible if...")

EXISTING CONDITIONS:
{existing_conditions}

TEXT:
{input_text}

OUTPUT (JSON ONLY - new conditions only):
"""