"""
canonical_field_registry.py
Auto-built typed registry for question generation.

Scans the conditions table at startup to build a complete field schema:
- Type from profile_field_registry.json (authoritative)
- Min/max bounds from condition values in DB
- Allowed values for categorical fields
- Widget specification

Usage:
    from canonical_field_registry import get_field_schema, get_all_fields
    schema = get_field_schema('age')
    # {'field': 'age', 'data_type': 'integer', 'widget': 'number_input', ...}
"""
import json
import os
import sqlite3
import logging
from functools import lru_cache
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Path to registry files
# Navigate from app/engine up to project root
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_CURRENT_DIR, '..', '..'))
PROFILE_REGISTRY_PATH = os.path.join(_PROJECT_ROOT, 'profile_field_registry.json')
DB_PATH = os.path.join(_PROJECT_ROOT, 'instance', 'yojanamitra.db')

# Profile fields that are mandatory before evaluation
REQUIRED_PROFILE_FIELDS = [
    "age", "state", "gender", "income", "caste",
    "occupation", "education", "marital_status", "residence",
    "disability", "religion"
]

# Authoritative type mapping from profile registry
PROFILE_TYPE_MAP = {}

# Widget selection based on data type
WIDGET_FOR_TYPE = {
    "boolean": "toggle",
    "integer": "number_input",
    "float": "number_input",
    "categorical": "dropdown",
    "category": "dropdown",
    "string": "text_input",
}

# Human-readable question text (fallback)
QUESTION_TEXT_OVERRIDES = {
    "age": "What is your age in years?",
    "income": "What is your annual family income in rupees?",
    "annual_family_income": "What is your annual family income in rupees?",
    "income_annual": "What is your annual family income in rupees?",
    "gender": "What is your gender?",
    "caste": "What is your caste category?",
    "category": "What is your caste category?",
    "occupation": "What is your occupation?",
    "education": "What is your highest education level?",
    "state": "Which state do you reside in?",
    "residence": "Do you live in a rural or urban area?",
    "marital_status": "What is your marital status?",
    "religion": "What is your religion?",
    "disability": "Do you have a disability certificate?",
    "is_disabled": "Do you have a disability certificate?",
    "disability_percentage": "What is your disability percentage?",
    "domicile_state": "Which state do you have a domicile certificate for?",
    "is_student": "Are you currently enrolled as a student?",
    "is_farmer": "Are you a farmer or engaged in agricultural activities?",
    "is_bpl": "Are you registered under BPL (Below Poverty Line)?",
    "is_widow": "Are you a widow?",
    "is_senior_citizen": "Are you 60 years or older?",
    "is_minor": "Are you below 18 years of age?",
    "is_employed": "Are you currently employed?",
    "is_unemployed": "Are you currently unemployed?",
    "is_landless": "Do you own any agricultural land?",
    "own_agricultural_land": "How many acres of agricultural land do you own?",
    "land_size_acres": "How many acres of land do you own?",
    "bank_account_available": "Do you have a bank account?",
    "aadhaar_available": "Do you have an Aadhaar card?",
    "ration_card_available": "Do you have a ration card?",
    "is_tribal": "Are you a member of a Scheduled Tribe (ST)?",
    "is_sc": "Do you belong to Scheduled Caste (SC)?",
    "is_obc": "Do you belong to Other Backward Class (OBC)?",
    "is_ews": "Do you belong to Economically Weaker Section (EWS)?",
}

# Default bounds for common fields (human limits, not scheme-specific)
DEFAULT_BOUNDS = {
    "age": {"min": 0, "max": 120, "unit": "years"},
    "age_min": {"min": 0, "max": 120, "unit": "years"},
    "age_max": {"min": 0, "max": 120, "unit": "years"},
    "income": {"min": 0, "max": 1500000, "unit": "INR"},
    "annual_family_income": {"min": 0, "max": 1500000, "unit": "INR"},
    "income_annual": {"min": 0, "max": 1500000, "unit": "INR"},
    "annual_family_income_max": {"min": 0, "max": 1500000, "unit": "INR"},
    "income_annual_max": {"min": 0, "max": 1500000, "unit": "INR"},
    "disability_percentage": {"min": 0, "max": 100, "unit": "%"},
    "disability_percentage_min": {"min": 0, "max": 100, "unit": "%"},
    "land_size_acres": {"min": 0, "max": 100, "unit": "acres"},
    "land_owned_min_acres": {"min": 0, "max": 100, "unit": "acres"},
    "land_owned_max_acres": {"min": 0, "max": 100, "unit": "acres"},
    "num_daughters": {"min": 0, "max": 20, "unit": None},
    "num_daughters_max": {"min": 0, "max": 20, "unit": None},
    "max_children_covered": {"min": 0, "max": 20, "unit": None},
    "service_duration_min_years": {"min": 0, "max": 50, "unit": "years"},
    "has_service_duration_min_years": {"min": 0, "max": 50, "unit": "years"},
}

