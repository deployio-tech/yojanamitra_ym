"""
Production-Grade AI Condition Extractor — TURBO EDITION
=========================================================
Async-concurrent extraction with dynamic rate limiting,
bulk DB writes, and adaptive backoff for maximum throughput.

Usage: python production_extractor.py
"""

import os
import sys
import json
import time
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Lock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Condition
from app.pipeline.extractor import GeminiExtractor

# ⚡ PERFORMANCE CONFIG
CONCURRENCY        = 20          # Parallel in-flight requests (tune: 10–40)
TARGET_RPM         = 700         # Stay under 750 RPM hard limit
BATCH_SIZE         = 200         # DB flush every N schemes (not a throttle)
DB_FLUSH_INTERVAL  = 30          # Also flush every N seconds if batch not full
BACKOFF_BASE       = 1.5         # Exponential backoff multiplier on 429/503
MAX_RETRIES        = 4
JSON_FILE          = 'all_schemes_export.json'

# Dedicated thread pool sized to match concurrency
# (prevents default pool exhaustion when 20 threads all call gemini.extract)
THREAD_POOL        = ThreadPoolExecutor(max_workers=CONCURRENCY + 4)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════════════
# PART 1: COMPLETE FIELD WHITELIST (41 FIELDS)
# ════════════════════════════════════════════════════════════════════════════════

ALLOWED_FIELDS = {
    # Demographics
    "age", "gender", "category", "occupation", "religion", "marital_status",
    "num_daughters", "residence_type",
    # Location
    "state", "residence", "is_rural", "is_urban", "state_residency",
    # Income
    "annual_income", "income", "family_income", "is_bpl", "has_income_cert",
    # Education
    "education_level", "is_student", "is_school_dropout", "is_first_gen_student",
    # Employment
    "is_farmer", "is_industrial_worker", "is_construction_worker",
    "is_self_employed", "is_pensioner", "loan_default_history",
    # Identification
    "has_aadhaar", "has_bank_account", "has_ration_card", "has_pucca_house", "is_citizen",
    # Vulnerable
    "is_disabled", "disability_percentage", "is_widow", "is_orphan",
    "is_landless", "is_tribal", "is_minority",
    # Other
    "land_ownership_size", "has_vending_certificate",
}

VALID_OPERATORS = {
    'gte', 'lte', 'gt', 'lt', 'eq', 'neq',
    'one_of', 'not_one_of', 'exists', 'not_exists'
}


# ════════════════════════════════════════════════════════════════════════════════
# PART 2: RULE COMPILER — Validation & Normalization (unchanged logic)
# ════════════════════════════════════════════════════════════════════════════════

class RuleCompiler:
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
    }

    OPERATOR_MAP = {
        '==': 'eq', '=': 'eq', '!=': 'neq',
        '>=': 'gte', '=>': 'gte',
        '<=': 'lte', '=<': 'lte',
        '>': 'gt', '<': 'lt',
        'in': 'one_of', 'not_in': 'not_one_of',
        'between': 'one_of', 'range': 'one_of',
    }

    NUMERIC_FIELDS = {
        'age', 'annual_income', 'income', 'family_income',
        'disability_percentage', 'land_ownership_size', 'num_daughters',
    }

    @classmethod
    def validate_condition(cls, cond):
        field    = cond.get('field', '')
        operator = cond.get('operator', '')
        value    = cond.get('value')

        if not field or not operator or value is None:
            return None

        # Normalize field
        nf = cls.FIELD_MAP.get(field.lower().strip(), field.lower().strip())
        if nf not in ALLOWED_FIELDS:
            return None

        # Normalize operator
        no = cls.OPERATOR_MAP.get(operator.lower().strip(), operator.lower().strip())
        if no not in VALID_OPERATORS:
            return None

        # Boolean cast
        if isinstance(value, str):
            lv = value.lower()
            if lv in ('true', 'yes', '1'):  value = True
            elif lv in ('false', 'no', '0'): value = False

        # Numeric cast
        if nf in cls.NUMERIC_FIELDS:
            try:
                value = float(str(value).replace(',', ''))
            except (ValueError, TypeError):
                return None

        ct = cond.get('condition_type', 'hard')
        if ct not in ('hard', 'soft'):
            ct = 'hard'

        return {
            'field':           nf,
            'operator':        no,
            'value':           value,
            'condition_type':  ct,
            'confidence':      cond.get('confidence', 1.0),
            'source_fragment': cond.get('source_fragment', ''),
        }


# ════════════════════════════════════════════════════════════════════════════════
# PART 3: ADAPTIVE RATE LIMITER — Token-bucket with back-pressure
# ════════════════════════════════════════════════════════════════════════════════

