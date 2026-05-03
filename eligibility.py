"""
engine/eligibility.py
Multi-pass eligibility engine.
Pass 1: Hard gate  — any hard FAIL → INELIGIBLE immediately
Pass 2: Soft score — UNKNOWN soft conditions reduce confidence
Pass 3: Acquirable — surface "things to gather" without blocking
"""
import json
import math
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

log = logging.getLogger(__name__)


# ── HUMANIZATION SYSTEM ─────────────────────────────────────────────────────────

import re

PROPER_NOUNS = ["India", "Indian", "Aadhaar", "NRI", "BPL", "SC", "ST", "OBC", "EWS", "APY", "PMSBY", "PMJJBY"]

CLEAN_MAP = {
    "nri": "NRI",
    "aadhaar": "Aadhaar",
    "bpl": "BPL",
    "sc": "SC",
    "st": "ST",
    "obc": "OBC",
    "ews": "EWS",
    "csc": "CSC",
    "pmsby": "PMSBY",
    "pmjjby": "PMJJBY",
    "apy": "APY",
}

def format_inr(amount):
    """Format number in Indian style: ₹2,50,000"""
    try:
        amount = int(amount)
        s = str(amount)
        if len(s) <= 3:
            return f"₹{s}"
        # Indian format: last 3 digits, then groups of 2
        last3 = s[-3:]
        rest = s[:-3]
        
        # Split rest into groups of 2 from right
        parts = []
        while rest:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        
        if parts:
            return f"₹{','.join(parts)},{last3}"
        else:
            return f"₹{last3}"
    except:
        return str(amount)


def add_article(text):
    """Add 'a' or 'an' article to text"""
    if not text:
        return text
    text = text.strip()
    text = re.sub(r'^(a|an)\s+', '', text, flags=re.IGNORECASE)
    if not text:
        return text
    if text[0].lower() in 'aeiou':
        return "an " + text
    return "a " + text


def sentence_case(text):
    """Convert to sentence case with proper noun preservation"""
    if not text:
        return text
    text = text.lower()
    text = text[0].upper() + text[1:]
    # Use word boundary replacement to avoid partial matches
    for word in PROPER_NOUNS:
        pattern = r'\b' + re.escape(word.lower()) + r'\b'
        text = re.sub(pattern, word, text)
    return text


def clean_technical_words(text: str) -> str:
    """Replace technical abbreviations with proper format (preserving case)"""
    result = text
    
    # Case-insensitive replacement, preserving the case pattern
    for ugly, clean in CLEAN_MAP.items():
        pattern = re.compile(ugly, re.IGNORECASE)
        def replacer(m):
            if clean.isupper():
                return clean  # NRI
            elif clean[0].isupper():
                return clean.capitalize()  # Aadhaar
            return clean
        result = pattern.sub(replacer, result)
    
    # Convert to sentence case (will be applied as final pass in humanize_condition)
    return result


def humanize_field(field: str) -> str:
    """Convert field name to human-readable format"""
    # Replace underscores with spaces
    field = field.replace("_", " ")
    
    # Special case handling for "citizen of India" type fields
    citizen_patterns = {
        "is citizen of india": "a citizen of India",
        "is indian citizen": "a citizen of India",
        "is citizen": "a citizen of India",
    }
    for pattern, replacement in citizen_patterns.items():
        if field.startswith(pattern) or field == pattern:
            return clean_technical_words(f"You are {replacement}")
    
    # Handle boolean prefix patterns FIRST, then clean technical words
    if field.startswith("is "):
        core = field[3:]
        # Add article if needed
        if core and not core.startswith(("a ", "an ", "the ")):
            if core[0] in "aeiou":
                core = f"an {core}"
            else:
                core = f"a {core}"
        return clean_technical_words(f"You are {core}")
    
    if field.startswith("has "):
        return clean_technical_words(f"You have {field[4:]}")
    
    if field.startswith("does "):
        return clean_technical_words(f"You do {field[5:]}")
    
    if field.startswith("can "):
        return clean_technical_words(f"You can {field[4:]}")
    
    if field.startswith("have "):
        return clean_technical_words(f"You have {field[5:]}")
    
    # Default to "Your ..."
    return clean_technical_words(f"Your {field}")


def format_value_with_indicator(value, field: str) -> str:
    """Format value with appropriate indicator (₹ for money, nothing for age/etc)"""
    if isinstance(value, (int, float)):
        # Check if it's a money-related field
        field_lower = field.lower()
        money_keywords = ['income', 'salary', 'amount', 'fee', 'premium', 'sum', 'cover', 'limit', 'loan']
        
        if any(kw in field_lower for kw in money_keywords):
            return format_inr(value)
        else:
            # For non-money fields like age, just return the number
            return str(value)
    return str(value)


