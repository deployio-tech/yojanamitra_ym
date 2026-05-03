"""
fix_db_fields.py — YojanaMitra Comprehensive DB Data Migration
Run with no arguments to fix ALL fields in one go:

    python fix_db_fields.py

Options:
    --dry-run       Preview only, no DB writes
    --field <n>     Fix one field only
    --generate      Regenerate db_fixes_v2.json first
"""

import sys, json, logging, argparse
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
log = logging.getLogger(__name__)

FIXES_FILE = Path(__file__).parent / 'db_fixes_v2.json'

LIST_FIELDS = {
    'allowed_states', 'allowed_genders', 'allowed_castes',
    'allowed_occupations', 'allowed_ration_card_types',
    'allowed_religions', 'allowed_marital_status',
    'allowed_father_occupations', 'allowed_mother_occupations',
}


def load_fixes(force_regenerate=False):
    if force_regenerate or not FIXES_FILE.exists():
        log.info('Generating fixes from eligibility text...')
        import generate_db_fixes
        return generate_db_fixes.main()
    with open(FIXES_FILE, encoding='utf-8') as f:
        return json.load(f)


def run_migration(dry_run=False, field_filter=None):
    fixes = load_fixes()
    if field_filter:
        fixes = [f for f in fixes if f['field'] == field_filter]
        log.info(f'Filtered to field={field_filter}: {len(fixes)} fixes')

    try:
        from app import app, db
    except ImportError as e:
        log.error(f'Cannot import app/db: {e}'); sys.exit(1)

    with app.app_context():
        try:
            from models import Scheme
        except ImportError:
            try:
                from app import Scheme
            except ImportError:
                log.error('Cannot import Scheme model.'); sys.exit(1)

        log.info(f'Applying {len(fixes)} fixes (dry_run={dry_run})...')
        applied = skipped = errors = 0
        by_field = {}

        for i, fix in enumerate(fixes):
            sid, field, new_val = fix['id'], fix['field'], fix['new']
            try:
                scheme = Scheme.query.get(sid)
                if not scheme:
                    errors += 1; continue

                current_raw = getattr(scheme, field, None)

                if field in LIST_FIELDS:
                    if isinstance(current_raw, str):
                        try:    current_parsed = json.loads(current_raw)
                        except: current_parsed = [current_raw] if current_raw else []
                    elif isinstance(current_raw, list):
                        current_parsed = current_raw
                    else:
                        current_parsed = []

                    if sorted(str(x) for x in current_parsed) == sorted(str(x) for x in new_val):
                        skipped += 1; continue

                    write_val = json.dumps(new_val)
                else:
                    if current_raw == new_val:
                        skipped += 1; continue
                    write_val = new_val

                if dry_run:
                    log.info(f'  [DRY] [{sid}] {field}: {current_raw!r} -> {write_val!r}')
                else:
                    setattr(scheme, field, write_val)

                applied += 1
                by_field[field] = by_field.get(field, 0) + 1

                if (i + 1) % 500 == 0:
                    log.info(f'  {i+1}/{len(fixes)} processed ({applied} applied)...')
                    if not dry_run:
                        try:    db.session.commit()
                        except Exception as be:
                            log.warning(f'Batch commit failed: {be}')
                            db.session.rollback()

            except Exception as e:
                log.warning(f'  Error scheme {sid} field {field}: {e}')
                try:    db.session.rollback()
                except: pass
                errors += 1; continue

        if not dry_run:
            try:    db.session.commit(); log.info('DB commit successful.')
            except Exception as e:
                log.error(f'Final commit failed: {e}'); db.session.rollback()
        else:
            log.info('Dry run complete - no changes written.')

        log.info(f'  Applied: {applied}  |  Already correct: {skipped}  |  Errors: {errors}')
        for f, c in sorted(by_field.items(), key=lambda x: -x[1]):
            log.info(f'    {f:<30} {c}')

        return applied, skipped, errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--field', type=str, default=None)
    parser.add_argument('--generate', action='store_true')
    args = parser.parse_args()

    if args.generate:
        import generate_db_fixes; generate_db_fixes.main()

    ALL_FIELDS = [
        'allowed_states',
        'min_age',
        'max_age',
        'max_income',
        'allowed_occupations',
        'allowed_genders',
    ]

    if args.field:
        run_migration(dry_run=args.dry_run, field_filter=args.field)
    else:
        grand_applied = grand_correct = grand_errors = 0
        grand_by_field = {}

        for field in ALL_FIELDS:
            log.info('=' * 55)
            log.info(f'  Migrating: {field}')
            log.info('=' * 55)
            a, c, e = run_migration(dry_run=args.dry_run, field_filter=field)
            grand_applied += a
            grand_correct += c
            grand_errors  += e
            grand_by_field[field] = a

        print()
        print('=' * 55)
        print('  ALL MIGRATIONS COMPLETE')
        print('=' * 55)
        print(f'  Fields migrated : {len(ALL_FIELDS)}')
        print(f'  Fixes applied   : {grand_applied}')
        print(f'  Already correct : {grand_correct}')
        print(f'  Errors          : {grand_errors}')
        print()
        print('  Breakdown:')
        for field, count in grand_by_field.items():
            label = f'{count} applied' if count > 0 else 'already up-to-date'
            print(f'    {field:<30}  {label}')
        print()
        if args.dry_run:
            print('  DRY RUN - no DB writes. Remove --dry-run to apply.')
        else:
            print('  Done! Restart your server for changes to take effect.')
        print('=' * 55)
