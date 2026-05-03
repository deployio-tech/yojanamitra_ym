# question_cache_db.py
#
# Single module for everything related to the question cache:
#   - Schema creation
#   - Fingerprint generation (stable, deterministic, collision-resistant)
#   - Stable YM-Q-ID generation (replaces md5-on-the-fly)
#   - Cache read (with hit tracking)
#   - Cache write
#   - Stats + admin queries
#
# Drop this file into your project root alongside yojanamitra.db.
# Import: from question_cache_db import cache_get, cache_put, init_db

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path("yojanamitra.db")

# ══════════════════════════════════════════════════════════════════════════════
# SCHEMA
# One new table. Zero changes to existing tables.
# ══════════════════════════════════════════════════════════════════════════════

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS question_cache (
    id                  INTEGER  PRIMARY KEY AUTOINCREMENT,

    -- Cache key — the ONLY lookup column
    fingerprint_hash    TEXT     UNIQUE NOT NULL,

    -- Human-readable key, for debugging and logs
    fingerprint_text    TEXT     NOT NULL,

    -- Components used to build the fingerprint
    scheme_id           TEXT     NOT NULL,
    unknown_fields      TEXT     NOT NULL,   -- JSON array, sorted alphabetically

    -- The output — exactly what the frontend consumes
    items_json          TEXT     NOT NULL,   -- JSON array of {title,text,type,icon,question,ym_q_id}
    ym_q_ids            TEXT     NOT NULL,   -- JSON array — redundant index for quick lookup

    -- Operational metadata
    hit_count           INTEGER  DEFAULT 0,
    created_at          TEXT     DEFAULT (datetime('now')),
    last_hit_at         TEXT,
    generation_source   TEXT     DEFAULT 'batch',   -- 'batch' | 'runtime'
    gemini_model        TEXT     DEFAULT 'gemini-flash-latest'
);

CREATE INDEX IF NOT EXISTS idx_qc_fingerprint_hash ON question_cache (fingerprint_hash);
CREATE INDEX IF NOT EXISTS idx_qc_scheme_id        ON question_cache (scheme_id);
CREATE INDEX IF NOT EXISTS idx_qc_hit_count        ON question_cache (hit_count DESC);
"""


def init_db(db_path: Path = DB_PATH) -> None:
    """
    Create question_cache table if it doesn't exist.
    Safe to call on every app startup — idempotent.
    """
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    logger.info(f"question_cache initialized in {db_path}")


# ══════════════════════════════════════════════════════════════════════════════
# FINGERPRINT
#
# The cache key is fully determined by (scheme_id, sorted(unknown_fields)).
# Two users with the same unknowns for the same scheme get identical questions.
# That's the entire premise of this system.
# ══════════════════════════════════════════════════════════════════════════════

def make_fingerprint(scheme_id: str, unknown_fields: list[str]) -> tuple[str, str]:
    """
    Returns (fingerprint_text, fingerprint_hash).

    fingerprint_text  →  "42_age_caste_category_income"
                         Human-readable. Stable. Used for debugging and logs.

    fingerprint_hash  →  SHA-256[:16] of fingerprint_text
                         The actual DB lookup key.

    Properties guaranteed:
    - Deterministic : same inputs → same output, always
    - Order-agnostic: ['age','income'] and ['income','age'] → same key
    - Scheme-scoped : scheme 42 and scheme 43 never collide even if fields match
    """
    sorted_fields    = sorted(f.strip().lower() for f in unknown_fields)
    fingerprint_text = f"{scheme_id}_{'_'.join(sorted_fields)}"
    fingerprint_hash = hashlib.sha256(
        fingerprint_text.encode("utf-8")
    ).hexdigest()[:16]
    return fingerprint_text, fingerprint_hash


def make_ym_q_id(fingerprint_hash: str, field_name: str) -> str:
    """
    Stable, permanent YM-Q-ID for a specific field within a fingerprint.

    REPLACES the old md5-on-the-fly approach that generated a new ID
    on every Gemini call and never stored it.

    Now every (fingerprint, field) pair has a single permanent ID,
    stored in question_cache.ym_q_ids and reused forever.

    Format: YM-Q-{8 uppercase hex chars}
    Example: YM-Q-3F8A12BC
    """
    raw = f"{fingerprint_hash}::{field_name.strip().lower()}"
    return "YM-Q-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8].upper()


# ══════════════════════════════════════════════════════════════════════════════
# CACHE READ
# ══════════════════════════════════════════════════════════════════════════════

def cache_get(
    scheme_id: str,
    unknown_fields: list[str],
    db_path: Path = DB_PATH,
) -> Optional[list[dict]]:
    """
    Look up cached questions for this (scheme_id, unknown_fields) combination.

    Returns:
        list[dict]  — the items array, ready to return to frontend verbatim
        None        — cache miss; caller must call Gemini and then cache_put()

    Side effect: increments hit_count and updates last_hit_at on HIT.
    The update is best-effort — a failure there never fails the read.
    """
    if not unknown_fields:
        return []

    _, fingerprint_hash = make_fingerprint(scheme_id, unknown_fields)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT items_json FROM question_cache WHERE fingerprint_hash = ?",
            (fingerprint_hash,),
        ).fetchone()

        if row is None:
            return None

        # Hit tracking — best-effort, never block the response
        try:
            conn.execute(
                """UPDATE question_cache
                   SET hit_count  = hit_count + 1,
                       last_hit_at = datetime('now')
                   WHERE fingerprint_hash = ?""",
                (fingerprint_hash,),
            )
            conn.commit()
        except Exception as e:
            logger.warning(f"Hit-count update failed for {fingerprint_hash}: {e}")

        return json.loads(row["items_json"])

    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# CACHE WRITE
# ══════════════════════════════════════════════════════════════════════════════

def cache_put(
    scheme_id: str,
    unknown_fields: list[str],
    items: list[dict],
    generation_source: str = "runtime",
    gemini_model: str = "gemini-flash-latest",
    db_path: Path = DB_PATH,
) -> str:
    """
    Store Gemini's output in the cache.

    Injects stable YM-Q-IDs into the items before storing.
    Uses INSERT OR REPLACE so re-running the batch script is always safe.

    Returns: fingerprint_hash (for logging)
    """
    fingerprint_text, fingerprint_hash = make_fingerprint(scheme_id, unknown_fields)

    # Inject stable YM-Q-IDs — replaces the old transient md5 generation
    items_with_ids: list[dict] = []
    for item in items:
        item_copy = dict(item)
        field_name = item_copy.get("title", "unknown")
        item_copy["ym_q_id"] = make_ym_q_id(fingerprint_hash, field_name)
        items_with_ids.append(item_copy)

    ym_q_ids = [i["ym_q_id"] for i in items_with_ids]

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """INSERT OR REPLACE INTO question_cache
               (fingerprint_hash, fingerprint_text, scheme_id, unknown_fields,
                items_json, ym_q_ids, generation_source, gemini_model)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                fingerprint_hash,
                fingerprint_text,
                str(scheme_id),
                json.dumps(sorted(f.strip().lower() for f in unknown_fields)),
                json.dumps(items_with_ids),
                json.dumps(ym_q_ids),
                generation_source,
                gemini_model,
            ),
        )
        conn.commit()
        logger.debug(
            f"Cached {fingerprint_hash} | scheme={scheme_id} "
            f"fields={sorted(unknown_fields)} | source={generation_source}"
        )
        return fingerprint_hash
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# CACHE INVALIDATION
# ══════════════════════════════════════════════════════════════════════════════

