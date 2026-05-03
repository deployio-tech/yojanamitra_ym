"""
Controlled Supplement Script
===========================
Safely merges new extraction (base) with existing conditions.

Strategy: New as base + selectively add from existing with strict validation.

Usage: python supplement_conditions.py
"""

import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════════

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

MAX_CONDITIONS_PER_FIELD = 3  # Safety limit per field per scheme


# ════════════════════════════════════════════════════════════════════════════════
# NORMALIZATION FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════════

def normalize_value(v):
    """Normalize value for comparison - handles JSON strings and lists."""
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except (json.JSONDecodeError, ValueError):
            return v.lower().strip() if isinstance(v, str) else v
    
    if isinstance(v, list):
        return sorted(str(x).lower() for x in v)
    
    if isinstance(v, (int, float)):
        return float(v)
    
    if isinstance(v, str):
        v = v.lower().strip()
        if v in ['true', 'yes', '1']:
            return True
        if v in ['false', 'no', '0']:
            return False
        return v
    
    return v


def safe_compare(v):
    """Safe number comparison - returns float or original."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


def normalize_operator(op):
    """Normalize operator to standard form."""
    op_map = {
        '==': 'eq', '=': 'eq',
        '>=': 'gte', '=>': 'gte',
        '<=': 'lte', '=<': 'lte',
        '>': 'gt', '<': 'lt',
        '!=': 'neq',
        'in': 'one_of', 'one_of': 'one_of',
        'not_in': 'not_one_of', 'not_one_of': 'not_one_of',
    }
    return op_map.get(op.lower().strip(), op.lower().strip())


# ════════════════════════════════════════════════════════════════════════════════
# CONFLICT DETECTION
# ════════════════════════════════════════════════════════════════════════════════

def values_conflict(c1, c2):
    """
    Check if two conditions on the SAME FIELD conflict.
    
    Returns True if conflict, False if compatible.
    
    Rules:
    - eq vs eq: different values = conflict
    - eq vs gte/lte: eq value outside range = conflict
    - eq vs eq: same value = not conflict (duplicate)
    """
    # Normalize operators
    op1 = normalize_operator(c1.get('operator', 'eq'))
    op2 = normalize_operator(c2.get('operator', 'eq'))
    
    v1 = safe_compare(normalize_value(c1.get('value')))
    v2 = safe_compare(normalize_value(c2.get('value')))
    
    # eq vs eq: different values = conflict
    if op1 == 'eq' and op2 == 'eq':
        return v1 != v2
    
    # Normalize order: put eq first
    if op1 != 'eq' and op2 == 'eq':
        op1, op2 = op2, op1
        v1, v2 = v2, v1
    
    # eq vs gte/lte: eq outside range = conflict
    if op1 == 'eq' and op2 in ['gte', 'lte', 'gt', 'lt']:
        if op2 == 'gte' and isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            if v1 < v2:
                return True
        if op2 == 'lte' and isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            if v1 > v2:
                return True
        if op2 == 'gt' and isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            if v1 <= v2:
                return True
        if op2 == 'lt' and isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            if v1 >= v2:
                return True
    
    return False


# ════════════════════════════════════════════════════════════════════════════════
# MERGE FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════════

def make_key(cond):
    """Create dedup key for a condition."""
    value = normalize_value(cond.get('value'))
    # Convert list to tuple for hashing
    if isinstance(value, list):
        value = tuple(value)
    return (
        cond.get('scheme_id'),
        normalize_operator(cond.get('operator', 'eq')),
        value
    )


def merge_eq_values(conditions):
    """
    Merge multiple eq conditions on same field into one_of.
    
    Example: category = SC, category = ST → category one_of [SC, ST]
    """
    # Group by scheme_id and field
    by_field = {}
    others = []
    
    for c in conditions:
        field = c.get('field')
        op = normalize_operator(c.get('operator', 'eq'))
        
        if op == 'eq' and field:
            key = (c.get('scheme_id'), field)
            if key not in by_field:
                by_field[key] = []
            by_field[key].append(c)
        else:
            others.append(c)
    
    # Merge eq values into one_of
    merged = list(others)
    for key, eq_conds in by_field.items():
        if len(eq_conds) > 1:
            # Multiple eq values - merge to one_of
            values = [normalize_value(c.get('value')) for c in eq_conds]
            values = [v for v in values if not isinstance(v, bool)]
            if values:
                merged.append({
                    'scheme_id': key[0],
                    'field': key[1],
                    'operator': 'one_of',
                    'value': json.dumps(values),
                    'condition_type': 'hard',
                    'confidence': 1.0,
                    'source_fragment': f'merged from {len(eq_conds)} eq conditions'
                })
        else:
            # Single eq - keep as is
            merged.extend(eq_conds)
    
    return merged


def deduplicate_strict(conditions):
    """Strict deduplication by scheme_id + field + operator + value."""
    seen = set()
    unique = []
    
    for c in conditions:
        key = make_key(c)
        if key not in seen:
            seen.add(key)
            unique.append(c)
    
    return unique


def controlled_supplement(new_conditions, existing_conditions):
    """
    Controlled supplement: New as base + selectively add from existing.
    
    Rules:
    1. New extraction is source of truth
    2. Add from existing only if: passes ALL filters
    3. Strict conflict detection
    4. Safety limits enforced
    """
    
    log.info(f"Starting controlled supplement...")
    log.info(f"New (base): {len(new_conditions)} conditions")
    log.info(f"Existing: {len(existing_conditions)} conditions")
    
    # Build new index for fast lookup
    new_index = {}
    new_by_scheme_field = {}  # (scheme_id, field) -> [conditions]
    
    for c in new_conditions:
        key = (c.get('scheme_id'), c.get('field'))
        new_index[key] = c
        
        skey = (c.get('scheme_id'), c.get('field'))
        if skey not in new_by_scheme_field:
            new_by_scheme_field[skey] = []
        new_by_scheme_field[skey].append(c)
    
    # Filter and add from existing
    supplement = []
    skipped_invalid_field = 0
    skipped_duplicate = 0
    skipped_conflict = 0
    skipped_limit = 0
    
    for c in existing_conditions:
        field = c.get('field', '')
        
        # Filter 1: Must be in whitelist
        if field not in ALLOWED_FIELDS:
            skipped_invalid_field += 1
            continue
        
        scheme_id = c.get('scheme_id')
        skey = (scheme_id, field)
        
        # Filter 2: Safety limit per field per scheme
        if skey in new_by_scheme_field:
            if len(new_by_scheme_field[skey]) >= MAX_CONDITIONS_PER_FIELD:
                skipped_limit += 1
                continue
        
        # Filter 3: Check if exists in new (exact match)
        existing_key = make_key(c)
        in_new = any(
            make_key(nc) == existing_key 
            for nc in new_by_scheme_field.get(skey, [])
        )
        if in_new:
            skipped_duplicate += 1
            continue
        
        # Filter 4: Check for conflicts
        same_field = new_by_scheme_field.get(skey, [])
        has_conflict = False
        
        for existing in same_field:
            if values_conflict(existing, c):
                has_conflict = True
                break
        
        if has_conflict:
            skipped_conflict += 1
            continue
        
        # Passed all filters - add to supplement
        supplement.append(c)
        
        # Update index
        if skey not in new_by_scheme_field:
            new_by_scheme_field[skey] = []
        new_by_scheme_field[skey].append(c)
    
    # Merge: new + supplement
    merged = new_conditions + supplement
    
    # Merge multiple eq values into one_of
    merged = merge_eq_values(merged)
    
    # Final deduplication
    merged = deduplicate_strict(merged)
    
    # Statistics
    log.info(f"\n=== SUPPLEMENT STATISTICS ===")
    log.info(f"Supplement added: {len(supplement)}")
    log.info(f"Skipped (invalid field): {skipped_invalid_field}")
    log.info(f"Skipped (duplicate): {skipped_duplicate}")
    log.info(f"Skipped (conflict): {skipped_conflict}")
    log.info(f"Skipped (limit): {skipped_limit}")
    log.info(f"Final total: {len(merged)}")
    
    return merged


# ════════════════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ════════════════════════════════════════════════════════════════════════════════

def run_supplement():
    """Main function to run controlled supplement."""
    
    import sys
    sys.path.insert(0, '.')
    
    from app import app, db, Condition
    
    with app.app_context():
        # Load validated JSON conditions (supplement source)
        log.info("Loading validated JSON conditions...")
        try:
            with open('validated_json_conditions.json', 'r', encoding='utf-8') as f:
                json_conditions = json.load(f)
            log.info(f"Loaded {len(json_conditions)} validated conditions from JSON")
        except FileNotFoundError:
            log.error("validated_json_conditions.json not found. Run validate_json_conditions.py first.")
            return
        except json.JSONDecodeError as e:
            log.error(f"Invalid JSON: {e}")
            return
        
        # Load DB conditions as base
        log.info("Loading conditions from database...")
        
        all_conds = Condition.query.all()
        
        # DB conditions are base, JSON conditions are supplement
        base_conditions = []
        existing_conditions = []  # manual/title_inference go to supplement
        
        for c in all_conds:
            cond_dict = {
                'id': c.id,
                'scheme_id': c.scheme_id,
                'field': c.field,
                'operator': c.operator,
                'value': c.value,
                'condition_type': c.condition_type,
                'confidence': c.confidence,
                'source': getattr(c, 'source', 'unknown'),
                'source_fragment': getattr(c, 'source_fragment', '')
            }
            
            source = cond_dict['source']
            if source in ['production_v2', 'production_v3_turbo', 'extraction', 'gemini_compiler_v2']:
                base_conditions.append(cond_dict)
            else:
                existing_conditions.append(cond_dict)
        
        log.info(f"Base (DB production): {len(base_conditions)}")
        log.info(f"Supplement (JSON): {len(json_conditions)}")
        log.info(f"Existing (manual/title_inference): {len(existing_conditions)}")
        
        # Run controlled supplement
        # controlled_supplement(new_conditions, existing_conditions)
        # - new_conditions = base (kept as-is)
        # - existing_conditions = supplement source (filtered before adding)
        log.info("\nStarting controlled supplement...")
        
        # Step 1: Add JSON conditions to DB base
        merged1 = controlled_supplement(base_conditions, json_conditions)
        log.info(f"After JSON supplement: {len(merged1)} conditions")
        
        # Step 2: Add manual/title_inference conditions
        merged2 = controlled_supplement(merged1, existing_conditions)
        log.info(f"After existing supplement: {len(merged2)} conditions")
        
        final_conditions = merged2
        
        # Save to database
        log.info("\nSaving to database...")
        
        # Clear all conditions
        Condition.query.delete()
        db.session.commit()
        
        # Insert final conditions (JSON-encode list values)
        for cond in final_conditions:
            value = cond['value']
            if isinstance(value, (list, dict)):
                value = json.dumps(value)
            elif not isinstance(value, str):
                value = str(value) if value is not None else None
            
            c = Condition(
                scheme_id=cond['scheme_id'],
                field=cond['field'],
                operator=cond['operator'],
                value=value,
                condition_type=cond.get('condition_type', 'soft'),
                confidence=cond.get('confidence', 0.5),
                source=cond.get('source', 'supplement_v1'),
                source_fragment=cond.get('source_fragment', '')
            )
            db.session.add(c)
        
        db.session.commit()
        
        # Final statistics
        total = Condition.query.count()
        schemes = len(set([c.scheme_id for c in Condition.query.all()]))
        
        # Field distribution
        fields = {}
        for c in Condition.query.all():
            f = c.field
            fields[f] = fields.get(f, 0) + 1
        
        log.info(f"\n{'='*60}")
        log.info("SUPPLEMENT COMPLETE")
        log.info(f"{'='*60}")
        log.info(f"Total conditions: {total}")
        log.info(f"Schemes covered: {schemes}")
        log.info(f"Unique fields: {len(fields)}")
        log.info(f"\nTop 15 fields:")
        for f, count in sorted(fields.items(), key=lambda x: -x[1])[:15]:
            log.info(f"  {f}: {count}")


if __name__ == '__main__':
    run_supplement()
