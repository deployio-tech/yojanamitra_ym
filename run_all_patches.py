"""
run_all_patches.py
==================
Run this single script from your backend folder to apply ALL patches:

    python run_all_patches.py

What it does (in order):
  1. Patches app.py  — inserts new db.Column lines into User class
  2. Patches app.py  — inserts new fields into save_profile() route
  3. Runs DB migration — ALTERs the user table to add new columns
"""

import sys, shutil, subprocess
from pathlib import Path

APP_PY = Path('app.py')

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Insert new db.Column lines into User class
# ─────────────────────────────────────────────────────────────────────────────

COLUMN_ANCHOR = "    career_goal = db.Column(db.String(100))"

NEW_COLUMNS = '''
    # ── NEW PROFILE FIELDS (generated from new_profile_fields.json) ──────────

    # Financial
    annual_family_income_v2         = db.Column(db.Integer)
    is_bpl_v2                       = db.Column(db.String(10))
    has_bank_account_v2             = db.Column(db.String(10))

    # Personal / Demographics
    social_category                 = db.Column(db.String(80))
    date_of_birth_v2                = db.Column(db.String(20))
    gender_v2                       = db.Column(db.String(20))
    marital_status_v2               = db.Column(db.String(30))

    # Disability
    disability_details              = db.Column(db.Text)

    # Employment / Occupation
    employment_status_v2            = db.Column(db.String(50))
    occupation_type                 = db.Column(db.String(80))

    # Land
    land_ownership_details          = db.Column(db.Text)

    # Family
    family_members_v2               = db.Column(db.Text)

    # Education
    education_details               = db.Column(db.Text)

    # Residency
    state_of_domicile               = db.Column(db.String(80))
    residence_location_type         = db.Column(db.String(20))
    years_in_current_state          = db.Column(db.Integer)

    # Special categories
    is_ex_serviceman_or_dependent   = db.Column(db.String(10))
    is_shg_member                   = db.Column(db.String(10))
    is_freedom_fighter_or_dependent = db.Column(db.String(10))

    # Health
    has_critical_illness            = db.Column(db.String(10))
    is_pregnant                     = db.Column(db.String(10))
    is_lactating_mother             = db.Column(db.String(10))

    # ── END NEW PROFILE FIELDS ───────────────────────────────────────────────
'''

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Insert new field saves into save_profile() route
# ─────────────────────────────────────────────────────────────────────────────

PROFILE_ANCHOR = "        db.session.commit()\n        return jsonify({'message': 'Profile updated', 'user': user.to_dict()}), 200"

