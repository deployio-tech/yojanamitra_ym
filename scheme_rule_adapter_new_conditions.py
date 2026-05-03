"""
scheme_rule_adapter — condition handlers for new condition keys
Generated from new_profile_fields.json + scheme_conditions.json

These handlers need to be merged into (or called by) scheme_rule_adapter.py's
build_rule() function.  Each handler returns True if the user PASSES that
condition, False if they fail it.

The profile dict passed to these functions is the raw_profile dict that is
already being constructed in app.py before ProfileNormalizer is applied.
All keys below are already present on raw_profile after the new fields patch.

──────────────────────────────────────────────────────────────────────────────
USAGE in build_rule():

    from scheme_rule_adapter_new_conditions import NEW_CONDITION_HANDLERS

    def build_rule(scheme):
        conditions = json.loads(scheme.conditions_json or '{}')
        def rule(profile):
            for key, value in conditions.items():
                handler = NEW_CONDITION_HANDLERS.get(key)
                if handler and not handler(profile, value):
                    return False
            # ... existing handlers ...
            return True
        return rule
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import json
from typing import Any


# ── Helpers ───────────────────────────────────────────────────────────────────

def _bool_flag(profile: dict, key: str) -> bool:
    """Return True when a Yes/No string profile field is 'Yes' or a bool True."""
    val = profile.get(key)
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ('yes', 'true', '1')


def _total_agricultural_land(profile: dict) -> float:
    """Sum all agricultural land parcels from land_ownership_details."""
    raw = profile.get('land_ownership_details') or profile.get('land_owned_acres')
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return 0.0
    if isinstance(raw, list):
        return sum(
            float(p.get('area_in_acres') or 0)
            for p in raw
            if str(p.get('land_type', '')).lower() == 'agricultural'
        )
    return 0.0


def _highest_education_rank(profile: dict) -> int:
    """
    Return a numeric rank for the highest education level achieved/pursuing.
    Lower = less educated.
    """
    _LEVEL_ORDER = [
        'below class 10', 'class 10', 'class 12', 'diploma',
        'graduation', 'post graduation', 'phd', 'other'
    ]
    # Try education_details list first
    raw = profile.get('education_details')
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            raw = None
    if isinstance(raw, list) and raw:
        best = -1
        for entry in raw:
            lvl = str(entry.get('education_level', '')).lower()
            if lvl in _LEVEL_ORDER:
                rank = _LEVEL_ORDER.index(lvl)
                if rank > best:
                    best = rank
        if best >= 0:
            return best

    # Fall back to legacy highest_education_level string
    legacy = str(profile.get('highest_education_level') or
                 profile.get('education') or '').lower().strip()
    _LEGACY_MAP = {
        'illiterate': 0, 'below class 10': 0, 'primary': 0,
        'middle': 1, 'class 10': 1, '10th': 1, 'sslc': 1, 'matric': 1,
        'class 12': 2, '12th': 2, 'hsc': 2, 'puc': 2, 'intermediate': 2,
        'diploma': 3,
        'graduation': 4, "bachelor's": 4, 'ug': 4, 'degree': 4,
        'post graduation': 5, 'pg': 5, "master's": 5,
        'phd': 6, 'doctorate': 6,
    }
    for key, rank in _LEGACY_MAP.items():
        if key in legacy:
            return rank
    return -1


_EDU_RANK_MAP = {
    'below class 10': 0,
    'class 10': 1,
    'secondary': 1,           # alias
    'class 12': 2,
    'higher secondary': 2,    # alias
    'diploma': 3,
    'graduation': 4,
    'post graduation': 5,
    'phd': 6,
}

def _edu_rank(level_str: str) -> int:
    return _EDU_RANK_MAP.get(str(level_str).lower().strip(), -1)


def _caste_category_list(profile: dict) -> list[str]:
    """
    Return a normalised list of caste category tokens for the user, e.g.
    ['sc'], ['st'], ['obc'], ['general'], ['ews'], ['minority'], ['dnt'].
    Reads from social_category (new) or caste (legacy).
    """
    cat = profile.get('social_category') or profile.get('caste') or ''
    cat_l = cat.lower()
    result = set()
    if 'scheduled caste' in cat_l or cat_l == 'sc':
        result.add('sc')
    if 'scheduled tribe' in cat_l or cat_l == 'st':
        result.add('st')
    if 'obc' in cat_l or 'other backward' in cat_l:
        result.add('obc')
    if 'ews' in cat_l or 'economically weaker' in cat_l:
        result.add('ews')
        result.add('general')  # EWS is a sub-category of General
    if 'minority' in cat_l:
        result.add('minority')
    if 'dnt' in cat_l or 'nomadic' in cat_l or 'denotified' in cat_l:
        result.add('dnt')
        result.add('st')       # DNT is treated as ST in most schemes
    if not result or 'general' in cat_l:
        result.add('general')
    return list(result)


# ── Condition handlers ────────────────────────────────────────────────────────
# Each handler signature: (profile: dict, condition_value: Any) -> bool
# Return True  → user PASSES this condition
# Return False → user FAILS this condition (ineligible)

def _handle_caste_category(profile: dict, value: Any) -> bool:
    """
    value: list of allowed caste tokens, e.g. ["sc", "st"]
    """
    if not value:
        return True
    required = [str(v).lower() for v in (value if isinstance(value, list) else [value])]
    user_cats = _caste_category_list(profile)
    return any(r in user_cats for r in required)


def _handle_education_level_min(profile: dict, value: Any) -> bool:
    """User must have AT LEAST this education level."""
    required_rank = _edu_rank(str(value))
    return _highest_education_rank(profile) >= required_rank


def _handle_education_level_max(profile: dict, value: Any) -> bool:
    """User must have AT MOST this education level."""
    required_rank = _edu_rank(str(value))
    user_rank = _highest_education_rank(profile)
    if user_rank < 0:
        return True  # unknown — don't disqualify
    return user_rank <= required_rank


def _handle_land_owned_min_acres(profile: dict, value: Any) -> bool:
    return _total_agricultural_land(profile) >= float(value)


def _handle_land_owned_max_acres(profile: dict, value: Any) -> bool:
    land = _total_agricultural_land(profile)
    if land == 0.0:
        return True  # no land declared — don't hard-fail (data might be missing)
    return land <= float(value)


def _handle_is_migrant_worker(profile: dict, value: Any) -> bool:
    # Not yet a first-class profile field; check occupation_type hint
    if not value:
        return True
    occ = str(profile.get('occupation_type') or profile.get('occupation') or '').lower()
    return 'migrant' in occ or 'transport' in occ


def _handle_is_acid_attack_survivor(profile: dict, value: Any) -> bool:
    if not value:
        return True
    # Stored as a special category flag when added in future; fall back to False
    return _bool_flag(profile, 'is_acid_attack_survivor')


def _handle_is_abandoned_woman(profile: dict, value: Any) -> bool:
    if not value:
        return True
    return (
        _bool_flag(profile, 'is_abandoned_woman') or
        str(profile.get('marital_status_v2') or
            profile.get('marital_status') or '').lower() in ('divorced', 'separated')
    )


def _handle_is_single_woman(profile: dict, value: Any) -> bool:
    if not value:
        return True
    gender = str(profile.get('gender_v2') or profile.get('gender') or '').lower()
    if 'female' not in gender:
        return False
    marital = str(profile.get('marital_status_v2') or
                  profile.get('marital_status') or '').lower()
    return marital in ('unmarried', 'widow/widower', 'divorced', 'separated')


def _handle_is_widow(profile: dict, value: Any) -> bool:
    if not value:
        return True
    marital = str(profile.get('marital_status_v2') or
                  profile.get('marital_status') or '').lower()
    return marital == 'widow/widower' or _bool_flag(profile, 'is_widow')


def _handle_is_minority(profile: dict, value: Any) -> bool:
    if not value:
        return True
    return (
        _bool_flag(profile, 'is_minority') or
        'minority' in _caste_category_list(profile)
    )


def _handle_requires_registered_enterprise(profile: dict, value: Any) -> bool:
    if not value:
        return True
    # Self-employed with an occupation type that suggests a business
    return _bool_flag(profile, 'is_self_employed') or str(
        profile.get('employment_status_v2') or
        profile.get('employment_status') or ''
    ).lower() == 'self-employed'


def _handle_requires_ngo_institution(profile: dict, value: Any) -> bool:
    """Only the applicant's institutional status matters; unknown → pass."""
    return True  # Cannot be determined from profile alone — skip hard-fail