def cache_invalidate_scheme(scheme_id: str, db_path: Path = DB_PATH) -> int:
    """
    Delete all cache entries for a scheme.
    Call this when a scheme's conditions are updated.
    Returns number of rows deleted.
    """
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.execute(
            "DELETE FROM question_cache WHERE scheme_id = ?",
            (str(scheme_id),),
        )
        conn.commit()
        deleted = cursor.rowcount
        logger.info(f"Invalidated {deleted} cache entries for scheme {scheme_id}")
        return deleted
    finally:
        conn.close()


def cache_invalidate_fingerprint(
    scheme_id: str,
    unknown_fields: list[str],
    db_path: Path = DB_PATH,
) -> bool:
    """Delete a single fingerprint. Returns True if it existed."""
    _, fingerprint_hash = make_fingerprint(scheme_id, unknown_fields)
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.execute(
            "DELETE FROM question_cache WHERE fingerprint_hash = ?",
            (fingerprint_hash,),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# STATS
# ══════════════════════════════════════════════════════════════════════════════

def cache_stats(db_path: Path = DB_PATH) -> dict:
    """
    Return a health summary of the cache.
    Useful for a /admin/cache-stats endpoint or periodic logging.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM question_cache"
        ).fetchone()["n"]

        total_hits = conn.execute(
            "SELECT COALESCE(SUM(hit_count), 0) AS n FROM question_cache"
        ).fetchone()["n"]

        never_hit = conn.execute(
            "SELECT COUNT(*) AS n FROM question_cache WHERE hit_count = 0"
        ).fetchone()["n"]

        by_source = {
            row["generation_source"]: row["n"]
            for row in conn.execute(
                "SELECT generation_source, COUNT(*) AS n "
                "FROM question_cache GROUP BY generation_source"
            ).fetchall()
        }

        top_schemes = [
            {"scheme_id": r["scheme_id"], "total_hits": r["hits"]}
            for r in conn.execute(
                "SELECT scheme_id, SUM(hit_count) AS hits "
                "FROM question_cache GROUP BY scheme_id "
                "ORDER BY hits DESC LIMIT 10"
            ).fetchall()
        ]

        most_missed = [
            {
                "fingerprint_text": r["fingerprint_text"],
                "scheme_id": r["scheme_id"],
            }
            for r in conn.execute(
                "SELECT fingerprint_text, scheme_id "
                "FROM question_cache "
                "WHERE generation_source = 'runtime' "
                "ORDER BY created_at DESC LIMIT 20"
            ).fetchall()
        ]

        return {
            "total_entries":       total,
            "total_hits":          total_hits,
            "never_hit_entries":   never_hit,
            "by_generation_source": by_source,
            "top_10_schemes":      top_schemes,
            "recent_runtime_misses": most_missed,
        }
    finally:
        conn.close()


if __name__ == "__main__":
    import pprint
    init_db()
    print("Cache stats:")
    pprint.pprint(cache_stats())
