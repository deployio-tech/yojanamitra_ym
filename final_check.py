import os
import json
from types import SimpleNamespace
from eligibility_engine_strict_v21 import StrictEligibilityEngine, UserProfile
from scheme_rule_adapter import build_rule

# Mock user data from DB for shreyas6504@gmail.com
user = UserProfile(
    user_id="shreyas6504@gmail.com",
    age=21,
    gender="Male",
    state="KA",
    income_annual=0,
    occupation=["Student"],
    caste_category="general",
    residence="urban",
    is_disabled=False,
    is_senior_citizen=False,
    is_minority=False,
    is_widow=False
)

engine = StrictEligibilityEngine()

# Test schemes that Gemini said "FULLY_ELIGIBLE"
test_schemes = [
    {"id": 1, "name": "Pradhan Mantri Jeevan Jyoti Bima Yojana (PMJJBY)", "min_age": 18, "max_age": 50, "eligibility": "18-50 years, bank account"},
    {"id": 2, "name": "Pradhan Mantri Suraksha Bima Yojana (PMSBY)", "min_age": 18, "max_age": 70, "eligibility": "18-70 years, bank account"},
    {"id": 3, "name": "Atal Pension Yojana (APY)", "min_age": 18, "max_age": 40, "eligibility": "18-40 years, bank account"}
]

print("--- Engine Verification (Deterministic) ---")
for s_dict in test_schemes:
    # mock the SQLAlchemy object
    s = SimpleNamespace(**s_dict)
    # Ensure all required attributes for build_rule are present
    s.description = ""
    s.exclusions = ""
    s.allowed_states = json.dumps(["All India"])
    s.allowed_genders = json.dumps(["All"])
    s.allowed_occupations = json.dumps([])
    s.allowed_castes = json.dumps([])
    s.disability_requirement = "Any"
    s.minority_requirement = "Any"
    s.senior_citizen_requirement = "Any"
    s.widow_requirement = "Any"
    s.min_income = None
    s.max_income = None
    
    rule = build_rule(s)
    result = engine.evaluate(user, rule)
    print(f"Scheme: {s.name}")
    print(f"Result: {result.eligibility_class}")
    print(f"Detail: {result.rejection_detail}")
    print("-" * 20)
