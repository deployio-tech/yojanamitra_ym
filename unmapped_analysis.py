"""
UNMAPPED FIELDS — ANALYSIS & ACTION PLAN
=========================================

KEY INSIGHT: The 15,039 "unmapped fields" are NOT 15,039 unique concepts.
Gemini named the same concept differently across schemes.

The top unmapped fields by real impact:

  residency_state    749  ← ALL are just "state" — already mapped!
  domicile_state     448  ← same thing
  residence_state    219  ← same thing  
  resident_state     103  ← same thing
  location_state      58  ← same thing

These 1,578 "unmapped" conditions are actually STATE conditions that Gemini
named differently. Fix: add aliases in FIELD_MAP → they all map to "state".

After collapsing aliases, the REAL new fields that need profile additions are:

TIER 1 — HIGH VALUE (add these first, big unlock):
  is_building_construction_worker  96 schemes  → bool
  annual_family_income_max_rural   53 schemes  → int  (rural income variant)
  annual_family_income_max_urban   52 schemes  → int  (urban income variant)
  monthly_family_income_max        31 schemes  → int  (annualise × 12)
  monthly_income_max               28 schemes  → int  (annualise × 12)
  is_unemployed                    31 schemes  → bool
  is_transgender                   22 schemes  → bool
  is_destitute                     18 schemes  → bool
  is_girl_student                  16 schemes  → bool (gender=female + is_student)
  bride_age_min / groom_age_min    34/20 schemes → int (marriage schemes)

TIER 2 — MEDIUM VALUE:
  is_artist                        19 schemes  → bool
  is_fisherman                     13 schemes  → bool
  is_pregnant (already exists)     14 schemes  → ALREADY MAPPED
  is_ex_serviceman (already)        9 schemes  → ALREADY MAPPED
  has_aadhar_card / has_aadhaar    26 schemes  → bool (document check)

SKIP — NOT INDIVIDUAL PROFILE FIELDS:
  applicant_type       216   → institutional/business, not individual
  enterprise_type       74   → business type, not individual
  school_type           70   → institution type
  institution_type      66   → institution type
  course_level          53   → changes per application, not profile
  course_type           51   → changes per application
  class_level           41   → student's current class
  residency_status     223   → just "must be resident" = assume true for all
  is_indian_citizen     72   → assume true for all Indian users
  is_citizen            71   → assume true
  is_permanent_resident 53   → assume true
  is_indian_national    30   → assume true
"""

# ═══════════════════════════════════════════════════════════════════════════
# PASTE 1 — Add to UserProfile in eligibility_engine_strict_v21.py
# Find the UserProfile @dataclass and add these fields
# ═══════════════════════════════════════════════════════════════════════════

USER_PROFILE_ADDITIONS = """
    # ── NEW FIELDS — add after existing booleans ──────────────────────────

    # Construction workers (96 BOCW schemes)
    is_construction_worker: bool = False       # maps: is_building_construction_worker,
                                               #       is_registered_construction_worker,
                                               #       is_engaged_in_construction_work

    # Unemployment (31 schemes)
    is_unemployed: bool = False

    # Transgender (22 schemes)
    is_transgender: bool = False

    # Destitute (18 schemes)
    is_destitute: bool = False

    # Artist (19 schemes)
    is_artist: bool = False

    # Fisherman (13 schemes)
    is_fisherman: bool = False

    # Monthly income (28+31 schemes use monthly, not annual)
    # Store as monthly; engine converts to annual for comparison
    income_monthly: Optional[int] = None

    # Rural/Urban income split (53+52 schemes)
    # Store both; engine picks the right one based on residence
    income_annual_rural: Optional[int] = None
    income_annual_urban: Optional[int] = None

    # Marriage age fields (bride/groom age for marriage assistance schemes)
    # Only relevant for users who are getting married — collect at time of applying
    # bride_age and groom_age are dynamic, not profile fields. Skip.

    # Documents (26 schemes check aadhaar explicitly)
    has_aadhaar: bool = True   # assume True; only set False if user says no

    # Girl student (16 schemes) — derived: gender=female AND is_student
    # No new field needed — engine derives this
"""

# ═══════════════════════════════════════════════════════════════════════════
# PASTE 2 — Add to FIELD_MAP in scheme_rule_adapter_patch.py
# Add these entries inside the FIELD_MAP dict in _build_open_conditions()
# ═══════════════════════════════════════════════════════════════════════════

