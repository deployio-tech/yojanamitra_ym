"""
COMPLETE GLOBAL FIELD ANALYSIS
================================
1. Get ALL condition fields from ALL schemes (not user-specific)
2. Remove ALL 67 profile form fields (irrelevant of user)
3. Count unmapped/missing fields
4. Count unique questions after deduplication and grouping
"""

import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Scheme
from app.engine.eligibility import get_canonical_field

print("\n" + "=" * 160)
print("COMPLETE GLOBAL FIELD ANALYSIS - SCHEME REQUIREMENTS vs PROFILE FORM")
print("=" * 160)

# ========================================
# STEP 1: Profile Form Fields (67 fields)
# ========================================
profile_form_fields = {
    'age', 'gender', 'occupation', 'income', 'caste', 'state', 'education', 
    'marital_status', 'disability', 'residence',
    'dob', 'aadhaar_available', 'district', 'block_taluk', 'domicile_status',
    'family_type', 'total_family_members', 'is_head_of_family', 'annual_family_income',
    'income_slab', 'income_certificate_available', 'achievement_certificates', 'sub_caste',
    'minority_status', 'ews_status', 'ration_card_available', 'ration_card_type',
    'education_status', 'highest_education_level', 'current_course', 'institution_type',
    'employment_status', 'govt_employee_in_family', 'is_farmer', 'own_agricultural_land',
    'land_size_acres', 'is_tenant_farmer', 'disability_percentage', 'is_widow_single_woman',
    'is_senior_citizen', 'bank_account_available', 'aadhaar_linked_bank', 'mobile_linked_bank',
    'income_cert_last_1_year', 'scheme_previously_availed', 'willing_to_submit_docs',
    'documents_available', 'has_pucca_house', 'house_type', 'is_bocw_registered', 'is_pensioner',
    'is_school_dropout', 'is_first_gen_student', 'is_landless', 'num_daughters',
    'father_occupation', 'mother_occupation', 'religion', 'land_type', 'is_orphan', 'is_tribal',
    'child_age', 'career_goal', 'education_milestones',
    'name', 'email', 'mobile'
}

print(f"\n📋 PROFILE FORM: {len(profile_form_fields)} fields")
print("=" * 160)

# ========================================
# STEP 2: Collect ALL condition fields from ALL schemes (GLOBAL)
# ========================================
print("\n🔍 STEP 1: Collecting ALL condition fields from ALL schemes...")
print("-" * 160)