NEW_PROFILE_SAVES = '''
        # ── NEW PROFILE FIELDS ────────────────────────────────────────────────

        # Financial
        user.annual_family_income_v2   = safe_int(data.get('annualFamilyIncome'))
        user.is_bpl_v2                 = data.get('isBpl')
        user.has_bank_account_v2       = data.get('hasBankAccount')

        # Personal / Demographics
        user.social_category           = data.get('socialCategory')
        user.date_of_birth_v2          = data.get('dateOfBirth')
        user.gender_v2                 = data.get('gender')
        user.marital_status_v2         = data.get('maritalStatus')

        # Disability details (JSON list)
        disability_details_raw = data.get('disabilityDetails')
        if disability_details_raw is not None:
            if isinstance(disability_details_raw, list):
                user.disability_details = json.dumps(disability_details_raw)
            elif isinstance(disability_details_raw, str):
                user.disability_details = disability_details_raw
            if isinstance(disability_details_raw, list) and disability_details_raw:
                first_pct = disability_details_raw[0].get('disability_percentage')
                if first_pct and not user.disability_percentage:
                    user.disability_percentage = safe_int(first_pct)

        # Employment / Occupation
        user.employment_status_v2      = data.get('employmentStatus')
        user.occupation_type           = data.get('occupationTypeNew')

        # Land ownership (JSON list)
        land_raw = data.get('landOwnershipDetails')
        if land_raw is not None:
            if isinstance(land_raw, list):
                user.land_ownership_details = json.dumps(land_raw)
            elif isinstance(land_raw, str):
                user.land_ownership_details = land_raw
            if isinstance(land_raw, list):
                total_ag = sum(
                    float(p.get('area_in_acres') or 0)
                    for p in land_raw
                    if str(p.get('land_type', '')).lower() == 'agricultural'
                )
                if total_ag > 0 and not user.land_size_acres:
                    user.land_size_acres = total_ag

        # Family members (JSON list)
        family_raw = data.get('familyMembers')
        if family_raw is not None:
            if isinstance(family_raw, list):
                user.family_members_v2 = json.dumps(family_raw)
            elif isinstance(family_raw, str):
                user.family_members_v2 = family_raw
            if isinstance(family_raw, list):
                daughters = [m for m in family_raw
                             if str(m.get('relation', '')).lower() == 'daughter'
                             and m.get('is_alive', True)]
                user.num_daughters = len(daughters)
                parents_alive = [m for m in family_raw
                                 if str(m.get('relation', '')).lower() in ('father', 'mother')
                                 and m.get('is_alive', True)]
                user.is_orphan = 'Yes' if len(parents_alive) == 0 else 'No'

        # Education details (JSON list)
        edu_raw = data.get('educationDetails')
        if edu_raw is not None:
            if isinstance(edu_raw, list):
                user.education_details = json.dumps(edu_raw)
            elif isinstance(edu_raw, str):
                user.education_details = edu_raw
            if isinstance(edu_raw, list) and edu_raw:
                _level_order = ['Below Class 10','Class 10','Class 12','Diploma',
                                'Graduation','Post Graduation','PhD','Other']
                completed = [e for e in edu_raw if e.get('status') in ('Completed','Pursuing')]
                if completed:
                    highest = max(completed, key=lambda e: _level_order.index(e.get('education_level','Other'))
                                  if e.get('education_level','') in _level_order else -1)
                    user.highest_education_level = highest.get('education_level')
                    user.education_status        = highest.get('status')
                    user.institution_type        = highest.get('institute_type')

        # Residency
        user.state_of_domicile         = data.get('stateOfDomicile')
        user.residence_location_type   = data.get('residenceLocationType')
        user.years_in_current_state    = safe_int(data.get('yearsInCurrentState'))

        # Special categories
        user.is_ex_serviceman_or_dependent   = data.get('isExServicemanOrDependent')
        user.is_shg_member                   = data.get('isShgMember')
        user.is_freedom_fighter_or_dependent = data.get('isFreedomFighterOrDependent')

        # Health
        user.has_critical_illness      = data.get('hasCriticalIllness')
        user.is_pregnant               = data.get('isPregnant')
        user.is_lactating_mother       = data.get('isLactatingMother')

        # ── BACK-FILL LEGACY COLUMNS ──────────────────────────────────────────
        if user.annual_family_income_v2 is not None:
            user.annual_family_income = user.annual_family_income_v2
            user.income               = user.annual_family_income_v2
        if user.is_bpl_v2 == 'Yes' and not user.ration_card_type:
            user.ration_card_type = 'BPL'
        elif user.is_bpl_v2 == 'No' and not user.ration_card_type:
            user.ration_card_type = 'APL'
        if user.has_bank_account_v2:
            user.bank_account_available = user.has_bank_account_v2
        if user.gender_v2:
            user.gender = user.gender_v2
        if user.marital_status_v2:
            user.marital_status = user.marital_status_v2
        if user.state_of_domicile:
            user.state = user.state_of_domicile
        if user.residence_location_type:
            user.residence = user.residence_location_type.lower()
        if user.employment_status_v2:
            user.employment_status = user.employment_status_v2
        if user.occupation_type and 'farmer' in user.occupation_type.lower():
            user.is_farmer = 'Yes'
        if user.occupation_type == 'Construction Worker' and not user.is_bocw_registered:
            user.is_bocw_registered = 'Yes'
        if user.social_category == 'Minority':
            user.minority_status = 'Yes'
        if user.social_category == 'Economically Weaker Section (EWS)':
            user.ews_status = 'Yes'
        _CASTE_MAP = {
            'Scheduled Caste (SC)': 'SC',
            'Scheduled Tribe (ST)': 'ST',
            'Other Backward Class (OBC) - Non-Creamy Layer': 'OBC',
            'Other Backward Class (OBC) - Creamy Layer': 'OBC',
            'Economically Weaker Section (EWS)': 'General',
            'General': 'General',
            'Minority': 'General',
            'Denotified/Nomadic/Semi-Nomadic Tribes (DNT/NT/SNT)': 'ST',
        }
        if user.social_category and not user.caste:
            user.caste = _CASTE_MAP.get(user.social_category, user.social_category)
        if user.marital_status_v2 in ('Widow/Widower', 'Divorced', 'Separated'):
            if not user.is_widow_single_woman:
                user.is_widow_single_woman = 'Yes'
        if user.date_of_birth_v2 and not user.dob:
            user.dob = user.date_of_birth_v2
        # ── END NEW PROFILE FIELDS ────────────────────────────────────────────
'''

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — DB Migration: ALTER TABLE to add the new columns
# ─────────────────────────────────────────────────────────────────────────────