# Valid categorical values (pooled from all schemes)
CATEGORICAL_VALUES = {
    "gender": ["Male", "Female", "Other", "Transgender"],
    "caste": ["GEN", "OBC", "SC", "ST", "EWS"],
    "caste_category": ["GEN", "OBC", "SC", "ST", "EWS"],
    "category": ["GEN", "OBC", "SC", "ST", "EWS"],
    "marital_status": ["Single", "Married", "Divorced", "Widowed", "Separated"],
    "residence": ["Rural", "Urban", "Semi-Urban"],
    "employment_status": ["Employed", "Unemployed", "Self-Employed", "Student", "Retired"],
    "religion": ["Hindu", "Muslim", "Christian", "Sikh", "Buddhist", "Jain", "Parsi", "Other"],
    "education": ["None", "Primary", "Middle", "High School", "Intermediate", "Graduate", "Post-Graduate"],
    "education_level": ["None", "Primary", "Middle", "High School", "Intermediate", "Graduate", "Post-Graduate"],
    "education_level_min": ["None", "Primary", "Middle", "High School", "Intermediate", "Graduate", "Post-Graduate"],
    "occupation": ["Farmer", "Student", "Government Employee", "Private Employee", "Self-Employed", "Unemployed", "Retired", "Homemaker", "Business"],
    "state": [],  # Populated from scheme states
}

# Field to canonical name mapping
CANONICAL_ALIASES = {
    "age_min": "age",
    "age_max": "age",
    "num_daughters_max": "num_daughters",
    "income": "annual_family_income",
    "annual_family_income": "annual_family_income",
    "income_annual": "annual_family_income",
    "income_annual_max": "annual_family_income",
    "annual_family_income_max": "annual_family_income",
    "caste": "caste",
    "caste_category": "caste",
    "category": "caste",
    "domicile_state": "state",
    "gender": "gender",
    "marital_status": "marital_status",
    "residence": "residence",
    "employment_status": "employment_status",
    "education": "education",
    "education_level": "education",
    "education_level_min": "education",
    "occupation": "occupation",
    "religion": "religion",
    "disability": "disability",
    "disability_percentage": "disability_percentage",
    "disability_percentage_min": "disability_percentage",
    "land_size_acres": "land_size_acres",
    "land_owned_min_acres": "land_size_acres",
    "land_owned_max_acres": "land_size_acres",
    "is_disabled": "disability",
    "is_differently_abled": "disability",
    "is_bpl": "is_bpl",
    "is_widow": "is_widow",
    "is_senior_citizen": "is_senior_citizen",
    "is_minor": "is_minor",
    "is_employed": "employment_status",
    "is_unemployed": "employment_status",
    "is_student": "is_student",
    "is_farmer": "is_farmer",
    "is_landless": "is_landless",
    "is_tribal": "is_tribal",
    "is_sc": "is_sc",
    "is_obc": "is_obc",
    "is_ews": "is_ews",
}


def _load_profile_registry() -> dict:
    """Load profile field registry for type information."""
    global PROFILE_TYPE_MAP
    if PROFILE_TYPE_MAP:
        return PROFILE_TYPE_MAP
    
    try:
        with open(PROFILE_REGISTRY_PATH, 'r') as f:
            data = json.load(f)
        for field, spec in data.get('profile_fields', {}).items():
            PROFILE_TYPE_MAP[field] = {
                'type': spec.get('type', 'string'),
                'data_type': spec.get('type', 'string'),
                'concepts': spec.get('concepts', []),
                'form_mappings': spec.get('form_mappings', []),
            }
        logger.info(f"Loaded {len(PROFILE_TYPE_MAP)} fields from profile registry")
    except Exception as e:
        logger.warning(f"Could not load profile registry: {e}")
    
    return PROFILE_TYPE_MAP


def _get_db_connection():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)


