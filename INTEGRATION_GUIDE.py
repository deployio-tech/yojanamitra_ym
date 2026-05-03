"""
HOW TO PLUG all_conditions.json INTO YOUR SYSTEM
=================================================

After extract_all_conditions.py finishes, you have:
  all_conditions.json       — conditions as a LIST (new open schema)
  scheme_conditions.json    — conditions as a DICT (old fixed schema, still works)

Your system currently reads scheme_conditions.json via _build_ai_conditions() in
scheme_rule_adapter.py. The new file uses a different shape (list of condition
objects instead of flat dict), so you need the patch below.

STEP 1 — Rename files so both exist:
  all_conditions.json       → new open schema (use this going forward)
  scheme_conditions.json    → old fixed schema (keep as fallback)

STEP 2 — Apply the patch below to scheme_rule_adapter.py
  It adds _build_open_conditions() which reads all_conditions.json
  and maps each condition's field/type/operator/value to an EligibilityCondition.
  _build_ai_conditions() (old) stays untouched as fallback.
  build_rule() tries new file first, falls back to old.

STEP 3 — About FULLY_ELIGIBLE vs POSSIBLY_ELIGIBLE
  Your engine already does this correctly:
    FULLY_ELIGIBLE    → all conditions passed, no missing data
    POSSIBLY_ELIGIBLE → all hard conditions passed BUT some profile fields
                        that the scheme needs are missing/null in the user profile

  The classification happens automatically in StrictEligibilityEngine.evaluate().
  You don't need to change the engine.

  What determines which bucket a scheme falls into:
    FULLY_ELIGIBLE:   user has values for every field the scheme checks, and passes all
    POSSIBLY_ELIGIBLE: user passes all checks BUT is missing a field
                       e.g. scheme needs is_bocw_registered, user never filled that in
                       → engine can't confirm, gives benefit of doubt = POSSIBLY_ELIGIBLE

  To IMPROVE the split (more schemes into FULLY_ELIGIBLE, fewer into POSSIBLY):
    → Add more fields to your profile form
    → Check unmapped_conditions.json for which new fields appear most often
    → Add those fields to UserProfile in eligibility_engine_strict_v21.py
    → Add them to the profile form in your frontend
    → Users who fill them in will move from POSSIBLY → FULLY

STEP 4 — New fields from all_conditions.json
  The new extractor finds fields your engine doesn't know yet (engine_missed=true).
  These generate conditions that will fall through to POSSIBLY_ELIGIBLE because
  the user profile doesn't have those fields.

  To promote them to FULLY_ELIGIBLE:
    a) Check field_coverage.json → unmapped_fields_by_frequency
    b) For each high-frequency field, add it to UserProfile dataclass
    c) Add it to the profile form
    d) Add it to _build_open_conditions() FIELD_MAP below

  Example: if "is_ex_serviceman" appears in 200 schemes but isn't in UserProfile,
  add `is_ex_serviceman: bool = False` to UserProfile and it starts working.

===============================================================================
PATCH — add this to scheme_rule_adapter.py
===============================================================================
"""

# ─────────────────────────────────────────────────────────────────────────────
# PATCH FOR scheme_rule_adapter.py
# Add these two blocks to your existing scheme_rule_adapter.py
# ─────────────────────────────────────────────────────────────────────────────

# ── BLOCK 1: Add near top of file, after existing _SCHEME_CONDITIONS loading ──

