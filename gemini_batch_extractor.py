"""
Gemini Batch Condition Extractor (Production-Grade)
===================================================
A deterministic rule compiler that converts unstructured scheme text into 
strictly typed database conditions.

Optimized for:
- Whitelist Enforcement (No ghost fields)
- Logic Grouping (Handling 'OR' conditions correctly)
- Type Integrity (Native Booleans & Floats)
- Balanced Speed (~600-800 RPM)
"""

import os
import sys
import json
import time
import logging
from datetime import datetime

# Insert local path to ensure app imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, db, Condition
    from app.pipeline.extractor import GeminiExtractor
except ImportError:
    print("CRITICAL: Could not find 'app' or 'GeminiExtractor'. Run from project root.")
    sys.exit(1)

# ⚡ PRODUCTION PERFORMANCE CONFIG
BATCH_SIZE = 50 
DELAY_BETWEEN_BATCHES = 1.0     # Cool-down for DB commits
DELAY_BETWEEN_REQUESTS = 0.08   # ~750 RPM: Fast but avoids 429 errors
JSON_FILE = 'all_schemes_fixed.json'

# 🔒 THE DATA CONTRACT (STRICT WHITELIST)
ALLOWED_FIELDS = {
    "age", "gender", "category", "occupation", "annual_income", 
    "state", "state_residency", "residence", "is_student", "is_farmer", 
    "is_bpl", "is_disabled", "disability_percentage", "land_ownership_size",
    "has_vending_certificate", "has_bank_account", "has_income_cert", "loan_default_history", 
    "education_level", "is_minority", "is_rural", "is_urban", "is_citizen",
    "is_industrial_worker", "is_widow", "is_self_employed", "religion",
    "income", "family_income", "has_aadhaar", "has_ration_card", "has_pucca_house",
    "is_construction_worker", "is_landless", "is_orphan", "is_pensioner",
    "is_tribal", "is_first_gen_student", "is_school_dropout", "num_daughters",
    "marital_status", "residence_type"
}

VALID_OPERATORS = {'eq', 'neq', 'gte', 'lte', 'one_of', 'exists', 'range'}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class RuleCompiler:
    """Ensures AI output matches the production database schema."""
    
    @staticmethod
    def validate_and_clean(cond):
        field = cond.get('field')
        operator = cond.get('operator')
        value = cond.get('value')

        # 1. Field Guard
        if field not in ALLOWED_FIELDS:
            return None

        # 2. Operator Normalization
        op_map = {'==': 'eq', '<=': 'lte', '>=': 'gte', 'in': 'one_of', 'between': 'range'}
        operator = op_map.get(operator, operator)
        if operator not in VALID_OPERATORS:
            return None

        # 3. Type Casting (Booleans)
        if isinstance(value, str):
            if value.lower() in ['true', 'yes', '1']: value = True
            elif value.lower() in ['false', 'no', '0']: value = False

        # 4. Type Casting (Numbers)
        if field in ["disability_percentage", "land_ownership_size", "annual_income", "age"]:
            try:
                if isinstance(value, (int, float)):
                    pass
                elif isinstance(value, str):
                    value = float(value.replace(',', ''))
            except:
                return None

        # 5. Logic Group Integrity
        # If part of an OR group, force 'hard' to prevent scoring conflicts
        if cond.get('logic_group') and cond.get('condition_type') == 'soft':
            cond['condition_type'] = 'hard'

        return {
            'field': field,
            'operator': operator,
            'value': value,
            'condition_type': cond.get('condition_type', 'hard'),
            'logic_group': cond.get('logic_group'),
            'confidence': cond.get('confidence', 1.0),
            'source_fragment': cond.get('source_fragment', '')
        }

def save_to_db(scheme_id, conditions):
    """Saves a batch of conditions to the DB using an atomic transaction."""
    with app.app_context():
        try:
            if not conditions:
                return 0
            
            # Atomic: Remove old rules, insert new verified rules
            Condition.query.filter_by(scheme_id=scheme_id).delete()
            
            count = 0
            for raw_c in conditions:
                clean_c = RuleCompiler.validate_and_clean(raw_c)
                if not clean_c:
                    continue
                
                db_record = Condition(
                    scheme_id=scheme_id,
                    field=clean_c['field'],
                    operator=clean_c['operator'],
                    value=json.dumps(clean_c['value']), # Standardized JSON storage
                    condition_type=clean_c['condition_type'],
                    logic_group=clean_c['logic_group'],
                    confidence=clean_c['confidence'],
                    source_fragment=clean_c['source_fragment'],
                    source='gemini_compiler_v2'
                )
                db.session.add(db_record)
                count += 1
            
            db.session.commit()
            return count
        except Exception as e:
            db.session.rollback()
            log.error(f"DB Error [ID {scheme_id}]: {e}")
            return 0

def get_full_text(scheme):
    """Combines fields for maximum extraction context."""
    parts = [scheme.get('name', ''), scheme.get('eligibility', ''), scheme.get('description', '')]
    text = ' '.join(parts).strip()
    return text[:8000] # Token safety limit

def run_extraction():
    API_KEY = os.environ.get('GEMINI_API_KEY', 'PASTE_YOUR_GEMINI_API_KEY_HERE')
    if not API_KEY:
        log.error("Missing GEMINI_API_KEY environment variable.")
        return

    gemini = GeminiExtractor(API_KEY, model_name="gemini-flash-latest")
    
    # Load Source File
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            schemes = json.load(f)
    except FileNotFoundError:
        log.error(f"File {JSON_FILE} not found.")
        return

    log.info(f"🚀 Starting Extraction: {len(schemes)} schemes.")
    start_time = time.time()
    total_conds = 0

    for i, scheme in enumerate(schemes):
        sid = scheme.get('id')
        text = get_full_text(scheme)

        if not text:
            continue

        try:
            # Call the AI Extractor
            raw_conditions, _, error, low_conf = gemini.extract(text, scheme)
            
            if not error and raw_conditions:
                saved = save_to_db(sid, raw_conditions)
                total_conds += saved
                
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed
                    eta = (len(schemes) - (i + 1)) / rate
                    print(f"Progress: {i+1}/{len(schemes)} | Rules: {total_conds} | ETA: {eta/60:.1f}m")

            # Balanced Throttling
            if (i + 1) % BATCH_SIZE == 0:
                time.sleep(DELAY_BETWEEN_BATCHES)
            else:
                time.sleep(DELAY_BETWEEN_REQUESTS)

        except Exception as e:
            log.error(f"Critical Failure on Scheme {sid}: {e}")

    print(f"\n✅ Finished! Total Rules Compiled: {total_conds}")

if __name__ == "__main__":
    run_extraction()
