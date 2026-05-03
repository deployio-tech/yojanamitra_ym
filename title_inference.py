"""
Title Inference Module
=====================
Strict pattern-based inference from scheme titles for controlled semantic augmentation.

Rules:
- Pattern-based (regex with word boundaries)
- Lower confidence than extraction (0.6-0.8)
- Never override existing conditions
- Pass through conflict detection
- Supplement only, never replace

Usage: python title_inference.py
"""

import re
import json
import logging
import sys
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Whitelist (must match ALLOWED_FIELDS in supplement_conditions.py)
ALLOWED_FIELDS = {
    "age", "gender", "category", "occupation", "religion", "marital_status", 
    "num_daughters", "residence_type", "state", "residence", "is_rural", 
    "is_urban", "state_residency", "annual_income", "income", "family_income", 
    "is_bpl", "has_income_cert", "education_level", "is_student", 
    "is_school_dropout", "is_first_gen_student", "occupation", "is_farmer", 
    "is_industrial_worker", "is_construction_worker", "is_self_employed", 
    "is_pensioner", "loan_default_history", "has_aadhaar", "has_bank_account", 
    "has_ration_card", "has_pucca_house", "is_citizen", "is_disabled", 
    "disability_percentage", "is_widow", "is_orphan", "is_landless", "is_tribal", 
    "is_minority", "land_ownership_size", "has_vending_certificate", "residence"
}

# Strict patterns: (regex, field, value, confidence)
# Only patterns with explicit "for X" or clear eligibility context
TITLE_PATTERNS = [
    # High confidence (0.75-0.8) - explicit "for X" structure
    (r"\bfor\s+(women|female)\b",         "gender",        "FEMALE",     0.8),
    (r"\bfor\s+(men|male)s?\b",           "gender",        "MALE",       0.8),
    (r"\bfor\s+(farmers?|cultivators?)\b","is_farmer",     True,         0.8),
    (r"\bfor\s+(students?|scholars?)\b",  "is_student",    True,         0.8),
    (r"\bfor\s+(widows?)\b",              "is_widow",      True,         0.8),
    (r"\bfor\s+(orphans?)\b",             "is_orphan",     True,         0.6),
    
    # High confidence (0.75) - explicit category with "for"
    (r"\bfor\s+(sc|st|scheduled caste|scheduled tribe)\b", 
                                              "category",    ["SC","ST"],  0.75),
    (r"\bfor\s+(obc|other backward class)\b", 
                                              "category",    "OBC",       0.75),
    
    # Medium confidence (0.65-0.7) - "for X scheme" or explicit context
    (r"\bwomen[\s']+(scheme|welfare|development)\b", 
                                              "gender",      "FEMALE",    0.7),
    (r"\bfarmer[\s']+(scheme|welfare)\b",  "is_farmer",    True,        0.7),
    (r"\bfor\s+(minorities?|minority)\b",  "is_minority",  True,        0.65),
    
    # Economic (0.7) - explicit poverty indicators
    (r"\b(bpl|below poverty line)\b",     "is_bpl",       True,        0.7),
    
    # Lower confidence (0.6) - tribal (needs explicit context)
    (r"\btribal\s+(welfare|development|scheme)\b", 
                                              "is_tribal",   True,        0.6),
]

# Compile patterns for efficiency
COMPILED_PATTERNS = [
    (re.compile(pattern, re.I), field, value, conf) 
    for pattern, field, value, conf in TITLE_PATTERNS
]


def normalize_title(title):
    """Normalize title once: lowercase, strip, collapse whitespace."""
    if not title:
        return ""
    return re.sub(r"\s+", " ", title.lower().strip())


def extract_conditions_from_title(title, scheme_id):
    """
    Extract conditions from a normalized title using strict patterns.
    Returns list of condition dicts (may be empty).
    """
    if not title:
        return []
    
    conditions = []
    matched_fields = {}  # field -> (condition, confidence) - keep highest only
    
    # Check for OR-group trigger: explicit "and" between different eligible groups
    or_trigger = re.search(
        r"\b(women|female|sc|st|obc|farmers?|workers?)\b.*\band\b.*(women|female|sc|st|obc|farmers?|workers?)\b",
        title, re.I
    )
    
    or_group_id = None
    if or_trigger:
        or_group_id = f"TITLE_OR_{scheme_id}"
    
    # Apply patterns
    for pattern, field, value, conf in COMPILED_PATTERNS:
        if field not in ALLOWED_FIELDS:
            continue
            
        match = pattern.search(title)
        if not match:
            continue
        
        # Skip if already matched this field with higher confidence
        if field in matched_fields:
            existing_conf = matched_fields[field][1]
            if existing_conf >= conf:
                continue
        
        # Build condition
        cond = {
            "scheme_id": scheme_id,
            "field": field,
            "operator": "eq" if isinstance(value, bool) else "one_of" if isinstance(value, list) else "eq",
            "value": value,
            "condition_type": "hard",
            "confidence": conf,
            "source": "title_inference",
            "source_fragment": title[:100],
        }
        
        if or_group_id:
            cond["logic_group"] = or_group_id
        
        matched_fields[field] = (cond, conf)
    
    # Convert matched fields to list
    for field, (cond, _) in matched_fields.items():
        conditions.append(cond)
    
    return conditions