def _handle_requires_literary_contribution(profile: dict, value: Any) -> bool:
    """Cannot be determined from standard profile fields — pass through."""
    return True


def _handle_requires_sports_achievement(profile: dict, value: Any) -> bool:
    """Check achievement_certificates list for a sports certificate."""
    if not value:
        return True
    certs_raw = profile.get('achievement_certificates') or []
    if isinstance(certs_raw, str):
        try:
            certs_raw = json.loads(certs_raw)
        except (ValueError, TypeError):
            certs_raw = []
    return any('sport' in str(c).lower() for c in certs_raw)


def _handle_has_pucca_house_disqualifies(profile: dict, value: Any) -> bool:
    """If the scheme has this condition, owning a pucca house DISQUALIFIES."""
    if not value:
        return True
    has_pucca = str(profile.get('has_pucca_house') or '').lower() == 'yes'
    return not has_pucca  # passes only if user does NOT have a pucca house


def _handle_is_govt_employee_disqualifies(profile: dict, value: Any) -> bool:
    """Government employees are disqualified."""
    if not value:
        return True
    is_govt = (
        str(profile.get('occupation_type') or '').lower() == 'government employee' or
        str(profile.get('occupation') or '').lower() in ('government', 'govt') or
        str(profile.get('govt_employee_in_family') or '').lower() == 'yes'
    )
    return not is_govt


