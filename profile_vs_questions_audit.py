"""
PROFILE FORM vs QUESTIONS AUDIT
================================

Identify which fields are:
1. In profile form only (should NOT be asked as questions)
2. Being asked as questions (check if they're already in profile)
3. Missing from both (need to add to profile OR questions)
"""

import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Scheme
from app.engine.eligibility import EligibilityEngine
from app.engine.questions import QuestionEngine

print("\n" + "=" * 140)
print("PROFILE FORM vs QUESTIONS ANALYSIS")
print("=" * 140)

# ========================================
# PART 1: Get profile form fields
# ========================================
print("\n" + "-" * 140)
print("PART 1: FIELDS IN PROFILE FORM")
print("-" * 140)

# These are the fields updated from the profile form (from save_profile() in app.py)
profile_form_fields = {
    # Core Demographics
    'age', 'gender', 'occupation', 'income', 'caste', 'state', 'education', 
    'marital_status', 'disability', 'residence',
    
    # Extended Details
    'dob', 'aadhaar_available', 'district', 'block_taluk', 'domicile_status',
    'family_type', 'total_family_members', 'is_head_of_family', 'annual_family_income',
    'income_slab', 'income_certificate_available', 'achievement_certificates', 'sub_caste',
    'minority_status', 'ews_status', 'ration_card_available', 'ration_card_type',
    'education_status', 'highest_education_level', 'current_course', 'institution_type',
    'employment_status', 'govt_employee_in_family', 'is_farmer', 'own_agricultural_land',
    'land_size_acres', 'is_tenant_farmer', 'disability_percentage', 'is_widow_single_woman',
    'is_senior_citizen', 'bank_account_available', 'aadhaar_linked_bank', 'mobile_linked_bank',
    'income_cert_last_1_year', 'scheme_previously_availed', 'willing_to_submit_docs',
    'documents_available',
    
    # Housing, Work & Social Status
    'has_pucca_house', 'house_type', 'is_bocw_registered', 'is_pensioner',
    'is_school_dropout', 'is_first_gen_student', 'is_landless', 'num_daughters',
    
    # Holistic Accuracy
    'father_occupation', 'mother_occupation', 'religion', 'land_type', 'is_orphan', 'is_tribal',
    
    # Predictive Forecasting
    'child_age', 'career_goal', 'education_milestones',
    
    # Auth fields
    'name', 'email', 'mobile'
}

print(f"\nTotal fields in profile form: {len(profile_form_fields)}")
print(f"\nProfile form fields:")
for i, field in enumerate(sorted(profile_form_fields), 1):
    # Convert snake_case to human readable
    readable = field.replace('_', ' ').title()
    print(f"  {i:2d}. {field:<35} ({readable})")

# ========================================
# PART 2: Get questions being asked
# ========================================
print("\n" + "-" * 140)
print("PART 2: FIELDS BEING ASKED AS QUESTIONS")
print("-" * 140)

