"""
fix_states_migration.py
=======================
One-time migration: corrects the `allowed_states` column for all schemes
that were scraped with the wrong default state ('Karnataka').

The scraper set allowed_states=['Karnataka'] for every scheme regardless of
its actual geographic scope.  scheme_rule_adapter._resolve_true_state() reads
the eligibility text and correctly detects the real state — but this causes
STATE_MISMATCH for Karnataka users because the engine uses the rule's
eligible_states, not the raw DB value.

Running this script once fixes 2,855+ schemes in the DB so that:
  - National/central schemes → allowed_states=['ALL']
  - State-specific schemes   → the correct state code (e.g. ['BR'] for Bihar)
  - Genuine Karnataka schemes → stay as ['KA']

Usage (run from your project root):
    python fix_states_migration.py

Or from Flask shell:
    flask shell
    exec(open('fix_states_migration.py').read())
"""

import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
log = logging.getLogger(__name__)

def run_migration():
    try:
        from app import app, db
        from models import Scheme  # adjust import if your model is elsewhere
    except ImportError:
        # Try alternate import path
        try:
            from app import app, db
            # Scheme may be defined in app.py itself
            with app.app_context():
                from app import Scheme
        except Exception as e:
            log.error(f"Could not import app/db/Scheme: {e}")
            log.error("Run this from your project root where app.py lives.")
            sys.exit(1)

    from scheme_rule_adapter import _resolve_true_state

    with app.app_context():
        schemes = Scheme.query.all()
        total   = len(schemes)
        changed = 0
        errors  = 0

        log.info(f"Processing {total} schemes...")

        for i, scheme in enumerate(schemes):
            try:
                old_states = scheme.allowed_states or []
                resolved   = _resolve_true_state(
                    scheme.name        or "",
                    scheme.eligibility or "",
                    scheme.description or "",
                    old_states,
                )
                if resolved != old_states:
                    scheme.allowed_states = resolved
                    changed += 1
                    if changed <= 20:                       # log first 20 changes
                        log.info(
                            f"  [{scheme.id}] {scheme.name[:50]}: "
                            f"{old_states} → {resolved}"
                        )
            except Exception as e:
                log.warning(f"  Skipping scheme {scheme.id} ({scheme.name[:40]}): {e}")
                errors += 1

            if (i + 1) % 500 == 0:
                log.info(f"  {i+1}/{total} processed, {changed} changes so far...")

        db.session.commit()
        log.info(f"\n✅ Migration complete.")
        log.info(f"   Total schemes:  {total}")
        log.info(f"   States updated: {changed}")
        log.info(f"   Errors skipped: {errors}")

if __name__ == "__main__":
    run_migration()