NEW_DB_COLUMNS = [
    ("annual_family_income_v2",         "INTEGER"),
    ("is_bpl_v2",                       "VARCHAR(10)"),
    ("has_bank_account_v2",             "VARCHAR(10)"),
    ("social_category",                 "VARCHAR(80)"),
    ("date_of_birth_v2",                "VARCHAR(20)"),
    ("gender_v2",                       "VARCHAR(20)"),
    ("marital_status_v2",               "VARCHAR(30)"),
    ("disability_details",              "TEXT"),
    ("employment_status_v2",            "VARCHAR(50)"),
    ("occupation_type",                 "VARCHAR(80)"),
    ("land_ownership_details",          "TEXT"),
    ("family_members_v2",               "TEXT"),
    ("education_details",               "TEXT"),
    ("state_of_domicile",               "VARCHAR(80)"),
    ("residence_location_type",         "VARCHAR(20)"),
    ("years_in_current_state",          "INTEGER"),
    ("is_ex_serviceman_or_dependent",   "VARCHAR(10)"),
    ("is_shg_member",                   "VARCHAR(10)"),
    ("is_freedom_fighter_or_dependent", "VARCHAR(10)"),
    ("has_critical_illness",            "VARCHAR(10)"),
    ("is_pregnant",                     "VARCHAR(10)"),
    ("is_lactating_mother",             "VARCHAR(10)"),
]

# ─────────────────────────────────────────────────────────────────────────────

def step1_patch_user_model(src):
    if 'annual_family_income_v2' in src:
        print("  [SKIP] User model columns already present.")
        return src, False
    if COLUMN_ANCHOR not in src:
        print(f"  [ERROR] Could not find anchor:\n    {COLUMN_ANCHOR}")
        print("  Manually paste NEW_COLUMNS after the last db.Column in the User class.")
        return src, False
    patched = src.replace(COLUMN_ANCHOR, COLUMN_ANCHOR + NEW_COLUMNS, 1)
    print("  [OK] New db.Column lines inserted into User class.")
    return patched, True


def step2_patch_save_profile(src):
    if 'annual_family_income_v2' in src and '# ── NEW PROFILE FIELDS' in src:
        print("  [SKIP] save_profile() patch already present.")
        return src, False
    if PROFILE_ANCHOR not in src:
        print(f"  [ERROR] Could not find save_profile anchor.")
        print("  Manually paste NEW_PROFILE_SAVES before db.session.commit() in save_profile().")
        return src, False
    patched = src.replace(PROFILE_ANCHOR, NEW_PROFILE_SAVES + PROFILE_ANCHOR, 1)
    print("  [OK] New field saves inserted into save_profile().")
    return patched, True


def step3_db_migration():
    import os
    from dotenv import load_dotenv
    load_dotenv()

    # Import after app.py is already patched
    from app import app, db
    from sqlalchemy import text

    db_url = os.getenv('DATABASE_URL', 'sqlite:///yojanamitra.db')
    is_pg  = db_url.startswith('postgres')

    added   = []
    skipped = []

    with app.app_context():
        with db.engine.connect() as conn:
            for col_name, col_type in NEW_DB_COLUMNS:
                try:
                    tbl = '"user"' if is_pg else 'user'
                    conn.execute(text(f'ALTER TABLE {tbl} ADD COLUMN {col_name} {col_type};'))
                    conn.commit()
                    added.append(col_name)
                    print(f"  [OK]   Added   : {col_name}")
                except Exception as e:
                    conn.rollback()
                    if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
                        skipped.append(col_name)
                        print(f"  [SKIP] Exists  : {col_name}")
                    else:
                        print(f"  [ERR]  {col_name}: {e}")
                        raise

    print(f"\n  Added {len(added)} column(s), skipped {len(skipped)} existing.")


# ─────────────────────────────────────────────────────────────────────────────

def main():
    if not APP_PY.exists():
        print("ERROR: app.py not found. Run this from your backend folder.")
        sys.exit(1)

    # Backup
    backup = Path('app.py.bak')
    shutil.copy(APP_PY, backup)
    print(f"Backup created: {backup}\n")

    src = APP_PY.read_text(encoding='utf-8')

    print("── Step 1: Patch User model columns ─────────────────────────")
    src, _ = step1_patch_user_model(src)

    print("\n── Step 2: Patch save_profile() route ───────────────────────")
    src, _ = step2_patch_save_profile(src)

    APP_PY.write_text(src, encoding='utf-8')
    print("\napp.py saved.\n")

    print("── Step 3: Run DB migration ──────────────────────────────────")
    step3_db_migration()

    print("\n✅  All patches applied. You can now restart your Flask server.")


if __name__ == '__main__':
    main()