FIELD_MAP_ADDITIONS = """
        # ── STATE ALIASES (749+448+219+103+58+37+26+14 = ~1700 schemes) ──────
        # All these are just "state" — Gemini named them differently
        'residency_state':          ('state',                   'in'),
        'domicile_state':           ('state',                   'in'),
        'residence_state':          ('state',                   'in'),
        'resident_state':           ('state',                   'in'),
        'location_state':           ('state',                   'in'),
        'state_of_residence':       ('state',                   'in'),
        'residential_state':        ('state',                   'in'),
        'parental_residence_state': ('state',                   'in'),

        # ── CONSTRUCTION WORKERS (96+67+21 = 184 schemes) ────────────────────
        'is_building_construction_worker':  ('is_construction_worker', 'is_true'),
        'is_registered_construction_worker':('is_construction_worker', 'is_true'),
        'is_engaged_in_construction_work':  ('is_construction_worker', 'is_true'),
        'is_construction_worker':           ('is_construction_worker', 'is_true'),

        # ── DISABILITY ALIASES (42+35+28 = 105 schemes) ───────────────────────
        'is_person_with_disability':  ('is_disabled',  'is_true'),
        'is_differently_abled':       ('is_disabled',  'is_true'),
        'is_divyangjan':              ('is_disabled',  'is_true'),

        # ── BPL ALIASES (83+21+20+20+9 = 153 schemes) ────────────────────────
        'is_below_poverty_line':  ('is_bpl', 'is_true'),
        'is_bpl_category':        ('is_bpl', 'is_true'),
        'is_bpl_family':          ('is_bpl', 'is_true'),
        'is_bpl_family_member':   ('is_bpl', 'is_true'),
        'poverty_status':         ('is_bpl', 'is_true'),   # enum → treat as bool

        # ── INCOME ALIASES ────────────────────────────────────────────────────
        'monthly_family_income_max':        ('income_annual',  'lte'),  # × 12 in handler
        'monthly_income_max':               ('income_annual',  'lte'),  # × 12 in handler
        'annual_family_income_max_rural':   ('income_annual',  'lte'),  # rural variant
        'annual_family_income_max_urban':   ('income_annual',  'lte'),  # urban variant
        'parental_annual_income_max':       ('income_annual',  'lte'),
        'annual_parental_income_max':       ('income_annual',  'lte'),

        # ── GENDER ALIASES ────────────────────────────────────────────────────
        'is_woman':     ('gender',  'in'),   # value → ['female']
        'is_female':    ('gender',  'in'),   # value → ['female']

        # ── NEW BOOLEANS ──────────────────────────────────────────────────────
        'is_unemployed':      ('is_unemployed',   'is_true'),
        'is_transgender':     ('is_transgender',  'is_true'),
        'is_destitute':       ('is_destitute',    'is_true'),
        'is_artist':          ('is_artist',       'is_true'),
        'is_fisherman':       ('is_fisherman',    'is_true'),
        'is_girl_student':    ('is_student',      'is_true'),  # engine still checks gender separately

        # ── DOCUMENT ALIASES ──────────────────────────────────────────────────
        'has_aadhar_card':              ('has_aadhaar', 'is_true'),
        'has_aadhaar_linked_bank_account': ('has_aadhaar', 'is_true'),

        # ── INCOME TAX DISQUALIFIER ALIASES ──────────────────────────────────
        'is_income_tax_payer_disqualifies': ('is_income_taxpayer', 'is_true'),
        'is_income_tax_payer':              ('is_income_taxpayer', 'is_true'),

        # ── WIDOW ALIASES ─────────────────────────────────────────────────────
        'is_destitute_widow':  ('is_widow', 'is_true'),

        # ── RESIDENCE AREA ALIASES ────────────────────────────────────────────
        'residence_area_type': ('residence', 'in'),
        'residency_location':  ('residence', 'in'),  # not a state — rural/urban

        # SKIP (citizenship assumed true for all users):
        # is_indian_citizen, is_citizen, is_permanent_resident,
        # is_indian_national, is_citizen_of_india, residency_status
"""

# ═══════════════════════════════════════════════════════════════════════════
# PASTE 3 — Special handler for monthly income and is_woman
# Add this inside the for loop in _build_open_conditions(),
# BEFORE the existing `if cond_type == 'range':` block
# ═══════════════════════════════════════════════════════════════════════════