with app.app_context():
    all_schemes = Scheme.query.all()
    print(f"   Total schemes in database: {len(all_schemes)}")
    
    # Collect ALL condition fields
    all_condition_fields = defaultdict(lambda: {
        'count': 0,  # How many schemes use this field
        'schemes': set(),
        'condition_types': set(),
        'canonical': None
    })
    
    for scheme in all_schemes:
        for cond in scheme.conditions:
            field = cond.field
            canonical = get_canonical_field(field)
            
            all_condition_fields[field]['count'] += 1
            all_condition_fields[field]['schemes'].add(scheme.id)
            all_condition_fields[field]['condition_types'].add(getattr(cond, 'condition_type', 'unknown'))
            all_condition_fields[field]['canonical'] = canonical
    
    print(f"   Total unique condition fields across all schemes: {len(all_condition_fields)}")
    
    # ========================================
    # STEP 3: Categorize fields
    # ========================================
    print("\n" + "=" * 160)
    print("FIELD CATEGORIZATION")
    print("=" * 160)
    
    in_profile = {}
    not_in_profile = {}
    
    for field_name, data in all_condition_fields.items():
        if field_name in profile_form_fields:
            in_profile[field_name] = data
        else:
            not_in_profile[field_name] = data
    
    print(f"\n✅ Fields IN profile form: {len(in_profile)}")
    print(f"❌ Fields NOT IN profile form (need to ask or handle): {len(not_in_profile)}")
    
    # ========================================
    # STEP 4: Show IN PROFILE fields
    # ========================================
    print(f"\n{'FIELDS IN PROFILE FORM':<50} | {'Schemes':<10} | {'Type':<20}")
    print("-" * 160)
    
    for field in sorted(in_profile.keys()):
        data = in_profile[field]
        schemes_count = len(data['schemes'])
        cond_types = ', '.join(sorted(data['condition_types']))
        print(f"{field:<50} | {schemes_count:<10} | {cond_types:<20}")
    
    # ========================================
    # STEP 5: Show NOT IN PROFILE fields (detailed)
    # ========================================
    print(f"\n" + "=" * 160)
    print(f"FIELDS NOT IN PROFILE - NEED TO HANDLE ({len(not_in_profile)} fields)")
    print("=" * 160)
    
    print(f"\n{'Field Name':<50} | {'Canonical':<30} | {'Schemes':<10} | {'Type':<20}")
    print("-" * 160)
    
    for field in sorted(not_in_profile.keys()):
        data = not_in_profile[field]
        schemes_count = len(data['schemes'])
        cond_types = ', '.join(sorted(data['condition_types']))
        canonical = data['canonical']
        print(f"{field:<50} | {canonical:<30} | {schemes_count:<10} | {cond_types:<20}")
    
    # ========================================
    # STEP 6: Group NOT IN PROFILE by canonical field
    # ========================================
    print(f"\n" + "=" * 160)
    print(f"GROUPING BY CANONICAL FIELD (Deduplication)")
    print("=" * 160)
    
    canonical_groups = defaultdict(lambda: {
        'fields': set(),
        'schemes': set(),
        'count': 0
    })
    
    for field_name, data in not_in_profile.items():
        canonical = data['canonical']
        canonical_groups[canonical]['fields'].add(field_name)
        canonical_groups[canonical]['schemes'].update(data['schemes'])
        canonical_groups[canonical]['count'] += 1
    
    total_unique_questions = len(canonical_groups)
    total_fields_to_handle = len(not_in_profile)
    total_schemes_using_unmapped = sum(len(data['schemes']) for data in not_in_profile.values())
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total fields NOT in profile: {total_fields_to_handle}")
    print(f"   Total unique canonical fields (after dedup): {total_unique_questions}")
    print(f"   Total scheme instances using these fields: {total_schemes_using_unmapped}")
    
    print(f"\n{'Canonical Field':<50} | {'# Fields':<10} | {'# Schemes':<10}")
    print("-" * 160)
    
    for canonical in sorted(canonical_groups.keys()):
        data = canonical_groups[canonical]
        variant_count = len(data['fields'])
        scheme_count = len(data['schemes'])
        print(f"{canonical:<50} | {variant_count:<10} | {scheme_count:<10}")
    
    # ========================================
    # STEP 7: Estimate questions to be formed
    # ========================================
    print(f"\n" + "=" * 160)
    print("QUESTION FORMATION ESTIMATE")
    print("=" * 160)
    
    print(f"\n📝 Questions to be formed from NOT-in-profile fields: {total_unique_questions}")
    
    print(f"\n   These questions will ask about:")
    for i, canonical in enumerate(sorted(canonical_groups.keys()), 1):
        data = canonical_groups[canonical]
        variants = sorted(data['fields'])
        scheme_count = len(data['schemes'])
        print(f"\n   {i:2d}. {canonical}")
        print(f"       Variants: {', '.join(variants[:5])}")
        if len(variants) > 5:
            print(f"                 + {len(variants)-5} more variants")
        print(f"       Affects: {scheme_count} schemes")
    
    # ========================================
    # FINAL SUMMARY
    # ========================================
    print(f"\n" + "=" * 160)
    print("FINAL SUMMARY")
    print("=" * 160)
    
    print(f"""
╔════════════════════════════════════════════╗
║           FIELD DISTRIBUTION              ║
╠════════════════════════════════════════════╣
║                                            ║
║  Profile Form            :   {len(profile_form_fields):3d} fields
║                                            ║
║  Total Condition Fields  :   {len(all_condition_fields):3d} fields
║    ├─ In Profile         :   {len(in_profile):3d} fields  ✅
║    └─ Not in Profile     :   {len(not_in_profile):3d} fields  ❌
║                                            ║
║  QUESTIONS TO BE FORMED  :   {total_unique_questions:3d} questions
║                                            ║
║  ANSWER: After deduplication and          ║
║  combining into unique questions,         ║
║  {total_unique_questions} distinct questions            ║
║  will be asked to users.                  ║
║                                            ║
╚════════════════════════════════════════════╝
""")
    
    print(f"\n📌 BREAKDOWN:")
    print(f"   • {len(profile_form_fields)} profile fields → User provides via form")
    print(f"   • {len(in_profile)} scheme fields → Already covered by profile")
    print(f"   • {len(not_in_profile)} additional fields needed → To be asked as questions")
    print(f"   • {total_unique_questions} unique question groups → After combining variants")
    print(f"\n   Total data collected per user: {len(profile_form_fields)} (profile) + {total_unique_questions} (questions) = {len(profile_form_fields) + total_unique_questions} fields")

print("\n" + "=" * 160)