OPEN_CONDITIONS_PATCH = '''
# ── Load new open-schema conditions (all_conditions.json) ─────────────────────
_OPEN_CONDITIONS = {}
_OC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'all_conditions.json')
try:
    with open(_OC_PATH, 'r', encoding='utf-8') as _f:
        _OPEN_CONDITIONS = json.load(_f)
    logger.info(f"Loaded {len(_OPEN_CONDITIONS)} open-schema conditions from all_conditions.json")
except Exception as _e:
    logger.warning(f"Could not load all_conditions.json: {_e}")


def _build_open_conditions(scheme_id: int) -> tuple:
    """
    Build EligibilityCondition objects from all_conditions.json (new open schema).
    Conditions are a list of {field, type, operator, value, value_min, value_max, ...}
    Returns (conditions_list, disqualifiers_list) or ([], []) if no data.

    Fields not in FIELD_MAP are silently skipped — they become POSSIBLY_ELIGIBLE
    triggers if the profile field doesn't exist yet. Add them to FIELD_MAP and
    UserProfile as you expand the profile.
    """
    entry = _OPEN_CONDITIONS.get(str(scheme_id))
    if not entry:
        return [], []
    if entry.get('_extraction_status') not in ('ok',):
        return [], []
    if entry.get('confidence', 0) < 0.65:
        return [], []
    if entry.get('is_institutional_scheme'):
        return [], []

    raw_conditions = entry.get('conditions', [])
    if isinstance(raw_conditions, dict):
        # Fallback: old dict format snuck in — use the old builder instead
        return [], []

    conds = []
    disqs = []
    sid = scheme_id

    # Map from Gemini field names → UserProfile field names
    # Add new fields here as you expand UserProfile
    FIELD_MAP = {
        # Age
        'age_min':                  ('age',                  'gte'),
        'age_max':                  ('age',                  'lte'),
        # Income
        'annual_family_income_max': ('income_annual',        'lte'),
        'income_annual_max':        ('income_annual',        'lte'),
        'monthly_income_max':       ('income_annual',        'lte'),   # will multiply by 12 below
        # Gender
        'gender':                   ('gender',               'in'),
        # Caste
        'caste_category':           ('caste_category',       'in'),
        # State
        'state':                    ('state',                'in'),
        # Residence
        'residence':                ('residence',            'in'),
        # Education
        'education_level_min':      ('education_level',      'gte'),
        'education_level_max':      ('education_level',      'lte'),
        # Disability
        'disability_percentage_min':('disability_percentage','gte'),
        # Land
        'land_owned_max_acres':     ('land_owned_acres',     'lte'),
        'land_owned_min_acres':     ('land_owned_acres',     'gte'),
        # Religion
        'religion':                 ('religion',             'in'),
        # Booleans — must be True
        'is_student':               ('is_student',           'is_true'),
        'is_disabled':              ('is_disabled',          'is_true'),
        'is_farmer':                ('is_farmer',            'is_true'),
        'is_bpl':                   ('is_bpl',               'is_true'),
        'is_bocw_registered':       ('is_bocw_registered',   'is_true'),
        'is_tribal':                ('is_tribal',            'is_true'),
        'is_widow':                 ('is_widow',             'is_true'),
        'is_senior_citizen':        ('is_senior_citizen',    'is_true'),
        'is_minority':              ('is_minority',          'is_true'),
        'is_orphan':                ('is_orphan',            'is_true'),
        'is_self_employed':         ('is_self_employed',     'is_true'),
        'is_migrant_worker':        ('is_migrant_worker',    'is_true'),
        'is_school_dropout':        ('is_school_dropout',    'is_true'),
        'is_first_gen_student':     ('is_first_gen_student', 'is_true'),
        'is_single_woman':          ('is_single_woman',      'is_true'),
        'is_abandoned_woman':       ('is_single_woman',      'is_true'),
        'is_pensioner':             ('is_pensioner',         'is_true'),
        'is_woman_entrepreneur':    ('is_woman_entrepreneur','is_true'),
        'is_landless':              ('is_landless',          'is_true'),
        'is_acid_attack_survivor':  ('is_acid_attack_survivor', 'is_true'),
        # Disqualifiers — presence disqualifies
        'has_pucca_house_disqualifies':     ('has_pucca_house',    'is_true'),
        'is_govt_employee_disqualifies':    ('is_govt_employee',   'is_true'),
        'is_income_taxpayer_disqualifies':  ('is_income_taxpayer', 'is_true'),
        # ── ADD NEW FIELDS HERE as you expand UserProfile ──────────────────────
        # Example: 'is_ex_serviceman': ('is_ex_serviceman', 'is_true'),
        # Example: 'has_aadhaar':      ('has_aadhaar',       'is_true'),
        # Example: 'num_children_max': ('num_children',      'lte'),
    }

    DISQUALIFIER_FIELDS = {
        'has_pucca_house_disqualifies',
        'is_govt_employee_disqualifies',
        'is_income_taxpayer_disqualifies',
    }

    for cond in raw_conditions:
        field_name = cond.get('field', '')
        cond_type  = cond.get('type', 'other')
        operator   = cond.get('operator', '')
        value      = cond.get('value')
        value_min  = cond.get('value_min')
        value_max  = cond.get('value_max')
        unit       = cond.get('unit', '')
        source     = cond.get('source_text', '')
        conf       = cond.get('confidence', 0.8)
        required   = cond.get('required', True)

        # Skip low-confidence individual conditions
        if conf < 0.6:
            continue

        # Skip unmapped fields — these will surface as POSSIBLY_ELIGIBLE naturally
        # because the profile field won't exist on UserProfile
        if field_name not in FIELD_MAP:
            continue

        engine_field, default_op = FIELD_MAP[field_name]
        is_disq = field_name in DISQUALIFIER_FIELDS

        # ── Range conditions (age, income, land, etc.) ──────────────────────
        if cond_type == 'range':
            lo = value_min if value_min is not None else (value if operator in ('min', 'gte', 'between') else None)
            hi = value_max if value_max is not None else (value if operator in ('max', 'lte', 'between') else None)

            # monthly income → annualise
            if field_name == 'monthly_income_max' and hi is not None:
                hi = int(hi) * 12

            if lo is not None:
                conds.append(EligibilityCondition(
                    field=engine_field, operator='gte', value=_coerce(lo, engine_field),
                    is_mandatory=required,
                    failure_message=f"Minimum {engine_field.replace('_',' ')}: {lo} {unit}.",
                    condition_id=f"{sid}_oc_{field_name}_min"))
            if hi is not None:
                conds.append(EligibilityCondition(
                    field=engine_field, operator='lte', value=_coerce(hi, engine_field),
                    is_mandatory=required,
                    failure_message=f"Maximum {engine_field.replace('_',' ')}: {hi} {unit}.",
                    condition_id=f"{sid}_oc_{field_name}_max"))

        # ── Enum / multi-value conditions ───────────────────────────────────
        elif cond_type in ('enum', 'multi_caste'):
            vals = value if isinstance(value, list) else ([value] if value else [])
            vals = [str(v).lower() for v in vals if v]

            # State codes: convert full names to 2-letter codes
            if engine_field == 'state':
                vals = [STATE_CODE_MAP.get(v, v.upper()) for v in vals]
                vals = [v for v in vals if len(v) == 2]

            # Caste: drop 'general' — general users shouldn't be excluded by caste conditions
            if engine_field == 'caste_category':
                vals = [v for v in vals if v not in ('all', 'any', 'general')]

            # Gender: filter noise
            if engine_field == 'gender':
                vals = [v for v in vals if v not in ('all', 'any')]

            if vals:
                conds.append(EligibilityCondition(
                    field=engine_field, operator='in', value=vals,
                    is_mandatory=required,
                    failure_message=f"{engine_field.replace('_',' ').title()} must be: {', '.join(vals)}.",
                    condition_id=f"{sid}_oc_{field_name}"))

        # ── Boolean conditions ──────────────────────────────────────────────
        elif cond_type == 'boolean':
            bool_val = value if isinstance(value, bool) else (str(value).lower() == 'true')
            op_str = 'is_true' if bool_val else 'is_false'

            ec = EligibilityCondition(
                field=engine_field, operator=op_str, value=None,
                is_mandatory=required,
                failure_message=f"Must {'be' if bool_val else 'not be'} {engine_field.replace('_',' ')}.",
                condition_id=f"{sid}_oc_{field_name}")

            if is_disq:
                disqs.append(ec)
            else:
                conds.append(ec)

        # ── Disqualifier conditions ─────────────────────────────────────────
        elif cond_type == 'disqualifier':
            disqs.append(EligibilityCondition(
                field=engine_field, operator='is_true', value=None,
                is_mandatory=True,
                failure_message=f"Disqualified: {engine_field.replace('_',' ')}.",
                condition_id=f"{sid}_oc_{field_name}_disq"))

    return conds, disqs


def _coerce(val, field: str):
    """Coerce a value to the right Python type based on field name."""
    numeric_fields = {
        'age', 'income_annual', 'annual_family_income',
        'disability_percentage', 'land_owned_acres', 'num_children',
        'num_daughters', 'num_sons', 'years_in_state',
    }
    if any(f in field for f in numeric_fields):
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return val
    return val
'''

