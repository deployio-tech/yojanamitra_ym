"""
JSON Condition Validator
========================
Validates and transforms conditions from all_conditions.json through strict
whitelist and operator validation, producing DB-ready conditions.

Usage: python validate_json_conditions.py
"""

import json
import re
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Whitelist (41 fields)
ALLOWED_FIELDS = {
    # Demographics (8)
    "age", "gender", "category", "occupation", "religion", "marital_status", "num_daughters", "residence_type",
    # Location (5)
    "state", "residence", "is_rural", "is_urban", "state_residency",
    # Income (5)
    "annual_income", "income", "family_income", "is_bpl", "has_income_cert",
    # Education (4)
    "education_level", "is_student", "is_school_dropout", "is_first_gen_student",
    # Employment (7)
    "occupation", "is_farmer", "is_industrial_worker", "is_construction_worker", "is_self_employed", "is_pensioner", "loan_default_history",
    # Identification (5)
    "has_aadhaar", "has_bank_account", "has_ration_card", "has_pucca_house", "is_citizen",
    # Vulnerable (7)
    "is_disabled", "disability_percentage", "is_widow", "is_orphan", "is_landless", "is_tribal", "is_minority",
    # Other (3)
    "land_ownership_size", "has_vending_certificate", "residence"
}

VALID_OPERATORS = {'gte', 'lte', 'gt', 'lt', 'eq', 'neq', 'one_of', 'not_one_of', 'exists', 'not_exists'}

FIELD_MAP = {
    'age_min': 'age', 'age_max': 'age', 'min_age': 'age', 'max_age': 'age',
    'caste': 'category', 'caste_category': 'category', 'social_category': 'category',
    'annual_family_income': 'annual_income', 'family_income': 'annual_income',
    'household_income': 'annual_income', 'total_income': 'annual_income',
    'domicile_state': 'state', 'location_state': 'state', 'residence_state': 'state',
    'resident_state': 'state', 'state_residency': 'state', 'domicile': 'state',
    'is_agri_farmer': 'is_farmer', 'is_agriculturist': 'is_farmer',
    'is_emp_worker': 'is_industrial_worker', 'is_labour': 'is_industrial_worker',
    'is_labor': 'is_industrial_worker',
    'sex': 'gender',
    'is_bpl_card': 'is_bpl',
    'has_aadhar': 'has_aadhaar',
    'is_permanent_resident': 'is_citizen',
    'is_indian_citizen': 'is_citizen',
    'is_citizen_of_india': 'is_citizen',
    'citizenship': 'is_citizen',
}

OPERATOR_MAP = {
    'must_be': 'eq',
    'must_not_be': 'neq',
    'must_not_apply': 'neq',
    'max': 'lte',
    'min': 'gte',
    'must_not_exceed': 'lte',
    'one_of': 'one_of',
    'must_be_in': 'one_of',
    'must_not_be_included': 'not_one_of',
    'must_be_less_than': 'lt',
    'must_be_older_than': 'gt',
    'must_be_at_or_below': 'lte',
    'must_be_greater_than_or_equal_to': 'gte',
    'must_be_on_or_before': 'lte',
    'must_be_on_or_after': 'gte',
    'must_be_before': 'lt',
    'must_be_after': 'gt',
    'must_not_be_greater_than': 'lte',
    'must_be_related_to': None,  # Skip - too ambiguous
    'must_meet': 'eq',
}


def parse_between(value):
    """Parse 'between' values into [min, max] for gte + lte splitting."""
    if isinstance(value, list) and len(value) == 2:
        try:
            return [int(value[0]), int(value[1])]
        except (ValueError, TypeError):
            return None
    
    if isinstance(value, str):
        parts = re.split(r'[-to\s]+', value.strip())
        if len(parts) == 2:
            try:
                return [int(parts[0]), int(parts[1])]
            except ValueError:
                return None
    
    return None


def normalize_value(value, operator):
    """Normalize value type based on operator and field."""
    if value is None:
        return None
    
    if operator in ('one_of', 'not_one_of'):
        if isinstance(value, list):
            return [str(v).lower().strip() if isinstance(v, str) else v for v in value]
        elif isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return [v.strip() for v in value.split(',')]
        return [value]
    
    if isinstance(value, str):
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value.lower().strip()
    
    return value