class AdaptiveRateLimiter:
    """
    Token-bucket limiter.  Automatically halves capacity on 429/503 and
    recovers gradually after a clean run.
    """

    def __init__(self, target_rpm: int):
        self._min_gap   = 60.0 / target_rpm   # seconds between tokens
        self._last_tick = 0.0
        self._lock      = asyncio.Lock()
        self._err_streak = 0

    async def acquire(self):
        async with self._lock:
            now  = asyncio.get_event_loop().time()
            wait = self._min_gap - (now - self._last_tick)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_tick = asyncio.get_event_loop().time()

    def on_success(self):
        if self._err_streak > 0:
            self._err_streak -= 1
            # Recover speed: reduce gap by 5 % (floor: original gap)
            self._min_gap = max(60.0 / TARGET_RPM, self._min_gap * 0.95)

    def on_error(self):
        self._err_streak += 1
        # Double the gap, cap at 8 s between requests
        self._min_gap = min(8.0, self._min_gap * 2.0)
        log.warning(f"Rate limiter backed off → {60/self._min_gap:.0f} RPM effective")


# ════════════════════════════════════════════════════════════════════════════════
# PART 4: BULK DB WRITER — Collects conditions and flushes in one transaction
# ════════════════════════════════════════════════════════════════════════════════

class BulkWriter:
    def __init__(self):
        self._buffer: list  = []
        self._lock           = Lock()
        self._last_flush     = time.time()
        self.written         = 0
        self.errors          = 0

    def enqueue(self, scheme_id: int, raw_conditions: list):
        clean = [RuleCompiler.validate_condition(c) for c in raw_conditions]
        clean = [c for c in clean if c]
        with self._lock:
            self._buffer.append((scheme_id, clean))
            should_flush = (
                len(self._buffer) >= BATCH_SIZE
                or (time.time() - self._last_flush) >= DB_FLUSH_INTERVAL
            )
        if should_flush:
            self.flush()

    def flush(self):
        with self._lock:
            if not self._buffer:
                return
            batch, self._buffer = self._buffer, []
            self._last_flush = time.time()

        with app.app_context():
            try:
                for scheme_id, conditions in batch:
                    Condition.query.filter_by(scheme_id=scheme_id).delete()
                    for c in conditions:
                        db.session.add(Condition(
                            scheme_id        = scheme_id,
                            field            = c['field'],
                            operator         = c['operator'],
                            value            = json.dumps(c['value']),
                            condition_type   = c['condition_type'],
                            confidence       = c['confidence'],
                            source_fragment  = c['source_fragment'],
                            source           = 'production_v3_turbo',
                        ))
                db.session.commit()
                self.written += sum(len(c) for _, c in batch)
                log.info(f"[DB] Flushed {len(batch)} schemes → {self.written} total conditions written")
            except Exception as e:
                db.session.rollback()
                self.errors += 1
                log.error(f"[DB] Flush error: {e}")


# ════════════════════════════════════════════════════════════════════════════════
# PART 5: ASYNC WORKER — Concurrent extraction with retry
# ════════════════════════════════════════════════════════════════════════════════

def get_full_text(scheme: dict) -> str:
    parts = [
        scheme.get('name')        or '',
        scheme.get('eligibility') or '',
        scheme.get('description') or '',
        scheme.get('exclusions')  or '',
    ]
    text = ' '.join(parts).strip()
    if len(text) > 8000:
        text = text[:8000].rsplit('.', 1)[0]
    return text