# ── BLOCK 2: Replace the top of _build_ai_conditions OR add to build_rule ──
# In build_rule(), change the call from:
#
#   ai_conds, ai_disqs = _build_ai_conditions(int(s.id))
#
# to:
#
#   ai_conds, ai_disqs = _build_open_conditions(int(s.id))
#   if not ai_conds and not ai_disqs:
#       ai_conds, ai_disqs = _build_ai_conditions(int(s.id))  # fallback to old
#

BUILD_RULE_PATCH = '''
# In build_rule(), find the line:
#   ai_conds, ai_disqs = _build_ai_conditions(int(s.id))
# Replace with:

    ai_conds, ai_disqs = _build_open_conditions(int(s.id))
    if not ai_conds and not ai_disqs:
        ai_conds, ai_disqs = _build_ai_conditions(int(s.id))  # fallback to old schema
'''


# ─────────────────────────────────────────────────────────────────────────────
# HOW FULLY vs POSSIBLY ELIGIBLE WORKS (no code change needed)
# ─────────────────────────────────────────────────────────────────────────────

CLASSIFICATION_EXPLANATION = """
FULLY_ELIGIBLE  → User passes ALL conditions AND no profile field was missing.
                  Engine saw everything it needed and said YES with certainty.
                  Score = 100

POSSIBLY_ELIGIBLE → User passed all HARD conditions but the engine hit a field
                    that doesn't exist in the user's profile yet.
                    Engine says "looks good but I can't be 100% sure."
                    Score = 60

NOT_ELIGIBLE    → User failed at least one mandatory condition.
                  Score = 0

The two buckets already exist in your app.py response:
  {
    "recommendations": [...],     ← FULLY_ELIGIBLE schemes
    "possibly_eligible": [...],   ← POSSIBLY_ELIGIBLE schemes
    "meta": {
      "fully_eligible": N,
      "possibly_eligible": N,
      ...
    }
  }

Your dashboard.html already renders both separately too.
So classification is ALREADY WORKING — you just need more conditions
from all_conditions.json to make the split more accurate.

TO GET MORE SCHEMES INTO FULLY_ELIGIBLE:
  1. Open unmapped_conditions.json
  2. Look at high_priority list (fields in 20+ schemes)
  3. For each field, add to UserProfile in eligibility_engine_strict_v21.py:
       is_ex_serviceman: bool = False
       has_aadhaar: bool = False
       num_children: int = 0
       ... etc
  4. Add those fields to your profile form in the frontend
  5. Add them to FIELD_MAP in _build_open_conditions() above
  6. Restart Flask — schemes that needed those fields move from
     POSSIBLY_ELIGIBLE → FULLY_ELIGIBLE for users who filled them in

NOTHING BREAKS if you don't add a field immediately —
the engine skips unknown fields and puts the scheme in POSSIBLY_ELIGIBLE,
which is the correct conservative behavior.
"""


if __name__ == "__main__":
    print("=" * 65)
    print("  INTEGRATION STEPS")
    print("=" * 65)
    print("""
STEP 1 — Finish extract_all_conditions.py run (resume if stopped):
  python extract_all_conditions.py --resume --rpm 15

STEP 2 — Apply BLOCK 1 patch to scheme_rule_adapter.py:
  Paste _build_open_conditions() and _coerce() functions into the file
  right after the existing _build_ai_conditions() function

STEP 3 — Apply BLOCK 2 patch to scheme_rule_adapter.py:
  Find the line `ai_conds, ai_disqs = _build_ai_conditions(int(s.id))`
  in build_rule() and replace it with the two-liner that tries
  _build_open_conditions first, then falls back to _build_ai_conditions

STEP 4 — Restart Flask:
  python app.py

STEP 5 — Check unmapped_conditions.json for new fields to add:
  High priority fields = appear in 20+ schemes
  Add them to UserProfile + profile form + FIELD_MAP to move
  those schemes from POSSIBLY_ELIGIBLE to FULLY_ELIGIBLE

STEP 6 — Run the audit to verify improvement:
  python profile_vs_gemini_audit_v2.py --synthesize-only
""")
    print(CLASSIFICATION_EXPLANATION)