SPECIAL_HANDLERS = """
        # ── Special: monthly income → annualise ──────────────────────────────
        if field_name in ('monthly_family_income_max', 'monthly_income_max', 'monthly_salary_max'):
            if cond_type == 'range' and value is not None:
                try:
                    annual_val = int(float(value)) * 12
                    conds.append(EligibilityCondition(
                        field='income_annual', operator='lte',
                        value=annual_val,
                        is_mandatory=bool(required),
                        failure_message=f'Monthly income must not exceed ₹{int(float(value)):,} (annual: ₹{annual_val:,}).',
                        condition_id=f'{sid}_oc_{field_name}_monthly'))
                except (ValueError, TypeError):
                    pass
            continue  # handled, skip normal flow

        # ── Special: is_woman / is_female → gender in ['female'] ─────────────
        if field_name in ('is_woman', 'is_female'):
            if value is True or value == 'True' or value == True:
                conds.append(EligibilityCondition(
                    field='gender', operator='in', value=['female'],
                    is_mandatory=bool(required),
                    failure_message='This scheme is for women applicants only.',
                    condition_id=f'{sid}_oc_{field_name}'))
            continue

        # ── Special: rural/urban income split ─────────────────────────────────
        if field_name == 'annual_family_income_max_rural':
            if value is not None:
                try:
                    conds.append(EligibilityCondition(
                        field='income_annual', operator='lte',
                        value=int(float(value)),
                        is_mandatory=False,  # soft — only applies to rural users
                        failure_message=f'Rural annual family income must not exceed ₹{int(float(value)):,}.',
                        condition_id=f'{sid}_oc_income_rural'))
                except (ValueError, TypeError):
                    pass
            continue

        if field_name == 'annual_family_income_max_urban':
            if value is not None:
                try:
                    conds.append(EligibilityCondition(
                        field='income_annual', operator='lte',
                        value=int(float(value)),
                        is_mandatory=False,  # soft — only applies to urban users
                        failure_message=f'Urban annual family income must not exceed ₹{int(float(value)):,}.',
                        condition_id=f'{sid}_oc_income_urban'))
                except (ValueError, TypeError):
                    pass
            continue

        # ── Skip: citizenship conditions — assume all users are Indian citizens ─
        if field_name in ('is_indian_citizen', 'is_citizen', 'is_permanent_resident',
                          'is_indian_national', 'is_citizen_of_india', 'residency_status',
                          'is_citizen_and_resident', 'nationality'):
            continue  # skip — we assume all app users are Indian citizens
"""

# ═══════════════════════════════════════════════════════════════════════════
# PASTE 4 — Profile form additions (what to add to your frontend)
# Add these fields to your profile setup form
# ═══════════════════════════════════════════════════════════════════════════

FRONTEND_PROFILE_FIELDS = """
NEW FIELDS TO ADD TO PROFILE FORM:
===================================

1. is_construction_worker  (BOCW registered / construction worker)
   Type: Yes/No toggle
   Label: "Are you a registered construction worker? (BOCW)"
   Unlocks: ~184 schemes

2. is_unemployed
   Type: Yes/No toggle (or derive from employment_status)
   Label: "Are you currently unemployed?"
   Unlocks: ~31 schemes
   Note: can derive from employment_status === 'Unemployed'

3. is_transgender
   Type: Yes/No/Prefer not to say
   Label: "Do you identify as transgender?"
   Unlocks: ~22 schemes

4. is_destitute
   Type: Yes/No toggle
   Label: "Are you destitute / without any means of livelihood?"
   Unlocks: ~18 schemes

5. is_artist
   Type: Yes/No toggle
   Label: "Are you a professional artist / cultural practitioner?"
   Unlocks: ~19 schemes

6. is_fisherman
   Type: Yes/No toggle
   Label: "Are you engaged in fishing / aquaculture?"
   Unlocks: ~13 schemes

TOTAL NEW FIELDS: 6
ESTIMATED SCHEMES UNLOCKED: ~287 more into FULLY_ELIGIBLE

ALREADY WORKS (no form change needed):
  - State aliases: 1700 schemes now correctly handled via FIELD_MAP
  - BPL aliases: +70 schemes via alias mapping
  - Disability aliases: +70 schemes via alias mapping
  - Monthly income: +59 schemes via annualise handler
  - Gender aliases (is_woman): +47 schemes
  - Income tax disqualifier aliases: +25 schemes
"""

if __name__ == '__main__':
    print(USER_PROFILE_ADDITIONS)
    print(FIELD_MAP_ADDITIONS)
    print(FRONTEND_PROFILE_FIELDS)