def humanize_condition(cond) -> str:
    """Convert condition to human-readable hint"""
    field = cond.field
    operator = cond.operator
    value = cond.value
    cond_type = getattr(cond, 'condition_type', 'soft')
    
    # Use "must" for hard conditions, "should" for soft
    modal = "must" if cond_type == "hard" else "should"
    
    # Get humanized field base
    field_text = humanize_field(field)
    
    # Handle special cases based on operator and value
    if operator == "eq":
        if value is True or str(value).lower() == "true":
            return sentence_case(field_text)
        elif value is False or str(value).lower() == "false":
            return sentence_case(field_text)
        else:
            val_str = format_value_with_indicator(value, field)
            return sentence_case(f"{field_text} {modal} be {val_str}")
    
    if operator == "neq":
        if value is True or str(value).lower() == "true":
            # Negative boolean - e.g., "has_no_existing_account"
            core = field.replace("has_", "").replace("is_", "").replace("_", " ")
            core = clean_technical_words(core)
            core = add_article(core)
            return sentence_case(f"You should not have {core}")
        elif value is False or str(value).lower() == "false":
            return sentence_case(f"{field_text} is true")
        else:
            val_str = format_value_with_indicator(value, field)
            return sentence_case(f"{field_text} {modal} not be {val_str}")
    
    if operator == "lte":
        val_str = format_value_with_indicator(value, field)
        return sentence_case(f"{field_text} {modal} be at most {val_str}")
    
    if operator == "gte":
        val_str = format_value_with_indicator(value, field)
        return sentence_case(f"{field_text} {modal} be at least {val_str}")
    
    if operator in ("in", "one_of"):
        if isinstance(value, list):
            vals = [str(v) for v in value[:3]]
            val_str = ", ".join(vals)
            if len(value) > 3:
                val_str += ", or other"
        else:
            val_str = str(value)
        return sentence_case(f"{field_text} {modal} be one of: {val_str}")
    
    if operator in ("not_in", "not_one_of"):
        if isinstance(value, list):
            vals = [str(v) for v in value[:3]]
            val_str = ", ".join(vals)
        else:
            val_str = str(value)
        return sentence_case(f"{field_text} {modal} not be any of: {val_str}")
    
    if operator in ("range", "between"):
        lo = format_value_with_indicator(value[0], field) if isinstance(value, (list, tuple)) else value[0]
        hi = format_value_with_indicator(value[1], field) if isinstance(value, (list, tuple)) else value[1]
        return sentence_case(f"{field_text} {modal} be between {lo} and {hi}")
    
    if operator == "boolean":
        if value is True or str(value).lower() == "true":
            return sentence_case(field_text)
        else:
            core = field.replace("is_", "").replace("has_", "").replace("_", " ")
            core = clean_technical_words(core)
            core = add_article(core)
            return sentence_case(f"You should not have {core}")
    
    # Fallback for unknown operators
    return sentence_case(f"{field_text} needs clarification")


def looks_complex(field: str) -> bool:
    """Check if field looks complex enough to need Gemini"""
    return (
        len(field) > 40 or
        "disqualifies" in field.lower() or
        "_min_" in field.lower() or
        "_max_" in field.lower() or
        "_operation" in field.lower() or
        "_misutilization" in field.lower()
    )


# In-memory cache for humanized conditions
_humanize_cache = {}


def format_condition(cond):
    """Format condition into human-readable eligibility hint (with caching)"""
    # Create cache key
    cache_key = f"{cond.field}:{cond.operator}:{cond.value}"
    
    # Check cache
    if cache_key in _humanize_cache:
        return _humanize_cache[cache_key]
    
    # Check if complex field needs Gemini (skip for now, use rule-based)
    if looks_complex(cond.field):
        # For complex fields, use a generic but clear message
        result = humanize_condition(cond)
    else:
        result = humanize_condition(cond)
    
    # Cache result
    _humanize_cache[cache_key] = result
    
    return result


GENDER_NORM = {
    "woman": "female", "women": "female", "girl": "female", "girls": "female",
    "daughter": "female", "man": "male", "men": "male", "boy": "male",
    "boys": "male", "son": "male", "transgender": "other", "trans": "other",
    "tg": "other", "third_gender": "other",
}

def normalize_gender(v):
    if v is None: return None
    v = str(v).strip().lower()
    return GENDER_NORM.get(v, v)


# ── CANONICAL FIELD SYSTEM ──────────────────────────────────────────────────────
# ONE SOURCE OF TRUTH - ALL fields map to canonical forms
CANONICAL_GROUPS = {
    "citizenship": [
        "is_indian_citizen",
        "is_citizen",
        "is_citizen_of_india",
        "is_indian_national"
    ],
    "bank_account": [
        "has_bank_account",
        "has_savings_bank_account",
        "has_valid_bank_account"
    ],
    "consent": [
        "has_provided_consent",
        "has_consent_for_auto_debit"
    ],
}

# Reverse lookup: original field -> canonical
FIELD_TO_CANONICAL = {}
for canonical, fields in CANONICAL_GROUPS.items():
    for f in fields:
        FIELD_TO_CANONICAL[f] = canonical


def get_canonical_field(field_name: str) -> str:
    """Convert any field to its canonical form."""
    return FIELD_TO_CANONICAL.get(field_name, field_name)


def normalize_condition_value(value):
    """Normalize condition value: convert invalid strings to None."""
    if value is None:
        return None
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ('none', 'null', ''):
            return None
    return value