async def extract_one(
    semaphore: asyncio.Semaphore,
    limiter:   AdaptiveRateLimiter,
    writer:    BulkWriter,
    gemini:    GeminiExtractor,
    scheme:    dict,
    stats:     dict,
):
    scheme_id = scheme.get('id')
    text      = get_full_text(scheme)

    if not text or len(text.strip()) < 10:
        stats['skipped'] += 1
        return

    async with semaphore:
        for attempt in range(MAX_RETRIES):
            await limiter.acquire()
            try:
                # GeminiExtractor.extract is synchronous — offload to thread pool
                loop = asyncio.get_event_loop()
                conditions, version, error, low_conf = await loop.run_in_executor(
                    THREAD_POOL, gemini.extract, text, scheme
                )

                if error:
                    # 429 / quota → backoff and retry
                    if '429' in str(error) or '503' in str(error):
                        limiter.on_error()
                        wait = BACKOFF_BASE ** (attempt + 1)
                        log.warning(f"Scheme {scheme_id} attempt {attempt+1} – backing off {wait:.1f}s")
                        await asyncio.sleep(wait)
                        continue
                    stats['failed'] += 1
                    log.warning(f"Scheme {scheme_id}: {error}")
                    return

                limiter.on_success()

                if conditions:
                    writer.enqueue(scheme_id, conditions)
                    stats['processed'] += 1
                    if low_conf:
                        stats['low_conf'] += 1
                else:
                    stats['failed'] += 1
                return

            except Exception as e:
                limiter.on_error()
                log.error(f"Scheme {scheme_id} attempt {attempt+1} exception: {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(BACKOFF_BASE ** (attempt + 1))

        stats['failed'] += 1   # exhausted retries


# ════════════════════════════════════════════════════════════════════════════════
# PART 6: PROGRESS MONITOR — Non-blocking background task
# ════════════════════════════════════════════════════════════════════════════════

async def progress_monitor(stats: dict, total: int, writer: BulkWriter, stop_evt: asyncio.Event):
    start = time.time()
    while not stop_evt.is_set():
        await asyncio.sleep(15)
        done    = stats['processed'] + stats['failed'] + stats['skipped']
        elapsed = time.time() - start
        rate    = done / elapsed if elapsed else 0
        eta     = (total - done) / rate if rate else 0
        pct     = done / total * 100
        print(
            f"[{pct:5.1f}%] {done}/{total} | "
            f"OK={stats['processed']} FAIL={stats['failed']} "
            f"LOW_CONF={stats['low_conf']} | "
            f"DB written={writer.written} | "
            f"ETA={eta/60:.1f}min"
        )


# ════════════════════════════════════════════════════════════════════════════════
# PART 7: MAIN ASYNC RUNNER
# ════════════════════════════════════════════════════════════════════════════════

async def run_async(schemes: list, gemini: GeminiExtractor):
    semaphore = asyncio.Semaphore(CONCURRENCY)
    limiter   = AdaptiveRateLimiter(TARGET_RPM)
    writer    = BulkWriter()
    stats     = {'processed': 0, 'failed': 0, 'skipped': 0, 'low_conf': 0}
    stop_evt  = asyncio.Event()

    monitor_task = asyncio.create_task(
        progress_monitor(stats, len(schemes), writer, stop_evt)
    )

    tasks = [
        extract_one(semaphore, limiter, writer, gemini, scheme, stats)
        for scheme in schemes
    ]

    await asyncio.gather(*tasks)

    stop_evt.set()
    await monitor_task

    writer.flush()  # Final flush for any remainder
    return stats, writer


# ════════════════════════════════════════════════════════════════════════════════
# PART 8: ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════════

def run_extraction():
    API_KEY = os.environ.get('GEMINI_API_KEY', 'PASTE_YOUR_GEMINI_API_KEY_HERE')
    if not API_KEY:
        log.error("GEMINI_API_KEY not found")
        return

    print(f"API Key   : {'Found' if API_KEY else 'Missing'}")
    print(f"Concurrency: {CONCURRENCY} parallel requests")
    print(f"Target RPM : {TARGET_RPM}")
    print(f"Model      : gemini-flash-latest")

    gemini = GeminiExtractor(API_KEY, model_name="gemini-flash-latest")

    # Load schemes
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), JSON_FILE)
    if not os.path.exists(json_path):
        json_path = 'C:/yojanamitra_complete/all_schemes_export.json'

    log.info(f"Loading: {json_path}")
    with open(json_path, encoding='utf-8') as f:
        schemes = json.load(f)

    total = len(schemes)
    log.info(f"Total schemes: {total}")

    # ── Smoke-test: extract scheme[0] synchronously before going async ──────────
    print("\n── Smoke-test (scheme 0) ──────────────────────────────────────────")
    try:
        test_text = get_full_text(schemes[0])
        conds, ver, err, lc = gemini.extract(test_text, schemes[0])
        if err:
            print(f"  ❌ Smoke-test FAILED: {err}")
            print("  Fix API key / model name before running full extraction.")
            return
        print(f"  ✅ OK — got {len(conds or [])} conditions from scheme[0] (id={schemes[0].get('id')})")
        print(f"  Sample: {(conds or [{}])[0]}")
    except Exception as e:
        print(f"  ❌ Smoke-test exception: {e}")
        return
    print("───────────────────────────────────────────────────────────────────\n")

    start = datetime.now()

    stats, writer = asyncio.run(run_async(schemes, gemini))

    elapsed = (datetime.now() - start).total_seconds()

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"Schemes processed : {stats['processed']}/{total}")
    print(f"Schemes failed    : {stats['failed']}")
    print(f"Schemes skipped   : {stats['skipped']}")
    print(f"Low-confidence    : {stats['low_conf']}")
    print(f"DB conditions     : {writer.written}")
    print(f"DB write errors   : {writer.errors}")
    avg = writer.written / stats['processed'] if stats['processed'] else 0
    print(f"Avg cond/scheme   : {avg:.1f}")
    print(f"Total time        : {elapsed/60:.1f} min")
    print(f"Effective RPM     : {stats['processed'] / (elapsed/60):.0f}")
    print("=" * 60)

    # ── Post-extraction audit ──────────────────────────────────────────────────
    print("\n=== POST-EXTRACTION AUDIT ===")
    with app.app_context():
        all_conds   = Condition.query.all()
        field_counts = {}
        for c in all_conds:
            field_counts[c.field] = field_counts.get(c.field, 0) + 1

        print(f"Unique fields: {len(field_counts)}")
        print("\nTop 20 fields:")
        for f, cnt in sorted(field_counts.items(), key=lambda x: -x[1])[:20]:
            print(f"  {f}: {cnt}")


if __name__ == '__main__':
    run_extraction()

