# ═══════════════════════════════════════════════════════════════════════════
# PASTE THIS ENTIRE BLOCK into scheme_rule_adapter.py
# Place it RIGHT AFTER the closing `return conds, disqs` of _build_ai_conditions()
# That is: after line 319 in your current file
# ═══════════════════════════════════════════════════════════════════════════

# ── Load new open-schema conditions (all_conditions.json) ──────────────────
_OPEN_CONDITIONS = {}
_OC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'all_conditions.json')
try:
    with open(_OC_PATH, 'r', encoding='utf-8') as _f:
        _OPEN_CONDITIONS = json.load(_f)
    logger.info(f"Loaded {len(_OPEN_CONDITIONS)} open-schema conditions from all_conditions.json")
except Exception as _e:
    logger.warning(f"Could not load all_conditions.json: {_e}")


def _coerce(val, field: str):
    """Coerce a value to the right Python type based on field name."""
    numeric_keywords = ('age', 'income', 'disability', 'land', 'children', 'daughters', 'sons', 'years', 'percent')
    if any(k in field for k in numeric_keywords):
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return val
    return val


def _build_open_conditions(scheme_id: int) -> tuple:
    """
    Build EligibilityCondition objects from all_conditions.json (new open schema).

    The new schema stores conditions as a LIST of objects:
      [{"field": "age_min", "type": "range", "operator": "min", "value": 18, ...}, ...]

    This replaces the old flat-dict schema from scheme_conditions.json.
    Unknown fields are skipped — they surface as POSSIBLY_ELIGIBLE naturally
    because UserProfile won't have them. Add fields to FIELD_MAP + UserProfile
    as you expand the profile to move them to FULLY_ELIGIBLE.
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
        return [], []  # old dict format — let _build_ai_conditions handle it

    conds = []
    disqs = []
    sid = scheme_id

    # ── Field map: Gemini field name → (UserProfile field, default operator) ──
    # Add new entries here as you add fields to UserProfile
    FIELD_MAP = {
        # Numeric ranges
        'age_min':                      ('age',                     'gte'),
        'age_max':                      ('age',                     'lte'),
        'annual_family_income_max':     ('income_annual',           'lte'),
        'income_annual_max':            ('income_annual',           'lte'),
        'monthly_income_max':           ('income_annual',           'lte'),   # annualised below
        'disability_percentage_min':    ('disability_percentage',   'gte'),
        'land_owned_max_acres':         ('land_owned_acres',        'lte'),
        'land_owned_min_acres':         ('land_owned_acres',        'gte'),
        # Enums
        'gender':                       ('gender',                  'in'),
        'caste_category':               ('caste_category',          'in'),
        'state':                        ('state',                   'in'),
        'residence':                    ('residence',               'in'),
        'education_level_min':          ('education_level',         'gte'),
        'education_level_max':          ('education_level',         'lte'),
        'religion':                     ('religion',                'in'),
        # Booleans (must be True)
        'is_student':                   ('is_student',              'is_true'),
        'is_disabled':                  ('is_disabled',             'is_true'),
        'is_farmer':                    ('is_farmer',               'is_true'),
        'is_bpl':                       ('is_bpl',                  'is_true'),
        'is_bocw_registered':           ('is_bocw_registered',      'is_true'),
        'is_tribal':                    ('is_tribal',               'is_true'),
        'is_widow':                     ('is_widow',                'is_true'),
        'is_senior_citizen':            ('is_senior_citizen',       'is_true'),
        'is_minority':                  ('is_minority',             'is_true'),
        'is_orphan':                    ('is_orphan',               'is_true'),
        'is_self_employed':             ('is_self_employed',        'is_true'),
        'is_migrant_worker':            ('is_migrant_worker',       'is_true'),
        'is_school_dropout':            ('is_school_dropout',       'is_true'),
        'is_first_gen_student':         ('is_first_gen_student',    'is_true'),
        'is_single_woman':              ('is_single_woman',         'is_true'),
        'is_abandoned_woman':           ('is_single_woman',         'is_true'),
        'is_pensioner':                 ('is_pensioner',            'is_true'),
        'is_woman_entrepreneur':        ('is_woman_entrepreneur',   'is_true'),
        'is_landless':                  ('is_landless',             'is_true'),
        'is_acid_attack_survivor':      ('is_acid_attack_survivor', 'is_true'),
        # Disqualifiers (presence = disqualified)
        'has_pucca_house_disqualifies':         ('has_pucca_house',     'is_true'),
        'is_govt_employee_disqualifies':        ('is_govt_employee',    'is_true'),
        'is_income_taxpayer_disqualifies':      ('is_income_taxpayer',  'is_true'),
        # ── ADD NEW FIELDS BELOW as you expand UserProfile ─────────────────
        # 'is_ex_serviceman':   ('is_ex_serviceman',   'is_true'),
        # 'has_aadhaar':        ('has_aadhaar',        'is_true'),
        # 'num_children_max':   ('num_children',       'lte'),
        # 'num_daughters_min':  ('num_daughters',      'gte'),
        # 'marital_status':     ('marital_status',     'in'),
    }

    DISQUALIFIER_FIELDS = {
        'has_pucca_house_disqualifies',
        'is_govt_employee_disqualifies',
        'is_income_taxpayer_disqualifies',
    }

    for cond in raw_conditions:
        field_name  = cond.get('field', '')
        cond_type   = cond.get('type', 'other')
        operator    = cond.get('operator', '')
        value       = cond.get('value')
        value_min   = cond.get('value_min')
        value_max   = cond.get('value_max')
        unit        = cond.get('unit', '') or ''
        conf        = cond.get('confidence', 0.8)
        required    = cond.get('required', True)

        # Skip low-confidence individual conditions
        if conf < 0.6:
            continue

        # Skip unmapped fields — they surface as POSSIBLY_ELIGIBLE naturally
        if field_name not in FIELD_MAP:
            continue

        engine_field, _ = FIELD_MAP[field_name]
        is_disq = field_name in DISQUALIFIER_FIELDS

        # ── RANGE ─────────────────────────────────────────────────────────
        if cond_type == 'range':
            lo = value_min if value_min is not None else (value if operator in ('min', 'gte', 'between') else None)
            hi = value_max if value_max is not None else (value if operator in ('max', 'lte', 'between') else None)

            # monthly → annual
            if field_name == 'monthly_income_max' and hi is not None:
                hi = int(hi) * 12

            if lo is not None:
                conds.append(EligibilityCondition(
                    field=engine_field, operator='gte',
                    value=_coerce(lo, engine_field),
                    is_mandatory=bool(required),
                    failure_message=f"Minimum {engine_field.replace('_', ' ')}: {lo}{' ' + unit if unit else ''}.",
                    condition_id=f"{sid}_oc_{field_name}_min"))

            if hi is not None:
                conds.append(EligibilityCondition(
                    field=engine_field, operator='lte',
                    value=_coerce(hi, engine_field),
                    is_mandatory=bool(required),
                    failure_message=f"Maximum {engine_field.replace('_', ' ')}: {hi}{' ' + unit if unit else ''}.",
                    condition_id=f"{sid}_oc_{field_name}_max"))

        # ── ENUM ──────────────────────────────────────────────────────────
        elif cond_type in ('enum', 'multi_caste'):
            vals = value if isinstance(value, list) else ([value] if value else [])
            vals = [str(v).lower() for v in vals if v]

            # State: convert full names → 2-letter codes
            if engine_field == 'state':
                vals = [STATE_CODE_MAP.get(v, v.upper()[:2]) for v in vals]
                vals = [v for v in vals if len(v) == 2]

            # Caste: never restrict general users
            if engine_field == 'caste_category':
                vals = [v for v in vals if v not in ('all', 'any', 'general')]

            # Gender: filter noise
            if engine_field == 'gender':
                vals = [v for v in vals if v not in ('all', 'any')]

            # Residence: only valid values
            if engine_field == 'residence':
                vals = [v for v in vals if v in ('rural', 'urban', 'semi-urban')]

            if vals:
                conds.append(EligibilityCondition(
                    field=engine_field, operator='in', value=vals,
                    is_mandatory=bool(required),
                    failure_message=f"{engine_field.replace('_', ' ').title()} must be: {', '.join(vals)}.",
                    condition_id=f"{sid}_oc_{field_name}"))

        # ── BOOLEAN ───────────────────────────────────────────────────────
        elif cond_type == 'boolean':
            bool_val = value if isinstance(value, bool) else (str(value).lower() == 'true')
            op_str = 'is_true' if bool_val else 'is_false'

            ec = EligibilityCondition(
                field=engine_field, operator=op_str, value=None,
                is_mandatory=bool(required),
                failure_message=f"Must {'be' if bool_val else 'not be'} {engine_field.replace('_', ' ')}.",
                condition_id=f"{sid}_oc_{field_name}")

            if is_disq:
                disqs.append(ec)
            else:
                conds.append(ec)

        # ── DISQUALIFIER ──────────────────────────────────────────────────
        elif cond_type == 'disqualifier':
            disqs.append(EligibilityCondition(
                field=engine_field, operator='is_true', value=None,
                is_mandatory=True,
                failure_message=f"Disqualified: must not be {engine_field.replace('_', ' ')}.",
                condition_id=f"{sid}_oc_{field_name}_disq"))

    return conds, disqs


# ═══════════════════════════════════════════════════════════════════════════
# CHANGE 2 — In build_rule(), find this line (line 873):
#
#   _ai_conds, _ai_disqs = _build_ai_conditions(s.id)
#
# Replace it with these 4 lines:
# ═══════════════════════════════════════════════════════════════════════════

"""
    # ── AI-EXTRACTED CONDITIONS — try new open schema first, fallback to old ──
    _ai_conds, _ai_disqs = _build_open_conditions(s.id)
    if not _ai_conds and not _ai_disqs:
        _ai_conds, _ai_disqs = _build_ai_conditions(s.id)
    if _ai_conds or _ai_disqs:
        conditions.extend(_ai_conds)
        disqualifiers.extend(_ai_disqs)
        rule_confidence = 0.95
"""