def validate_condition(raw_cond, scheme_id):
    """Validate and transform a single raw condition. Returns list of conditions (may be 0, 1, or 2 for 'between')."""
    results = []
    
    field = raw_cond.get('field', '')
    raw_operator = raw_cond.get('operator', '')
    value = raw_cond.get('value')
    confidence = raw_cond.get('confidence', 0.5)
    source_text = raw_cond.get('source_text', '')[:200]
    
    if not field or not raw_operator:
        return results
    
    mapped_field = FIELD_MAP.get(field.lower().strip(), field.lower().strip())
    if mapped_field not in ALLOWED_FIELDS:
        return results
    
    if raw_operator == 'between':
        parsed = parse_between(value)
        if not parsed:
            return results
        
        min_val, max_val = parsed
        condition_type = 'hard' if confidence >= 0.8 else 'soft'
        
        results.append({
            'scheme_id': scheme_id,
            'field': mapped_field,
            'operator': 'gte',
            'value': min_val,
            'condition_type': condition_type,
            'confidence': confidence,
            'source': 'json_validation',
            'source_fragment': source_text
        })
        
        results.append({
            'scheme_id': scheme_id,
            'field': mapped_field,
            'operator': 'lte',
            'value': max_val,
            'condition_type': condition_type,
            'confidence': confidence,
            'source': 'json_validation',
            'source_fragment': source_text
        })
        return results
    
    if raw_operator == 'allowed_to_be':
        if isinstance(value, list):
            mapped_operator = 'one_of'
        else:
            mapped_operator = 'eq'
    else:
        mapped_operator = OPERATOR_MAP.get(raw_operator)
    
    if mapped_operator is None or mapped_operator not in VALID_OPERATORS:
        return results
    
    if value is None:
        return results
    
    normalized_value = normalize_value(value, mapped_operator)
    
    condition_type = 'hard' if confidence >= 0.8 else 'soft'
    
    results.append({
        'scheme_id': scheme_id,
        'field': mapped_field,
        'operator': mapped_operator,
        'value': normalized_value,
        'condition_type': condition_type,
        'confidence': confidence,
        'source': 'json_validation',
        'source_fragment': source_text
    })
    
    return results


def validate_json_conditions(json_path):
    """Load and validate all conditions from JSON file."""
    log.info(f"Loading {json_path}...")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    schemes = data.get('schemes', {})
    log.info(f"Found {len(schemes)} schemes in JSON")
    
    all_validated = []
    stats = {
        'total_raw': 0,
        'passed': 0,
        'rejected_field': 0,
        'rejected_operator': 0,
        'rejected_between': 0,
        'rejected_value': 0
    }
    
    for scheme_id_str, scheme in schemes.items():
        try:
            scheme_id = int(scheme_id_str)
        except (ValueError, TypeError):
            continue
        
        conditions = scheme.get('conditions', [])
        if not isinstance(conditions, list):
            continue
        
        for raw_cond in conditions:
            if not isinstance(raw_cond, dict):
                continue
            
            stats['total_raw'] += 1
            validated = validate_condition(raw_cond, scheme_id)
            
            if validated:
                all_validated.extend(validated)
                stats['passed'] += len(validated)
            else:
                field = raw_cond.get('field', '')
                raw_op = raw_cond.get('operator', '')
                mapped_field = FIELD_MAP.get(field.lower().strip(), field.lower().strip())
                
                if mapped_field not in ALLOWED_FIELDS:
                    stats['rejected_field'] += 1
                elif raw_op == 'between' and not parse_between(raw_cond.get('value')):
                    stats['rejected_between'] += 1
                elif OPERATOR_MAP.get(raw_op) is None:
                    stats['rejected_operator'] += 1
                else:
                    stats['rejected_value'] += 1
    
    log.info(f"\n{'='*60}")
    log.info("VALIDATION STATISTICS")
    log.info(f"{'='*60}")
    log.info(f"Total raw conditions: {stats['total_raw']}")
    log.info(f"Passed validation: {stats['passed']}")
    log.info(f"Rejected - field not in whitelist: {stats['rejected_field']}")
    log.info(f"Rejected - invalid operator: {stats['rejected_operator']}")
    log.info(f"Rejected - invalid between value: {stats['rejected_between']}")
    log.info(f"Rejected - invalid value: {stats['rejected_value']}")
    log.info(f"Pass rate: {stats['passed']/stats['total_raw']*100:.1f}%")
    
    return all_validated


def get_sample_conditions(conditions, n=5):
    """Return sample conditions for sanity check."""
    return conditions[:n]


if __name__ == '__main__':
    conditions = validate_json_conditions('all_conditions.json')
    
    log.info(f"\nValidated conditions collected: {len(conditions)}")
    
    samples = get_sample_conditions(conditions, 5)
    log.info("\n--- SAMPLE VALIDATED CONDITIONS (Sanity Check) ---")
    for i, c in enumerate(samples, 1):
        log.info(f"\n{i}. Scheme {c['scheme_id']}")
        log.info(f"   field: {c['field']}")
        log.info(f"   operator: {c['operator']}")
        log.info(f"   value: {c['value']} (type: {type(c['value']).__name__})")
        log.info(f"   type: {c['condition_type']}, conf: {c['confidence']}")
    
    with open('validated_json_conditions.json', 'w', encoding='utf-8') as f:
        json.dump(conditions, f, ensure_ascii=False, indent=2)
    log.info(f"\nSaved validated conditions to validated_json_conditions.json")