with app.app_context():
    minimal_profile = {"age": 25, "state": "Karnataka"}
    
    engine = EligibilityEngine()
    possible_schemes = []
    schemes = Scheme.query.limit(200).all()
    
    for scheme in schemes:
        result = engine.evaluate(scheme, minimal_profile)
        if result.result.lower() == 'possible':
            possible_schemes.append((scheme, result))
    
    qengine = QuestionEngine()
    questions = qengine.select_questions(possible_schemes, minimal_profile)
    
    asked_fields = {q.field for q in questions}
    
    print(f"\nTotal fields being asked: {len(asked_fields)}")
    print(f"\nFields being asked as questions:")
    for i, field in enumerate(sorted(asked_fields), 1):
        readable = field.replace('_', ' ').title()
        # Find how many schemes this affects
        scheme_count = len([q for q in questions if q.field == field and hasattr(q, 'schemes_affected')])
        print(f"  {i:2d}. {field:<35} ({readable})")
    
    # ========================================
    # PART 3: Overlap Analysis
    # ========================================
    print("\n" + "=" * 140)
    print("OVERLAP ANALYSIS")
    print("=" * 140)
    
    # Normalize field names for comparison (snake_case vs camelCase mapping)
    profile_normalized = set()
    for f in profile_form_fields:
        profile_normalized.add(f)
    
    # Map question fields to profile field equivalents
    field_equivalents = {
        'age': 'age',
        'gender': 'gender',
        'occupation': 'occupation',
        'annual_income': 'income',  # might map to annual_family_income or income
        'education_level': 'highest_education_level',
        'education': 'education',
        'category': None,  # doesn't map to profile field
        'state': 'state',
        'citizenship': None,  # Check if maps to is_citizen fields
        'is_student': 'education_status',
        'is_farmer': 'is_farmer',
        'residence': 'residence',
        'is_urban': 'residence',  # Urban/Rural
        'is_rural': 'residence',  # Urban/Rural
        'bank_account': 'bank_account_available',
        'is_disabled': 'disability',
        'disability_percentage': 'disability_percentage',
        'is_pensioner': 'is_pensioner',
        'is_self_employed': 'employment_status',
        'marital_status': 'marital_status',
        'is_bpl': None,  # BPL status - not in profile yet
        'is_minority': 'minority_status',
        'is_construction_worker': None,  # Not in profile
        'loan_default_history': None,  # Not in profile
    }
    
    # Check overlaps
    overlap_fields = []
    for q_field in asked_fields:
        if q_field in field_equivalents:
            p_field = field_equivalents[q_field]
            if p_field and p_field in profile_form_fields:
                overlap_fields.append((q_field, p_field))
    
    print(f"\n🔴 QUESTIONS ASKING FOR PROFILE FIELDS (DUPLICATE): {len(overlap_fields)}")
    if overlap_fields:
        print(f"\nThese fields are ALREADY in profile form but being asked as questions:")
        for q_field, p_field in sorted(overlap_fields):
            print(f"  • {q_field:<30} ← already in profile as: {p_field}")
    
    # ========================================
    # PART 4: What's NOT in profile but being asked
    # ========================================
    
    new_question_fields = []
    for q_field in asked_fields:
        found_in_profile = False
        for p_field in profile_form_fields:
            if p_field in field_equivalents.values() and field_equivalents.get(q_field) == p_field:
                found_in_profile = True
                break
        if not found_in_profile:
            new_question_fields.append(q_field)
    
    print(f"\n🟢 QUESTIONS ASKING FOR NEW FIELDS (Not in profile): {len(new_question_fields)}")
    if new_question_fields:
        print(f"\nThese fields are being asked but are NOT in profile form:")
        for field in sorted(new_question_fields):
            readable = field.replace('_', ' ').title()
            print(f"  • {field:<35} ({readable})")
    
    # ========================================
    # PART 5: Scheme condition fields breakdown
    # ========================================
    print("\n" + "=" * 140)
    print("SCHEME CONDITION FIELDS - COMPLETE BREAKDOWN")
    print("=" * 140)
    
    all_condition_fields = defaultdict(lambda: {'schemes': set()})
    for scheme, _ in possible_schemes:
        for cond in scheme.conditions:
            all_condition_fields[cond.field]['schemes'].add(scheme.id)
    
    print(f"\nTotal unique condition fields needed: {len(all_condition_fields)}")
    
    in_profile_only = []
    in_questions_only = []
    in_both = []
    in_neither = []
    
    for cond_field in all_condition_fields.keys():
        in_profile = cond_field in profile_form_fields
        in_question = cond_field in asked_fields
        
        if in_profile and in_question:
            in_both.append(cond_field)
        elif in_profile and not in_question:
            in_profile_only.append(cond_field)
        elif in_question and not in_profile:
            in_questions_only.append(cond_field)
        else:
            in_neither.append(cond_field)
    
    print(f"\nCONDITION FIELD COVERAGE:")
    print(f"  ✅ In profile form ONLY: {len(in_profile_only)} fields")
    print(f"  ❓ Being asked as questions ONLY: {len(in_questions_only)} fields")
    print(f"  ⚡ In BOTH profile & questions: {len(in_both)} fields")
    print(f"  ❌ In NEITHER profile nor questions: {len(in_neither)} fields")
    
    print(f"\n[IN PROFILE ONLY] (Already available from profile form):")
    for i, field in enumerate(sorted(in_profile_only), 1):
        schemes = len(all_condition_fields[field]['schemes'])
        print(f"  {i:2d}. {field:<35} affects {schemes:2d} schemes")
    
    print(f"\n[IN QUESTIONS ONLY] (Being asked, not in profile):")
    for i, field in enumerate(sorted(in_questions_only), 1):
        schemes = len(all_condition_fields[field]['schemes'])
        print(f"  {i:2d}. {field:<35} affects {schemes:2d} schemes")
    
    print(f"\n[IN BOTH] (Redundant - being asked when already in profile):")
    for i, field in enumerate(sorted(in_both), 1):
        schemes = len(all_condition_fields[field]['schemes'])
        print(f"  {i:2d}. {field:<35} affects {schemes:2d} schemes")
    
    print(f"\n[IN NEITHER] (Missing from both profile and questions):")
    for i, field in enumerate(sorted(in_neither), 1):
        schemes = len(all_condition_fields[field]['schemes'])
        print(f"  {i:2d}. {field:<35} affects {schemes:2d} schemes")
    
    # ========================================
    # PART 6: Recommendation
    # ========================================
    print("\n" + "=" * 140)
    print("RECOMMENDATIONS")
    print("=" * 140)
    
    print(f"""
📋 CURRENT SITUATION:

Profile Form: Collects {len(profile_form_fields)} fields
Questions: Asks {len(asked_fields)} fields
Conditions Needed: {len(all_condition_fields)} unique fields

❌ PROBLEM IDENTIFIED:

Some of the questions being asked are ALREADY collected in the profile form:
  • This is redundant and wastes user time
  • Re-asking information the user already provided is poor UX
  • These fields should be fetched from profile, not asked as questions

✅ SOLUTION:

For questions, EXCLUDE any fields that are already in the profile form.

The following should NEVER be asked as questions (they're in profile):
""")
    
    if in_both:
        for field in sorted(in_both):
            print(f"  ✗ {field}")
    
    print(f"""

Focus questions ONLY on fields that are NOT in the profile form:
  • These are truly missing information
  • These need to be answered by the user

The optimal question set would be:
  • All {len(in_questions_only)} fields that are NOT in profile
  • Plus up to {len(in_neither)} fields from the 'in neither' category
  • Total: {len(in_questions_only) + len(in_neither)} high-value questions

This will avoid duplicates while maximizing coverage.
""")

print("=" * 140)