def _scan_condition_values(field: str, conn) -> dict:
    """
    Scan condition table for all values used by a field.
    Returns min/max for numeric, allowed values for categorical.
    """
    result = {
        'min': None,
        'max': None,
        'values': set(),
        'operators': set(),
    }
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT operator, value, condition_type 
            FROM conditions 
            WHERE field = ?
        """, (field,))
        
        for op, val, cond_type in cursor.fetchall():
            result['operators'].add(op)
            
            if val is None:
                continue
            
            # Parse value
            try:
                # Try JSON array first
                if val.startswith('['):
                    vals = json.loads(val)
                    if isinstance(vals, list):
                        result['values'].update(str(v) for v in vals if v)
                        continue
                
                # Try numeric
                cleaned = str(val).replace(',', '').replace('₹', '').strip('"\'')
                num = float(cleaned)
                if result['min'] is None or num < result['min']:
                    result['min'] = num
                if result['max'] is None or num > result['max']:
                    result['max'] = num
            except (ValueError, TypeError):
                # Treat as string/categorical
                result['values'].add(str(val).strip('"'))
        
        result['values'] = sorted(result['values'])
        
    except Exception as e:
        logger.warning(f"Error scanning field {field}: {e}")
    
    return result


def get_canonical_name(field: str) -> str:
    """Map field to canonical name."""
    return CANONICAL_ALIASES.get(field, field)


def infer_data_type(field: str, operators: set, values: set) -> str:
    """Infer data type from operators and values."""
    # Boolean inference
    if operators <= {'eq', 'boolean', 'neq'} and not values:
        return 'boolean'
    
    if 'true' in values or 'false' in values:
        return 'boolean'
    
    # Numeric inference
    if operators & {'gte', 'lte', 'gt', 'lt'}:
        return 'integer'
    
    # Categorical
    if operators & {'in', 'one_of', 'neq'} and values:
        if len(values) <= 4:
            return 'categorical'
        return 'categorical'
    
    # Default based on field name
    if field.startswith('is_') or field.startswith('has_'):
        return 'boolean'
    
    return 'string'


def build_field_schema(field: str, conn) -> dict:
    """Build complete schema for a field."""
    canonical = get_canonical_name(field)
    
    # Get type from profile registry - ALWAYS authoritative
    profile_info = PROFILE_TYPE_MAP.get(canonical, PROFILE_TYPE_MAP.get(field, {}))
    profile_type = profile_info.get('type') if profile_info else None
    
    # Only infer type if profile registry has no type or has generic 'string'
    if not profile_type or profile_type == 'string':
        inferred = infer_data_type(field, set(), set())  # Default inference
        if profile_type == 'string':
            # Keep string for text fields, don't infer as categorical
            profile_type = 'string'
        else:
            profile_type = inferred
    
    # Scan condition values
    cond_info = _scan_condition_values(field, conn)
    
    # Get bounds
    bounds = {}
    if field in DEFAULT_BOUNDS:
        bounds = DEFAULT_BOUNDS[field].copy()
    else:
        if profile_type in ('integer', 'float') and (cond_info['min'] is not None or cond_info['max'] is not None):
            bounds['min'] = int(cond_info['min']) if cond_info['min'] else 0
            bounds['max'] = int(cond_info['max']) if cond_info['max'] else 1000000
    
    # Get allowed values for categorical
    allowed = None
    if field in CATEGORICAL_VALUES:
        allowed = CATEGORICAL_VALUES[field]
    elif cond_info['values']:
        allowed = cond_info['values'][:20]  # Limit to prevent abuse
    
    # Widget selection
    if profile_type in ('integer', 'float'):
        widget = 'number_input'
        if bounds.get('max', 100) <= 100 and 'percentage' in field.lower():
            widget = 'slider'
    elif profile_type == 'boolean':
        widget = 'toggle'
    elif profile_type == 'categorical' and allowed and len(allowed) <= 4:
        widget = 'radio'
    elif profile_type == 'categorical':
        widget = 'dropdown'
    else:
        widget = WIDGET_FOR_TYPE.get(profile_type, 'text_input')
    
    # Question text
    question_text = QUESTION_TEXT_OVERRIDES.get(
        field, 
        QUESTION_TEXT_OVERRIDES.get(canonical, f"Please provide your {canonical.replace('_', ' ')}")
    )
    
    return {
        'field': field,
        'canonical': canonical,
        'data_type': profile_type,
        'widget': widget,
        'min': bounds.get('min'),
        'max': bounds.get('max'),
        'unit': bounds.get('unit'),
        'allowed_values': allowed,
        'question_text': question_text,
    }


def _build_registry() -> dict:
    """Build complete registry from condition table + profile registry."""
    _load_profile_registry()
    
    registry = {
        'fields': {},
        'required_profile_fields': REQUIRED_PROFILE_FIELDS,
        'canonical_aliases': CANONICAL_ALIASES,
    }
    
    conn = _get_db_connection()
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT field FROM conditions")
        fields = [row[0] for row in cursor.fetchall()]
        
        logger.info(f"Building registry for {len(fields)} fields from condition table")
        
        for field in sorted(fields):
            schema = build_field_schema(field, conn)
            registry['fields'][field] = schema
        
        # Also include profile fields not in conditions
        for field, spec in PROFILE_TYPE_MAP.items():
            if field not in registry['fields']:
                canonical = get_canonical_name(field)
                ptype = spec.get('type', 'string')
                registry['fields'][field] = {
                    'field': field,
                    'canonical': canonical,
                    'data_type': ptype,
                    'widget': WIDGET_FOR_TYPE.get(ptype, 'text_input'),
                    'min': None,
                    'max': None,
                    'unit': None,
                    'allowed_values': CATEGORICAL_VALUES.get(field),
                    'question_text': QUESTION_TEXT_OVERRIDES.get(field, f"Please provide {field}"),
                }
        
        logger.info(f"Registry built: {len(registry['fields'])} fields total")
        
    finally:
        conn.close()
    
    return registry


# Cache the built registry
_CACHED_REGISTRY = None


def get_registry() -> dict:
    """Get the complete field registry."""
    global _CACHED_REGISTRY
    if _CACHED_REGISTRY is None:
        _CACHED_REGISTRY = _build_registry()
    return _CACHED_REGISTRY


def get_field_schema(field: str) -> Optional[dict]:
    """Get schema for a specific field."""
    canonical = get_canonical_name(field)
    registry = get_registry()
    return registry['fields'].get(field) or registry['fields'].get(canonical)


def get_all_fields() -> list:
    """Get all fields in the registry."""
    registry = get_registry()
    return list(registry['fields'].keys())


def get_required_fields() -> list:
    """Get required profile fields."""
    return REQUIRED_PROFILE_FIELDS


def get_widget_for_field(field: str) -> str:
    """Get widget type for a field."""
    schema = get_field_schema(field)
    return schema.get('widget', 'text_input') if schema else 'text_input'


def get_data_type_for_field(field: str) -> str:
    """Get data type for a field."""
    schema = get_field_schema(field)
    return schema.get('data_type', 'string') if schema else 'string'


def get_question_text_for_field(field: str) -> str:
    """Get question text for a field."""
    schema = get_field_schema(field)
    return schema.get('question_text', f"Please provide {field}") if schema else f"Please provide {field}"


def get_bounds_for_field(field: str) -> dict:
    """Get min/max bounds for a field."""
    schema = get_field_schema(field)
    if schema:
        return {'min': schema.get('min'), 'max': schema.get('max'), 'unit': schema.get('unit')}
    return {}


def reload_registry():
    """Force rebuild of registry (for testing)."""
    global _CACHED_REGISTRY, PROFILE_TYPE_MAP
    _CACHED_REGISTRY = None
    PROFILE_TYPE_MAP = {}
    return get_registry()


if __name__ == "__main__":
    # CLI test
    import sys
    logging.basicConfig(level=logging.INFO)
    
    registry = get_registry()
    print(f"Registry built: {len(registry['fields'])} fields")
    print(f"Required profile fields: {len(REQUIRED_PROFILE_FIELDS)}")
    print()
    
    # Show sample schemas
    for field in ['age', 'income', 'gender', 'caste', 'occupation', 'is_farmer', 'disability_percentage']:
        schema = registry['fields'].get(field)
        if schema:
            print(f"{field}:")
            print(f"  type: {schema['data_type']}, widget: {schema['widget']}")
            print(f"  question: {schema['question_text']}")
            if schema.get('allowed_values'):
                print(f"  options: {schema['allowed_values']}")
            if schema.get('max'):
                print(f"  bounds: {schema['min']}-{schema['max']} {schema.get('unit', '')}")
            print()