def simulate_answer(field, profile):
    """STRICT: Return value for EXACT field name (canonical)."""
    # Get canonical form - this is the ONLY key we'll use
    canonical = get_canonical_field(field)
    
    # If value exists in profile at canonical key, use it
    if canonical in profile and profile[canonical] is not None:
        return profile[canonical]
    
    # Also check raw field name (after canonicalization)
    if field in profile and profile[field] is not None:
        return profile[field]
    
    # Provide defaults based on field patterns (for simulation only)
    if canonical in ["citizenship"]:
        return True
    if canonical in ["bank_account"]:
        return True
    if canonical in ["consent"]:
        return True
    
    # Numeric defaults
    if 'age' in canonical:
        return 25
    if 'income' in canonical:
        return 150000
    
    # Default for unknown fields
    return True


def validate_and_normalize(field, value):
    """Normalize user answer to canonical form."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lv = value.lower()
        if lv in ("true", "yes", "1"):
            return True
        if lv in ("false", "no", "0"):
            return False
        try:
            return int(value)
        except ValueError:
            return value
    return value


def discover_all_required_fields(engine, schemes, base_profile, max_depth=5):
    """
    PHASE 1: GLOBAL FIELD DISCOVERY
    Discover ALL required fields across ALL schemes.
    Returns UNION of all HARD USER fields needed.
    """
    from app.engine.questions import is_user_answerable
    
    discovered = set()
    
    for scheme in schemes:
        profile = dict(base_profile)
        
        for iteration in range(max_depth):
            before = len(discovered)
            
            eo = engine.evaluate(scheme, profile)
            
            for f in eo.missing_fields:
                if not is_user_answerable(f):
                    continue
                
                # SAFETY FIX 1: Canonical before set
                canonical = get_canonical_field(f)
                
                # SAFETY FIX 2: Ignore already-satisfied fields
                if canonical in profile and profile[canonical] is not None:
                    continue
                
                if canonical not in discovered:
                    discovered.add(canonical)
                    # TEMP simulation to unlock deeper conditions
                    profile[canonical] = simulate_answer(canonical, profile)
            
            # EDGE FIX 2: No-change break
            after = len(discovered)
            if before == after:
                break
    
    return discovered  # UNION of ALL fields across ALL schemes


def extract_all_user_fields_from_conditions(schemes):
    """
    STATIC EXTRACTION: Scan ALL scheme conditions for HARD USER fields.
    Returns complete set of fields required for eligibility decisions.
    """
    from app.engine.questions import is_user_answerable
    
    static_fields = set()
    
    for scheme in schemes:
        for cond in scheme.conditions:
            # MICRO FIX 1: Only HARD USER fields
            if (
                is_user_answerable(cond.field)
                and getattr(cond, 'condition_type', None) == 'hard'
            ):
                canonical = get_canonical_field(cond.field)
                static_fields.add(canonical)
    
    return static_fields


def get_hybrid_fields(engine, schemes, base_profile, max_depth=5):
    """
    HYBRID FIELD DISCOVERY
    Combines dynamic discovery + static extraction for complete coverage.
    """
    # Phase 1: Dynamic discovery (runtime coverage)
    dynamic_fields = discover_all_required_fields(engine, schemes, base_profile, max_depth)
    
    # Phase 2: Static extraction (condition scan)
    static_fields = extract_all_user_fields_from_conditions(schemes)
    
    # Phase 3: UNION + canonical normalization
    final_fields = dynamic_fields.union(static_fields)
    final_fields = {get_canonical_field(f) for f in final_fields}
    
    return final_fields


# ── Profile Normalizer ─────────────────────────────────────────────────────────
# Import ProfileNormalizer for centralized field mapping
from app.engine.profile_normalizer import ProfileNormalizer

def FIELD_MAP_compat(field: str) -> Optional[str]:
    """Temporary shim. Delete after Phase 2."""
    return ProfileNormalizer.get_instance().form_to_canonical.get(field)

# ── Field normalization ─────────────────────────────────────────────────────────
# Maps condition field names to profile field names
# DEPRECATED: Use ProfileNormalizer instead. This dict is kept for backward compat.
FIELD_MAP = {
    # AGE
    "age_min": "age",
    "age_max": "age",
    "age_min_for_overdraft": "age",
    "age_max_for_overdraft": "age",

    # CITIZENSHIP
    "is_citizen_of_india": "is_citizen",

    # BANK / KYC
    "has_full_kyc_standard_account": "has_bank_account",
    "has_minimum_transactions_and_kyc_adherence": "has_kyc",
    "has_satisfactory_account_operation_for_overdraft": "has_bank_history",

    # NRI
    "is_nri": "is_nri",

    # MINOR (derived from age - handled in get_profile_value)
    "is_minor": "age",
    
    # EXISTING ACCOUNT (maps to bank_account)
    "has_existing_standard_savings_account": "has_bank_account",
    
    # HOUSEHOLD (not user-answerable - skip)
    "household_count_for_overdraft": "household_count",
    
    # EXPANDED FIELD MAPPING (for is_user_answerable fields)
    "caste_category": "category",
    "caste_or_gender_status": "category",
    "annual_family_income_max": "annual_income",
    "annual_parental_income_max": "annual_income",
    "family_economic_status": "annual_income",
    "residence_state": "state",
    "residence_area_type": "residence",
    "residence_status": "residence",
    "residential_state": "state",
    "domicile_state": "state",
    "current_class": "education_level",
    "student_class_min": "education_level",
    "student_class_max": "education_level",
    "occupation_type": "occupation",
    "has_regular_income_source": "occupation",
    "child_count": "child_count",
    # Added to fix remaining POSSIBLE cases
    "caste_category_for_relaxation": "category",
    "caste_or_gender_status": "category",
    "continuation_marks_relaxation_category": "education_level",
    "age_relaxation_applicable": "age",
    # Additional mappings for remaining missing fields
    "is_indian_citizen": "is_citizen",
    "is_indian_national": "is_citizen",
    "residency_state": "state",
    "has_own_bank_account": "has_bank_account",
    "caste_category_for_assistance": "category",
    "is_person_with_disability": "is_disabled",
    "land_ownership_or_lease_duration": "land_size_acres",
    "land_lease_period_min": "land_size_acres",
    "family_poverty_status": "is_bpl",
    "employment_status": "employment_status",
    "course_level": "education_level",
    "applicant_type": "occupation",
    "eligible_entity_type": "occupation",
    "has_parivar_pehchan_patra": "has_ration_card",
    "has_proof_of_identity": "has_aadhaar",
    "has_sc_st_certificate": "category",
    "has_completed_online_registration": "has_aadhaar",
    "has_obtained_in_principle_approval": "has_bank_account",
    "has_registered_fishing_boat": "is_farmer",
    "has_fishing_license": "is_farmer",
    # More additional mappings
    "caste_category_for_assistance": "category",
    "caste_category_for_priority": "category",
    "loan_purpose": "occupation",
    "activity_type": "occupation",
    "minimum_qualification": "education_level",
    "has_phd_degree": "education_level",
    "institution_recognition": "education_level",
    "is_fisher": "occupation",
    "is_woman": "gender",
    "completed_online_registration": "has_aadhaar",
    "obtained_in_principle_approval": "has_bank_account",
    "has_co_owner_consent": "has_bank_account",
    # More additional mappings
    "employment_status": "employment_status",
    "employment_sector": "occupation",
    "beneficiary_occupation": "occupation",
    "institution_type": "education_level",
    "is_law_graduate": "education_level",
    "beneficiary_type": "occupation",
}


def get_profile_value(field_name: str, user_profile: dict) -> Any:
    """STRICT: Concept-level lookup with None guard.
    
    1. field → concept (via field_to_concept)
    2. concept → all fields in concept
    3. profile.get(any_field_in_concept)
    4. If None → return None (unknown)
    """
    # Load concept registry for mapping
    import json
    import os
    
    registry_path = os.path.join(os.path.dirname(__file__), '..', '..', 'concept_registry.json')
    try:
        with open(registry_path, 'r') as f:
            registry = json.load(f)
            field_to_concept = registry.get('field_to_concept', {})
    except Exception:
        field_to_concept = {}
    
    # Get canonical field name
    canonical = get_canonical_field(field_name)
    
    # Get concept for this field
    concept = field_to_concept.get(canonical, canonical)
    
    # Find all fields for this concept
    concept_fields = []
    for c in registry.get('concepts', []):
        if c['concept'] == concept:
            concept_fields = c.get('fields', [])
            break
    
    # Try all fields in this concept (any match = we know the answer)
    for f in concept_fields:
        value = user_profile.get(f)
        if value is not None:
            return value
    
    # Try original field name
    value = user_profile.get(field_name)
    if value is not None:
        return value
    
    # Try canonical
    value = user_profile.get(canonical)
    return value


# Fields that cannot be answered by users (bank internal, system states)
# These should be completely ignored in eligibility evaluation
NON_ANSWERABLE_FIELDS = [
    "has_satisfactory_account_operation_for_overdraft",
    "has_minimum_transactions_and_kyc_adherence",
    "household_count_for_overdraft",
    # System/internal fields (not user-profile fields)
    "total_population_min",
    "eligible_agency_type",
    "eligible_organization_type",
    "university_recognition",
    "category_i_study_year",
    "category_ii_qualification_status",
    "placement_officer_duty_scope",
    "residence_location_covered",
    "family_composition_must_be",
    "max_daughters_per_family",
    # ALL Disqualification fields (not user-answerable)
    "is_govt_employee_disqualifies",
    "is_suicide_disqualifies",
    "is_breach_of_law_with_criminal_intent_disqualifies",
    "is_defaulter_disqualifies",
    "self_nomination_disqualifies",
    "is_self_inflicted_injury_disqualifies",
    "is_pregnancy_related_disqualifies",
    "has_pre_existing_condition_disqualifies",
    "is_under_influence_disqualifies",
    "is_venereal_disease_or_insanity_disqualifies",
    "is_aviation_activity_disqualifies",
    "is_radiation_contamination_disqualifies",
    "is_nuclear_weapons_material_disqualifies",
    "is_war_related_disqualifies",
    "is_war_related_loss_disqualifies",
    "is_natural_death_disqualifies",
    "is_funeral_or_ambulance_charge_claim_disqualifies",
    "availing_other_scholarship_disqualifies",
    "is_receiving_other_pension_disqualifies",
    "prior_sponsorship_disqualifier",
    "is_non_accidental_disability_disqualifies",
    "is_residing_in_urban_municipal_area_disqualifies",
    "is_urban_resident_disqualifies",
    "is_resident_disqualifies",
    "has_received_similar_training_disqualifies",
    "project_purpose_refinancing_disqualifies",
    "project_purpose_personal_consumption_disqualifies",
    "lacks_formal_training_certification",
    # Project/work scheme fields
    "submits_dpr_or_scp",
    "project_cost_exclusion",
    "project_viability",
    "application_submission_timeline",
    "application_submission_deadline",
    "vehicle_utilization_purpose",
    "ensures_affordable_supply",
    "submits_undertaking_for_costs",
    "assistance_level_preference",
    "willingness_to_work",
    "guaranteed_work_days_per_year_max",
    "work_skill_level_disqualifies",
    # Academic/professional fields
    "achievement_level",
    "academic_record_quality",
    "profession",
    "nationality",
    "cause_of_death",
    "enterprise_sector",
    "shareholding_for_non_individual_enterprise",
    # Additional household/special condition fields
    "has_disabled_member_and_no_able_bodied_adult",
    "owns_refrigerator_disqualifies",
    # Skills/training fields
    "has_proven_work_experience_or_inherent_skills",
    "has_previously_completed_same_pmkvy_course",
]


# ── Result constants ──────────────────────────────────────────────────────────
ELIGIBLE   = "eligible"
POSSIBLE   = "possible"
INELIGIBLE = "ineligible"
UNKNOWN_R  = "unknown"

# ── Single-condition evaluation ───────────────────────────────────────────────
PASS_R    = "pass"
FAIL_R    = "fail"
UNKNOWN_C = "unknown"


@dataclass
class ConditionResult:
    condition_id: str
    field: str
    status: str           # pass | fail | unknown
    condition_type: str = "soft"  # hard | soft
    reason: str = ""


@dataclass
class EligibilityOutput:
    result:          str
    confidence:      float
    hard_score:      float      = 1.0
    soft_score:      float      = 1.0
    context_score:   float      = 0.5
    coverage_penalty:float      = 1.0
    blocking_field:  Optional[str] = None
    blocking_reason: str        = ""
    missing_fields:  list       = field(default_factory=list)
    acquirable:      list       = field(default_factory=list)
    condition_results: list     = field(default_factory=list)
    clarification_needed: list = field(default_factory=list)


# ── Operator evaluation ───────────────────────────────────────────────────────

def _eval_operator(operator: str, profile_val: Any, cond_val: Any) -> str:
    try:
        if operator == "lte":
            if profile_val is None:
                return UNKNOWN_C
            return PASS_R if float(profile_val) <= float(cond_val) else FAIL_R
        if operator == "gte":
            if profile_val is None:
                return UNKNOWN_C
            return PASS_R if float(profile_val) >= float(cond_val) else FAIL_R
        if operator == "eq":
            if profile_val is None:
                return UNKNOWN_C
            return PASS_R if str(profile_val).lower() == str(cond_val).lower() else FAIL_R
        if operator == "neq":
            if profile_val is None:
                return UNKNOWN_C
            return PASS_R if str(profile_val).lower() != str(cond_val).lower() else FAIL_R
        if operator in ("in", "one_of"):
            if profile_val is None:
                return UNKNOWN_C
            vals = [str(v).lower() for v in (cond_val if isinstance(cond_val, list) else [cond_val])]
            pv = str(profile_val).lower()
            return PASS_R if pv in vals else FAIL_R
        if operator in ("not_in", "not_one_of"):
            if profile_val is None:
                return UNKNOWN_C
            vals = [str(v).lower() for v in (cond_val if isinstance(cond_val, list) else [cond_val])]
            pv = str(profile_val).lower()
            return PASS_R if pv not in vals else FAIL_R
        if operator == "boolean":
            if profile_val is None:
                return UNKNOWN_C
            pv = profile_val if isinstance(profile_val, bool) else str(profile_val).lower() in ("true", "1", "yes")
            cv = cond_val if isinstance(cond_val, bool) else str(cond_val).lower() in ("true", "1", "yes")
            return PASS_R if pv == cv else FAIL_R
        if operator in ("range", "between"):
            if profile_val is None:
                return UNKNOWN_C
            # cond_val = [min, max]
            lo, hi = float(cond_val[0]), float(cond_val[1])
            return PASS_R if lo <= float(profile_val) <= hi else FAIL_R
    except (TypeError, ValueError, IndexError):
        pass
    return UNKNOWN_C


def evaluate_single(condition, profile: dict) -> ConditionResult:
    """Evaluate one Condition ORM object against a flat profile dict."""
    field_name = condition.field
    
    # Normalize condition value FIRST - convert invalid strings to None
    cond_val = normalize_condition_value(condition.value)
    
    # If value is None after normalization → treat as FAIL
    if cond_val is None:
        return ConditionResult(condition.id, field_name, FAIL_R,
                               condition_type=getattr(condition, 'condition_type', 'soft'),
                               reason=f"Invalid condition value: {repr(condition.value)}")
    
    profile_val = get_profile_value(field_name, profile)
    if field_name == "gender":
        profile_val = normalize_gender(profile_val)

    if profile_val is None:
        return ConditionResult(condition.id, field_name, UNKNOWN_C,
                               condition_type=getattr(condition, 'condition_type', 'soft'),
                               reason=f"Field '{field_name}' unknown in profile")

    if field_name == "gender" and isinstance(cond_val, str):
        cond_val = normalize_gender(cond_val)

    status = _eval_operator(condition.operator, profile_val, cond_val)
    reason = ""
    if status == FAIL_R:
        reason = f"{field_name} {condition.operator} {cond_val} (user has {profile_val})"

    return ConditionResult(condition.id, field_name, status,
                           condition_type=getattr(condition, 'condition_type', 'soft'),
                           reason=reason)


# ── Margin bonus ──────────────────────────────────────────────────────────────
NUMERIC_BONUS_FIELDS = {"age", "annual_income", "family_income",
                         "monthly_income", "income", "disability_percentage"}


def _margin_bonus(conditions, user_profile) -> float:
    bonus = 0.0
    for cond in conditions:
        if cond.condition_type not in ("hard", "soft"):
            continue
        if cond.field not in NUMERIC_BONUS_FIELDS:
            continue
        pv = get_profile_value(cond.field, user_profile)
        if pv is None:
            continue
        try:
            pv = float(pv)
            cv = float(json.loads(cond.value) if isinstance(cond.value, str) else cond.value)
        except (ValueError, TypeError):
            continue
        if cond.operator == "gte" and pv > cv:
            margin = min((pv - cv) / cv, 1.0) if cv > 0 else 0.0
            if margin >= 0.20:
                bonus += 0.02
            if margin >= 0.50:
                bonus += 0.01
        elif cond.operator == "lte" and pv < cv:
            margin = min((cv - pv) / cv, 1.0) if cv > 0 else 0.0
            if margin >= 0.20:
                bonus += 0.02
            if margin >= 0.50:
                bonus += 0.01
    return min(bonus, 0.10)


# ── Main engine ───────────────────────────────────────────────────────────────

class EligibilityEngine:

    def __init__(self, config=None):
        self.cfg = config or {}
        self.w_hard    = self.cfg.get("WEIGHT_HARD",    0.40)
        self.w_soft    = self.cfg.get("WEIGHT_SOFT",    0.25)
        self.w_context = self.cfg.get("WEIGHT_CONTEXT",  0.35)
        self._normalizer = ProfileNormalizer.get_instance()

    def _get_profile_value(self, condition_field: str, user_profile: dict) -> Any:
        """
        Resolve a condition field to its value in the normalized profile.
        Profile should already be normalized by this point.
        Steps: canonical lookup → direct lookup → concept fallback.
        """
        canonical = self._normalizer.form_to_canonical.get(
            condition_field, condition_field
        )

        if canonical in user_profile and user_profile[canonical] is not None:
            return user_profile[canonical]

        if condition_field in user_profile and user_profile[condition_field] is not None:
            return user_profile[condition_field]

        return None

    def evaluate(self, scheme, user_profile: dict,
                 context_score: float = 0.5) -> EligibilityOutput:
        """
        Full three-pass evaluation.
        scheme        : Scheme ORM object (with .conditions loaded)
        user_profile  : flat dict from user.get_profile_dict()
        context_score : 0.0–1.0 from ContextualReasoner
        """
        # Lazy pipeline trigger - if no conditions, run pipeline
        conditions = list(scheme.condition_rows)
        if not conditions:
            # Try to run pipeline to extract conditions
            try:
                from app.pipeline import get_pipeline
                from flask import current_app
                from app import Scheme
                pipeline = get_pipeline(current_app._get_current_object())
                all_schemes = Scheme.query.filter_by(is_active=True).all()
                result = pipeline.run(scheme, all_schemes)
                db.session.commit()
                conditions = list(scheme.condition_rows)
                print(f"[LAZY] Pipeline ran for scheme {scheme.id}: {len(conditions)} conditions")
            except Exception as e:
                print(f"[LAZY] Pipeline error for scheme {scheme.id}: {e}")
        
        if not conditions:
            # Still no conditions → treat as unknown, low confidence
            return EligibilityOutput(
                result=POSSIBLE,
                confidence=0.10,
                blocking_reason="No conditions extracted for this scheme",
                missing_fields=[],
            )

        hard_conds       = [c for c in conditions if c.condition_type == "hard"       and not c.is_ambiguous]
        soft_conds       = [c for c in conditions if c.condition_type == "soft"       or  c.is_ambiguous]
        acquirable_conds = [c for c in conditions if c.condition_type == "acquirable"]

        # ── BASE PROFILE DEFAULTS (Must inject BEFORE evaluation) ───────────────
        # REMOVED: Assumption-based defaults were suppressing UNKNOWN → blocking adaptive questions
        # None = unknown → will trigger POSSIBLE status and question generation
        # Only keep truly universal defaults here if absolutely necessary
        
        all_results = []
        missing     = []
        acq_names   = [c.field for c in acquirable_conds]

        # ── Pass 1: Hard gate — group by field ───────────────────────────────
        # Numeric fields (age, income): use range-based AND logic
        # Categorical fields (gender, category, occupation): use OR logic
        hard_unknown = []
        soft_unknown = []
        hard_score   = 1.0
        NUMERIC_FIELDS = {"age", "age_min", "age_max", "age_min_for_overdraft", "age_max_for_overdraft",
                          "annual_income", "family_income", "monthly_income",
                          "income", "disability_percentage"}

        from collections import defaultdict
        by_field = defaultdict(list)
        for cond in hard_conds:
            by_field[cond.field].append(cond)

        for field_name, field_conds in by_field.items():
            # Skip non-answerable fields completely (bank internal, system states)
            if field_name in NON_ANSWERABLE_FIELDS:
                continue

            profile_val = self._get_profile_value(field_name, user_profile)
            if profile_val in [None, "", [], "unknown"] or profile_val is None:
                hard_unknown.append(field_name)
                hard_score = 0.0  # Missing field is UNKNOWN, not FAIL
                for cond in field_conds:
                    all_results.append(ConditionResult(cond.id, field_name, UNKNOWN_C,
                                        condition_type=getattr(cond, 'condition_type', 'soft'),
                                        reason=f"Field '{field_name}' not in profile"))
                continue

            fail_reasons = []

            if field_name in NUMERIC_FIELDS:
                # Range-based AND logic for numeric fields
                # Collect all gte conditions → max lower bound
                # Collect all lte conditions → min upper bound
                # Profile passes if: max_lower <= value <= min_upper
                gte_vals = []
                lte_vals = []
                for cond in field_conds:
                    cr = evaluate_single(cond, user_profile)
                    all_results.append(cr)
                    if cr.status == FAIL_R:
                        fail_reasons.append(cr.reason)
                    try:
                        if cond.operator == "gte":
                            gte_vals.append(float(cond.value) if not isinstance(cond.value, (int, float)) else cond.value)
                        elif cond.operator == "lte":
                            lte_vals.append(float(cond.value) if not isinstance(cond.value, (int, float)) else cond.value)
                    except (ValueError, TypeError):
                        pass

                max_lower = max(gte_vals) if gte_vals else float("-inf")
                min_upper = min(lte_vals) if lte_vals else float("inf")
                try:
                    pv = float(profile_val)
                except (ValueError, TypeError):
                    max_lower = float("inf")  # force fail

                if gte_vals or lte_vals:
                    if max_lower <= pv <= min_upper:
                        pass  # numeric range satisfied
                    else:
                        return EligibilityOutput(
                            result=INELIGIBLE,
                            confidence=1.0, hard_score=0.0, soft_score=0.0,
                            context_score=context_score,
                            blocking_field=field_name,
                            blocking_reason=f"value {pv} not in range [{max_lower}, {min_upper}]",
                            missing_fields=[], acquirable=acq_names,
                            condition_results=all_results,
                        )
            else:
                # OR logic for categorical fields (gender, category, occupation, etc.)
                any_pass = False
                for cond in field_conds:
                    cr = evaluate_single(cond, user_profile)
                    all_results.append(cr)
                    if cr.status == PASS_R:
                        any_pass = True
                    elif cr.status == FAIL_R:
                        fail_reasons.append(cr.reason)

                if not any_pass:
                    return EligibilityOutput(
                        result=INELIGIBLE,
                        confidence=1.0, hard_score=0.0, soft_score=0.0,
                        context_score=context_score,
                        blocking_field=field_name,
                        blocking_reason="; ".join(fail_reasons),
                        missing_fields=[], acquirable=acq_names,
                        condition_results=all_results,
                    )

        # ── Check for missing required fields (that weren't evaluated) ──────
        required_fields = set(by_field.keys())
        for field_name in required_fields:
            if field_name in NON_ANSWERABLE_FIELDS:
                continue
            profile_val = self._get_profile_value(field_name, user_profile)
            if profile_val in [None, "", [], "unknown"] or profile_val is None:
                if field_name not in hard_unknown:
                    hard_unknown.append(field_name)

        # ── Pass 2: Soft scoring ──────────────────────────────────────────────
        passed = failed = 0

        for cond in soft_conds:
            # Skip non-answerable fields in scoring
            if cond.field in NON_ANSWERABLE_FIELDS:
                continue
            cr = evaluate_single(cond, user_profile)
            all_results.append(cr)
            if cr.status == PASS_R:
                passed += 1
            elif cr.status == FAIL_R:
                failed += 1
            else:
                soft_unknown.append(cond.field)

        # ── Generate clarification hints for HARD unknown conditions ────────────────
        # Only generate clarifications if not already failed (i.e., still possible)
        clarifications = []
        
        # Check if any hard condition has failed
        has_hard_fail = False
        for cr in all_results:
            if cr.condition_type == "hard" and cr.status == FAIL_R:
                has_hard_fail = True
                break
        
        # Only add clarifications if not hard-failed
        if not has_hard_fail:
            # Use hard_unknown list - these are fields that are actually missing from profile
            # Find the actual conditions that correspond to these fields
            for field_name in hard_unknown:
                for cond in hard_conds:
                    if cond.field == field_name:
                        clarifications.append(format_condition(cond))
                        break  # Only add once per field
        
        # Deduplicate
        clarifications = sorted(set(clarifications))

        total_soft = passed + failed + len(soft_unknown)
        if total_soft > 0:
            soft_score = passed / (passed + failed + 0.5 * len(soft_unknown))
        else:
            soft_score = 1.0

        # ── Pass 3: Acquirable (informational only) ───────────────────────────
        # Already collected field names above

        # ── Coverage penalty ──────────────────────────────────────────────────
        # Only count answerable fields
        answerable_conds = [c for c in conditions if c.field not in NON_ANSWERABLE_FIELDS]
        known_count = sum(
            1 for c in answerable_conds
            if self._get_profile_value(c.field, user_profile) is not None
        )
        total_answerable = len(answerable_conds)
        coverage_penalty = known_count / total_answerable if total_answerable > 0 else 1.0
        coverage_penalty = max(0.3, coverage_penalty)   # floor at 0.3

        # ── Composite confidence ──────────────────────────────────────────────
        confidence = (
            self.w_hard    * hard_score    +
            self.w_soft    * soft_score    +
            self.w_context * context_score
        ) * coverage_penalty
        confidence = max(0.0, min(1.0, confidence))

        # ── Margin bonus (exceeding requirements) ─────────────────────────────
        if hard_score >= 1.0:
            margin = _margin_bonus(conditions, user_profile)
            confidence = min(1.0, confidence + margin)

        # ── Missing fields (hard unknowns first, then soft) ───────────────────
        # Filter out non-answerable fields AND convert to canonical forms
        missing_raw = [f for f in (hard_unknown + soft_unknown) if f not in NON_ANSWERABLE_FIELDS]
        # Deduplicate by canonical form
        seen_canonical = set()
        missing = []
        for f in missing_raw:
            canonical = get_canonical_field(f)
            if canonical not in seen_canonical:
                seen_canonical.add(canonical)
                missing.append(canonical)

        # ── Apply confidence penalty for missing required fields ──────────────
        if missing:
            confidence *= 0.5  # Penalty for missing required fields

        # ── Unmapped field handling (CHECK BEFORE RESULT) ───────────────────
        # Treat unmapped fields as MISSING (soft), not as HARD FAIL
        # This allows the adaptive questioning system to generate questions for them
        import json
        import os
        
        # Load field_to_concept from registry
        registry_path = os.path.join(os.path.dirname(__file__), '..', '..', 'concept_registry.json')
        field_to_concept = {}
        try:
            with open(registry_path, 'r') as f:
                registry = json.load(f)
                field_to_concept = registry.get('field_to_concept', {})
        except Exception:
            pass  # If registry fails, treat all as unmapped

        unmapped = []
        for field in missing:
            canonical = get_canonical_field(field)
            if canonical not in field_to_concept:
                unmapped.append(canonical)

        if unmapped:
            # Log for batch review (mapping expansion)
            from app.engine.unmapped_logger import log_unmapped_fields
            log_unmapped_fields(unmapped, getattr(scheme, 'id', None))
        
        # ── RESULT CLASSIFICATION (STRICT RULES) ─────────────────────────────
        # Import locally to avoid circular import
        from app.engine.questions import is_user_answerable
        
        # Analyze user-answerable HARD conditions ONLY (not system fields)
        user_hard_fail = False
        user_hard_missing = False
        
        for r in all_results:
            if not is_user_answerable(r.field):
                continue  # Skip SYSTEM fields
            cond_type = getattr(r, "condition_type", "soft")
            if cond_type != "hard":
                continue  # Only check HARD conditions
            
            raw_status = r.status
            if raw_status is None:
                status = "missing"
            else:
                status = str(raw_status).strip().lower()

            if status in ["fail", "false"]:
                user_hard_fail = True
            elif status in ["missing", "unknown", "none", ""]:
                user_hard_missing = True
        
        # Unmapped hard-condition fields: only count as missing if the scheme
        # actually has a hard condition on that field (not just concept-registry gaps)
        if unmapped:
            # Only flag missing if unmapped fields appear in the scheme's hard conditions
            unmapped_set = set(unmapped)
            hard_field_names = {c.field for c in hard_conds if is_user_answerable(c.field)}
            actually_missing_unmapped = unmapped_set & hard_field_names
            if actually_missing_unmapped:
                user_hard_missing = True
        
        # STRICT ORDER (LOCKED LOGIC): FAIL → MISSING → ELIGIBLE
        if user_hard_fail:
            # RULE 1: Any HARD USER FAIL → INELIGIBLE (Immediate mismatch)
            result = INELIGIBLE
        elif user_hard_missing:
            # RULE 2: No Hard Fail, but info is missing → POSSIBLE (Wait for answer)
            result = POSSIBLE
        else:
            # RULE 3: No Hard Fail, No Missing Info → FULLY ELIGIBLE
            result = ELIGIBLE

        return EligibilityOutput(
            result=result,
            confidence=round(confidence, 4),
            hard_score=round(hard_score, 4),
            soft_score=round(soft_score, 4),
            context_score=round(context_score, 4),
            coverage_penalty=round(coverage_penalty, 4),
            blocking_field=None,
            blocking_reason="",
            missing_fields=missing,
            acquirable=acq_names,
            condition_results=all_results,
            clarification_needed=clarifications,
        )
