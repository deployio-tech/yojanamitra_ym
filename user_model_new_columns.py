# ─────────────────────────────────────────────────────────────────────────────
# NEW PROFILE FIELDS  (generated from new_profile_fields.json)
# Add these columns to the User class in app.py, after the existing columns.
# ─────────────────────────────────────────────────────────────────────────────

    # ── Financial ────────────────────────────────────────────────────────────
    # Canonical annual family income (replaces the annual_family_income / income
    # split; keep old columns for backward compat, populate both on save)
    annual_family_income_v2        = db.Column(db.Integer)

    # Explicit BPL flag collected from the form (replaces ration_card_type inference)
    is_bpl_v2                      = db.Column(db.String(10))   # "Yes" / "No"

    # Whether the user has a bank account (replaces bank_account_available)
    has_bank_account_v2            = db.Column(db.String(10))   # "Yes" / "No"

    # ── Personal / Demographics ───────────────────────────────────────────────
    # Richer social category (replaces caste + minority_status + ews_status)
    # Values: "General" | "Scheduled Caste (SC)" | "Scheduled Tribe (ST)" |
    #         "Other Backward Class (OBC) - Creamy Layer" |
    #         "Other Backward Class (OBC) - Non-Creamy Layer" |
    #         "Economically Weaker Section (EWS)" | "Minority" |
    #         "Denotified/Nomadic/Semi-Nomadic Tribes (DNT/NT/SNT)"
    social_category                = db.Column(db.String(80))

    # ISO-8601 date string e.g. "1995-04-12" (replaces dob; age is derived)
    date_of_birth_v2               = db.Column(db.String(20))

    # Richer gender set: "Male" | "Female" | "Transgender" (replaces gender)
    gender_v2                      = db.Column(db.String(20))

    # Richer marital status: "Unmarried" | "Married" | "Widow/Widower" |
    #                        "Divorced" | "Separated"  (replaces marital_status)
    marital_status_v2              = db.Column(db.String(30))

    # ── Disability ────────────────────────────────────────────────────────────
    # JSON list of disability entries, e.g.:
    # [{"disability_type": "Visual Impairment", "disability_percentage": 60}]
    # Shown only when disability == "Yes".
    disability_details             = db.Column(db.Text)

    # ── Employment / Occupation ───────────────────────────────────────────────
    # Richer employment status (replaces employment_status):
    # "Employed (Salaried)" | "Self-Employed" | "Unemployed" |
    # "Student" | "Retired" | "Homemaker"
    employment_status_v2           = db.Column(db.String(50))

    # Occupation sub-type (shown when employed / self-employed):
    # "Farmer/Agricultural Labourer" | "Construction Worker" | "Artisan/Craftsperson" |
    # "Street Vendor" | "Safai Karamchari/Sanitation Worker" | "Domestic Worker" |
    # "Transport Worker (Driver/Conductor)" | "Government Employee" |
    # "Private Sector Employee" | "Journalist" | "Teacher/Academician" |
    # "Healthcare Worker" | "Fisherman" | "Weaver" | "Other"
    occupation_type                = db.Column(db.String(80))

    # ── Land ─────────────────────────────────────────────────────────────────
    # JSON list of land parcels, e.g.:
    # [{"area_in_acres": 2.5, "land_type": "Agricultural", "is_irrigated": true}]
    land_ownership_details         = db.Column(db.Text)

    # ── Family ────────────────────────────────────────────────────────────────
    # JSON list of family members, e.g.:
    # [{"relation": "Daughter", "date_of_birth": "2015-06-01", "is_alive": true}]
    # Derived values (num_daughters, is_orphan, child_age) are computed from this
    # list by the eligibility engine — not stored separately.
    family_members                 = db.Column(db.Text)

    # ── Education ─────────────────────────────────────────────────────────────
    # JSON list of qualifications, e.g.:
    # [{"education_level": "Class 10", "stream": "General", "status": "Completed",
    #   "percentage_marks": 72.5, "year_of_passing": 2018,
    #   "institute_type": "Government"}]
    education_details              = db.Column(db.Text)

    # ── Residency ─────────────────────────────────────────────────────────────
    # Canonical state/UT name (replaces state); full name e.g. "Karnataka"
    state_of_domicile              = db.Column(db.String(80))

    # "Rural" | "Urban"  (replaces residence)
    residence_location_type        = db.Column(db.String(20))

    # Number of years continuously resident in state_of_domicile
    years_in_current_state         = db.Column(db.Integer)

    # ── Special Categories ────────────────────────────────────────────────────
    is_ex_serviceman_or_dependent  = db.Column(db.String(10))   # "Yes" / "No"
    is_shg_member                  = db.Column(db.String(10))   # "Yes" / "No"
    is_freedom_fighter_or_dependent= db.Column(db.String(10))   # "Yes" / "No"

    # ── Health ────────────────────────────────────────────────────────────────
    has_critical_illness           = db.Column(db.String(10))   # "Yes" / "No"
    # Shown only when gender == "Female"
    is_pregnant                    = db.Column(db.String(10))   # "Yes" / "No"
    is_lactating_mother            = db.Column(db.String(10))   # "Yes" / "No"
