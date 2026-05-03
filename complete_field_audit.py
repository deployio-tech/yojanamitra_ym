"""
COMPLETE PROFILE FORM FIELD AUDIT
==================================

Get ALL profile form fields from User model
Compare with questions being asked
Remove ANY overlap - questions should ONLY ask what's NOT in profile
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Scheme, User
from app.engine.eligibility import EligibilityEngine
from app.engine.questions import QuestionEngine

print("\n" + "=" * 140)
print("COMPLETE AUDIT: PROFILE FORM FIELDS vs QUESTIONS")
print("=" * 140)

# ========================================
# STEP 1: Get ALL User model fields
# ========================================
print("\n[STEP 1] Reading all User model columns...")

all_user_columns = {c.name for c in User.__table__.columns}

# Filter out system/metadata columns
system_cols = {'id', 'created_at', 'password_hash', 'email', 'verified_schemes_data', 'verified_scheme_ids', 'profile_version'}
profile_form_fields = sorted(all_user_columns - system_cols)

print(f"\n✅ Found {len(profile_form_fields)} profile form fields in User model:")
for i, field in enumerate(profile_form_fields, 1):
    print(f"   {i:2d}. {field}")

# ========================================
# STEP 2: Get questions being asked
# ========================================
print("\n" + "=" * 140)
print("[STEP 2] Reading questions being asked...")
print("=" * 140)

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
    
    asked_fields = sorted({q.field for q in questions})
    
    print(f"\n✅ Found {len(asked_fields)} fields being asked as questions:")
    for i, field in enumerate(asked_fields, 1):
        print(f"   {i:2d}. {field}")
    
    # ========================================
    # STEP 3: Find overlap (PROBLEMATIC!)
    # ========================================
    print("\n" + "=" * 140)
    print("[STEP 3] OVERLAP ANALYSIS")
    print("=" * 140)
    
    # Map question field names to profile field names
    # Some field names differ slightly between conditions and profile
    field_mapping = {
        # Direct matches
        'age': 'age',
        'state': 'state',
        'gender': 'gender',
        'occupation': 'occupation',
        'education': 'education',
        'marital_status': 'marital_status',
        'disability': 'disability',
        'residence': 'residence',
        'caste': 'caste',
        'income': 'income',
        'religion': 'religion',
        'is_farmer': 'is_farmer',
        'is_pensioner': 'is_pensioner',
        'is_tribal': 'is_tribal',
        'is_orphan': 'is_orphan',
        'is_self_employed': 'is_self_employed',
        'is_construction_worker': 'is_bocw_registered',
        'is_school_dropout': 'is_school_dropout',
        'is_first_gen_student': 'is_first_gen_student',
        'is_landless': 'is_landless',
        'has_pucca_house': 'has_pucca_house',
        'is_bocw_registered': 'is_bocw_registered',
        
        # Alternative/related names
        'education_level': 'highest_education_level',
        'is_disabled': 'disability',
        'is_rural': 'residence',
        'is_urban': 'residence',
        'annual_income': 'annual_family_income',  # or income
        'bank_account': 'bank_account_available',
        'has_bank_account': 'bank_account_available',
        'is_student': 'education_status',
        'is_minority': 'minority_status',
        'is_bpl': 'ration_card_type',
        'disability_percentage': 'disability_percentage',
        
        # New profile form fields
        'is_citizen': 'is_citizen',
        'is_urban': 'is_urban',
        'has_bank_account': 'has_bank_account',
        'residence_type': 'residence_type',
        
        # Fields NOT in profile (OK to ask)
        'category': None,  # This is like caste but could be different
        'citizenship': None,  # New field, might not be 'is_citizen'
        'loan_default_history': None,  # Not in profile
    }
    
    overlap_found = []
    for q_field in asked_fields:
        mapped_profile_field = field_mapping.get(q_field)
        if mapped_profile_field and mapped_profile_field in profile_form_fields:
            overlap_found.append((q_field, mapped_profile_field))
    
    if overlap_found:
        print(f"\n🔴 OVERLAPS FOUND ({len(overlap_found)}):")
        print(f"\nQuestions asking for fields already in profile form:")
        for q_field, p_field in sorted(overlap_found):
            print(f"   ❌ {q_field:<30} → already in profile as: {p_field}")
    else:
        print(f"\n✅ No overlaps found (all questions are for non-profile fields)")
    
    # ========================================
    # STEP 4: What questions SHOULD be asked
    # ========================================
    print("\n" + "=" * 140)
    print("[STEP 4] RECOMMENDED QUESTIONS (Non-profile fields only)")
    print("=" * 140)
    
    safe_to_ask = []
    cannot_ask = []
    
    for q_field in asked_fields:
        mapped_profile_field = field_mapping.get(q_field)
        if mapped_profile_field and mapped_profile_field in profile_form_fields:
            cannot_ask.append((q_field, mapped_profile_field))
        else:
            safe_to_ask.append(q_field)
    
    print(f"\n✅ SAFE TO ASK AS QUESTIONS ({len(safe_to_ask)}):")
    for field in sorted(safe_to_ask):
        print(f"   • {field}")
    
    print(f"\n❌ SHOULD NOT ASK - ALREADY IN PROFILE ({len(cannot_ask)}):")
    for q_field, p_field in sorted(cannot_ask):
        print(f"   • {q_field:<25} (use profile field: {p_field})")
    
    # ========================================
    # STEP 5: Missing fields analysis
    # ========================================
    print("\n" + "=" * 140)
    print("[STEP 5] MISSING FIELDS ANALYSIS")
    print("=" * 140)
    
    all_condition_fields = set()
    for scheme, _ in possible_schemes:
        for cond in scheme.conditions:
            all_condition_fields.add(cond.field)
    
    # Fields needed but not in profile and not being asked
    missing_completely = set()
    for cond_field in all_condition_fields:
        in_profile = cond_field in profile_form_fields
        being_asked = cond_field in asked_fields
        
        if not in_profile and not being_asked:
            # Check if there's a mapping
            has_mapping = field_mapping.get(cond_field) and field_mapping.get(cond_field) in profile_form_fields
            if not has_mapping:
                missing_completely.add(cond_field)
    
    print(f"\n⚠️  Fields needed by schemes but NOT in profile and NOT asked ({len(missing_completely)}):")
    for field in sorted(missing_completely):
        print(f"   • {field}")
    
    # ========================================
    # STEP 6: Recommendation
    # ========================================
    print("\n" + "=" * 140)
    print("[STEP 6] FINAL RECOMMENDATION")
    print("=" * 140)
    
    print(f"""