def _handle_is_income_taxpayer_disqualifies(profile: dict, value: Any) -> bool:
    """Income taxpayers are disqualified; infer from income level."""
    if not value:
        return True
    income = (
        profile.get('annual_family_income_v2') or
        profile.get('annual_family_income') or
        profile.get('income') or 0
    )
    # Basic income-tax threshold in India is ₹3,00,000 (new regime floor, 2024-25)
    is_taxpayer = int(income or 0) > 300000
    return not is_taxpayer


def _handle_is_ex_serviceman(profile: dict, value: Any) -> bool:
    if not value:
        return True
    return _bool_flag(profile, 'is_ex_serviceman_or_dependent')


def _handle_is_shg_member(profile: dict, value: Any) -> bool:
    if not value:
        return True
    return _bool_flag(profile, 'is_shg_member')


def _handle_has_bank_account(profile: dict, value: Any) -> bool:
    if not value:
        return True
    return (
        _bool_flag(profile, 'has_bank_account_v2') or
        _bool_flag(profile, 'has_bank_account') or
        str(profile.get('bank_account_available') or '').lower() == 'yes'
    )


# ── Master dispatch table ─────────────────────────────────────────────────────
# Map every condition key that appears in scheme_conditions.json to its handler.

NEW_CONDITION_HANDLERS: dict[str, Any] = {
    # ── Already handled by existing engine but listed here for completeness ──
    # age_min / age_max / annual_family_income_max / income_annual_max
    # gender / residence / state / is_bpl / is_disabled / is_farmer /
    # is_self_employed / is_student / is_senior_citizen / is_orphan /
    # is_tribal / is_bocw_registered / is_landless / is_first_gen_student /
    # is_school_dropout / is_pensioner / is_widow / disability_percentage_min
    # — these are already in build_rule(); no need to re-add.

    # ── New handlers ─────────────────────────────────────────────────────────
    "caste_category":                   _handle_caste_category,
    "education_level_min":              _handle_education_level_min,
    "education_level_max":              _handle_education_level_max,
    "land_owned_min_acres":             _handle_land_owned_min_acres,
    "land_owned_max_acres":             _handle_land_owned_max_acres,
    "is_migrant_worker":                _handle_is_migrant_worker,
    "is_acid_attack_survivor":          _handle_is_acid_attack_survivor,
    "is_abandoned_woman":               _handle_is_abandoned_woman,
    "is_single_woman":                  _handle_is_single_woman,
    "is_widow":                         _handle_is_widow,
    "is_minority":                      _handle_is_minority,
    "requires_registered_enterprise":   _handle_requires_registered_enterprise,
    "requires_ngo_institution":         _handle_requires_ngo_institution,
    "requires_literary_contribution":   _handle_requires_literary_contribution,
    "requires_sports_achievement":      _handle_requires_sports_achievement,
    "has_pucca_house_disqualifies":     _handle_has_pucca_house_disqualifies,
    "is_govt_employee_disqualifies":    _handle_is_govt_employee_disqualifies,
    "is_income_taxpayer_disqualifies":  _handle_is_income_taxpayer_disqualifies,
    # New fields from new_profile_fields.json
    "is_ex_serviceman_or_dependent":    _handle_is_ex_serviceman,
    "is_shg_member":                    _handle_is_shg_member,
    "has_bank_account":                 _handle_has_bank_account,
}