def load_schemes():
    """Load schemes from all_schemes_export.json."""
    json_path = 'all_schemes_export.json'
    log.info(f"Loading {json_path}...")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        schemes = json.load(f)
    
    log.info(f"Loaded {len(schemes)} schemes")
    return schemes


def run_title_inference():
    """Main function to run title inference."""
    
    sys.path.insert(0, '.')
    from app import app, db, Condition
    
    # Load schemes
    schemes = load_schemes()
    
    # Load existing conditions from DB (to avoid duplicates)
    log.info("Loading existing conditions from database...")
    existing_by_scheme = {}
    with app.app_context():
        for c in Condition.query.all():
            sid = c.scheme_id
            if sid not in existing_by_scheme:
                existing_by_scheme[sid] = set()
            existing_by_scheme[sid].add(c.field)
    
    log.info(f"Checked {len(existing_by_scheme)} schemes in DB")
    
    # Extract conditions from titles
    log.info("Extracting conditions from titles...")
    all_inferred = []
    stats = {
        "total_schemes": len(schemes),
        "schemes_with_match": 0,
        "conditions_extracted": 0,
        "skipped_already_exists": 0,
    }
    
    for scheme in schemes:
        scheme_id = scheme.get('id')
        if not scheme_id:
            continue
        
        title = normalize_title(scheme.get('name', ''))
        if not title:
            continue
        
        # Extract conditions
        conditions = extract_conditions_from_title(title, scheme_id)
        
        if not conditions:
            continue
        
        stats["schemes_with_match"] += 1
        
        # Filter out if field already exists in DB
        existing_fields = existing_by_scheme.get(scheme_id, set())
        for cond in conditions:
            if cond['field'] in existing_fields:
                stats["skipped_already_exists"] += 1
                continue
            all_inferred.append(cond)
            stats["conditions_extracted"] += 1
    
    log.info(f"\n{'='*60}")
    log.info("TITLE INFERENCE STATISTICS")
    log.info(f"{'='*60}")
    log.info(f"Total schemes processed: {stats['total_schemes']}")
    log.info(f"Schemes with pattern match: {stats['schemes_with_match']}")
    log.info(f"Conditions extracted: {stats['conditions_extracted']}")
    log.info(f"Skipped (field exists): {stats['skipped_already_exists']}")
    
    if not all_inferred:
        log.info("No conditions to add.")
        return []
    
    # Show sample conditions
    log.info("\n--- SAMPLE INFERRED CONDITIONS ---")
    for i, c in enumerate(all_inferred[:5], 1):
        log.info(f"  {i}. Scheme {c['scheme_id']}: {c['field']} = {c['value']} (conf={c['confidence']})")
    
    return all_inferred


def save_to_db(conditions):
    """Save conditions to database via controlled supplement."""
    
    if not conditions:
        log.info("No conditions to save.")
        return
    
    sys.path.insert(0, '.')
    from app import app, db, Condition
    from supplement_conditions import controlled_supplement
    
    with app.app_context():
        # Load current DB conditions
        log.info("Loading current DB conditions...")
        db_conditions = []
        for c in Condition.query.all():
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
            db_conditions.append(cond_dict)
        
        log.info(f"Current DB conditions: {len(db_conditions)}")
        log.info(f"New title_inference conditions: {len(conditions)}")
        
        # Run controlled supplement
        log.info("\nRunning controlled supplement...")
        final = controlled_supplement(db_conditions, conditions)
        log.info(f"Final conditions: {len(final)}")
        
        # Clear and save
        log.info("\nSaving to database...")
        Condition.query.delete()
        db.session.commit()
        
        for cond in final:
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
                source=cond.get('source', 'title_inference'),
                source_fragment=cond.get('source_fragment', '')
            )
            db.session.add(c)
        
        db.session.commit()
        
        # Final stats
        total = Condition.query.count()
        sources = db.session.execute(db.text(
            'SELECT source, COUNT(*) FROM condition GROUP BY source ORDER BY COUNT(*) DESC'
        )).fetchall()
        
        log.info(f"\n{'='*60}")
        log.info("TITLE INFERENCE COMPLETE")
        log.info(f"{'='*60}")
        log.info(f"Total conditions: {total}")
        log.info("\nSource distribution:")
        for src, cnt in sources:
            log.info(f"  {src}: {cnt}")


if __name__ == '__main__':
    conditions = run_title_inference()
    
    if conditions:
        save_to_db(conditions)
    else:
        log.info("No new conditions extracted from titles.")