📋 CURRENT STATE:

Profile Form Fields: {len(profile_form_fields)}
Questions Being Asked: {len(asked_fields)}
Overlaps (PROBLEM): {len(cannot_ask)}

🎯 RECOMMENDED ACTION:

1. REMOVE {len(cannot_ask)} questions that ask for profile fields:
""")
    for q_field, p_field in sorted(cannot_ask):
        print(f"   ❌ {q_field:<25} → Use profile.{p_field} instead")
    
    print(f"""
2. KEEP {len(safe_to_ask)} questions for non-profile fields:
""")
    for field in sorted(safe_to_ask):
        print(f"   ✅ {field}")
    
    print(f"""
3. ADD these fields to profile form (if missing):
""")
    for field in sorted(missing_completely):
        print(f"   ✏️  Add to profile: {field}")
    
    print(f"""

FINAL RESULT:
• Profile form as SOURCE OF TRUTH for {len(profile_form_fields)} core fields
• Questions ask ONLY for {len(safe_to_ask)} additional clarifications
• No redundancy, no duplication
• Engine uses profile for all {len(profile_form_fields)} + questions for {len(safe_to_ask)} = {len(profile_form_fields) + len(safe_to_ask)} total context

✅ CLEAR SEPARATION OF CONCERNS:
   Profile Form: Baseline info user fills once
   Questions: Scheme-specific clarifications asked on-demand
""")

print("=" * 140)
