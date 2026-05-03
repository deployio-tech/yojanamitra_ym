"""
PROFILE FORM — save_profile() additions
Generated from new_profile_fields.json

Paste this block inside the save_profile() route in app.py,
just before the final `db.session.commit()` call (around line 2054).

The block:
  1. Saves every new field to the User model.
  2. Back-fills the legacy columns that the eligibility engine still reads,
     so nothing breaks before you migrate the engine itself.
"""

        # ── NEW PROFILE FIELDS ────────────────────────────────────────────────

        # Financial
        user.annual_family_income_v2   = safe_int(data.get('annualFamilyIncome'))
        user.is_bpl_v2                 = data.get('isBpl')           # "Yes"/"No"
        user.has_bank_account_v2       = data.get('hasBankAccount')  # "Yes"/"No"

        # Personal / Demographics
        user.social_category           = data.get('socialCategory')
        user.date_of_birth_v2          = data.get('dateOfBirth')
        user.gender_v2                 = data.get('gender')          # "Male"/"Female"/"Transgender"
        user.marital_status_v2         = data.get('maritalStatus')

        # Disability details (JSON list)
        disability_details_raw = data.get('disabilityDetails')
        if disability_details_raw is not None:
            if isinstance(disability_details_raw, list):
                user.disability_details = json.dumps(disability_details_raw)
            elif isinstance(disability_details_raw, str):
                user.disability_details = disability_details_raw
            # Back-fill legacy disability_percentage from first entry
            if isinstance(disability_details_raw, list) and disability_details_raw:
                first_pct = disability_details_raw[0].get('disability_percentage')
                if first_pct and not user.disability_percentage:
                    user.disability_percentage = safe_int(first_pct)

        # Employment / Occupation
        user.employment_status_v2      = data.get('employmentStatus')
        user.occupation_type           = data.get('occupationTypeNew')  # 'occupationTypeNew' avoids clash with 'occupation'

        # Land ownership (JSON list)
        land_raw = data.get('landOwnershipDetails')
        if land_raw is not None:
            if isinstance(land_raw, list):
                user.land_ownership_details = json.dumps(land_raw)
            elif isinstance(land_raw, str):
                user.land_ownership_details = land_raw
            # Back-fill legacy land_size_acres from sum of agricultural parcels
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
                user.family_members = json.dumps(family_raw)
            elif isinstance(family_raw, str):
                user.family_members = family_raw
            # Derived: num_daughters, is_orphan
            if isinstance(family_raw, list):
                daughters = [
                    m for m in family_raw
                    if str(m.get('relation', '')).lower() == 'daughter'
                    and m.get('is_alive', True)
                ]
                user.num_daughters = len(daughters)
                parents_alive = [
                    m for m in family_raw
                    if str(m.get('relation', '')).lower() in ('father', 'mother')
                    and m.get('is_alive', True)
                ]
                user.is_orphan = 'Yes' if len(parents_alive) == 0 else 'No'

        # Education details (JSON list)
        edu_raw = data.get('educationDetails')
        if edu_raw is not None:
            if isinstance(edu_raw, list):
                user.education_details = json.dumps(edu_raw)
            elif isinstance(edu_raw, str):
                user.education_details = edu_raw
            # Back-fill legacy highest_education_level
            if isinstance(edu_raw, list) and edu_raw:
                _level_order = [
                    'Below Class 10', 'Class 10', 'Class 12', 'Diploma',
                    'Graduation', 'Post Graduation', 'PhD', 'Other'
                ]
                completed = [
                    e for e in edu_raw if e.get('status') in ('Completed', 'Pursuing')
                ]
                if completed:
                    def _level_rank(e):
                        lvl = e.get('education_level', '')
                        return _level_order.index(lvl) if lvl in _level_order else -1
                    highest = max(completed, key=_level_rank)
                    user.highest_education_level = highest.get('education_level')
                    user.education_status = highest.get('status')
                    user.institution_type  = highest.get('institute_type')

        # Residency
        user.state_of_domicile         = data.get('stateOfDomicile')
        user.residence_location_type   = data.get('residenceLocationType')  # "Rural"/"Urban"
        user.years_in_current_state    = safe_int(data.get('yearsInCurrentState'))

        # Special categories
        user.is_ex_serviceman_or_dependent   = data.get('isExServicemanOrDependent')
        user.is_shg_member                   = data.get('isShgMember')
        user.is_freedom_fighter_or_dependent = data.get('isFreedomFighterOrDependent')

        # Health
        user.has_critical_illness      = data.get('hasCriticalIllness')
        user.is_pregnant               = data.get('isPregnant')
        user.is_lactating_mother       = data.get('isLactatingMother')

        # ── BACK-FILL LEGACY COLUMNS so the existing engine keeps working ──────
        # annual_family_income
        if user.annual_family_income_v2 is not None:
            user.annual_family_income = user.annual_family_income_v2
            user.income = user.annual_family_income_v2  # legacy column

        # ration_card_type / BPL inference
        if user.is_bpl_v2 == 'Yes' and not user.ration_card_type:
            user.ration_card_type = 'BPL'
        elif user.is_bpl_v2 == 'No' and user.ration_card_type in (None, ''):
            user.ration_card_type = 'APL'

        # bank_account_available
        if user.has_bank_account_v2:
            user.bank_account_available = user.has_bank_account_v2

        # gender (legacy)
        if user.gender_v2:
            user.gender = user.gender_v2

        # marital_status (legacy)
        if user.marital_status_v2:
            user.marital_status = user.marital_status_v2

        # state (legacy) — full name is fine; engine does lower().strip() comparison
        if user.state_of_domicile:
            user.state = user.state_of_domicile

        # residence (legacy)
        if user.residence_location_type:
            user.residence = user.residence_location_type.lower()  # "rural"/"urban"

        # employment_status (legacy)
        if user.employment_status_v2:
            user.employment_status = user.employment_status_v2

        # is_farmer back-fill from occupation_type
        if user.occupation_type and 'farmer' in user.occupation_type.lower():
            user.is_farmer = 'Yes'

        # is_bocw_registered back-fill (construction workers are typically BOCW)
        if user.occupation_type == 'Construction Worker' and not user.is_bocw_registered:
            user.is_bocw_registered = 'Yes'

        # minority_status back-fill
        if user.social_category == 'Minority':
            user.minority_status = 'Yes'
        elif user.social_category and user.social_category != 'Minority':
            if not user.minority_status:
                user.minority_status = 'No'

        # ews_status back-fill
        if user.social_category == 'Economically Weaker Section (EWS)':
            user.ews_status = 'Yes'

        # caste back-fill
        _CASTE_MAP = {
            'Scheduled Caste (SC)':                        'SC',
            'Scheduled Tribe (ST)':                        'ST',
            'Other Backward Class (OBC) - Non-Creamy Layer': 'OBC',
            'Other Backward Class (OBC) - Creamy Layer':   'OBC',
            'Economically Weaker Section (EWS)':           'General',
            'General':                                     'General',
            'Minority':                                    'General',
            'Denotified/Nomadic/Semi-Nomadic Tribes (DNT/NT/SNT)': 'ST',
        }
        if user.social_category and not user.caste:
            user.caste = _CASTE_MAP.get(user.social_category, user.social_category)

        # is_widow_single_woman back-fill
        if user.marital_status_v2 in ('Widow/Widower', 'Divorced', 'Separated'):
            if not user.is_widow_single_woman:
                user.is_widow_single_woman = 'Yes'

        # dob back-fill
        if user.date_of_birth_v2 and not user.dob:
            user.dob = user.date_of_birth_v2
        # ── END NEW PROFILE FIELDS ────────────────────────────────────────────
