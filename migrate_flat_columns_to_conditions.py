"""
migrate_flat_columns_to_conditions.py
Migrates existing schemes' flat eligibility columns to structured Condition rows.
Safe to run multiple times — checks for existing conditions before creating.
Usage: python migrate_flat_columns_to_conditions.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Scheme, Condition


def flat_columns_to_conditions(scheme):
    """Convert a Scheme's flat columns to Condition objects and return a list."""
    import json

    def _j(col):
        if not col:
            return []
        try:
            return json.loads(col)
        except Exception:
            return []

    def _add(conds, field, operator, value, ctype='hard', conf=0.90, src=None):
        if value is not None and value != [] and value != '':
            v = json.dumps(value) if not isinstance(value, str) else value
            cond = Condition(
                scheme_id=scheme.id,
                field=field,
                operator=operator,
                value=v,
                condition_type=ctype,
                confidence=conf,
                source_fragment=src or f"Migrated from flat column: {field}",
            )
            conds.append(cond)

    conds = []

    if scheme.min_age is not None:
        _add(conds, 'age', 'gte', scheme.min_age, 'hard', 0.95)
    if scheme.max_age is not None:
        _add(conds, 'age', 'lte', scheme.max_age, 'hard', 0.95)

    genders = _j(scheme.allowed_genders)
    if genders:
        if len(genders) == 1:
            _add(conds, 'gender', 'eq', genders[0], 'hard', 0.90)
        else:
            _add(conds, 'gender', 'in', genders, 'hard', 0.90)

    if scheme.min_income is not None:
        _add(conds, 'annual_income', 'gte', scheme.min_income, 'hard', 0.90)
    if scheme.max_income is not None:
        _add(conds, 'annual_income', 'lte', scheme.max_income, 'hard', 0.95)

    castes = _j(scheme.allowed_castes)
    if castes:
        _add(conds, 'category', 'in', castes, 'hard', 0.90)

    states = _j(scheme.allowed_states)
    if states:
        if len(states) == 1:
            _add(conds, 'state', 'eq', states[0], 'hard', 0.95)
        else:
            _add(conds, 'state', 'in', states, 'hard', 0.95)

    ed_list = _j(scheme.allowed_education)
    if ed_list:
        _add(conds, 'education_level', 'in', ed_list, 'soft', 0.85)

    marital = _j(scheme.allowed_marital_status)
    if marital:
        _add(conds, 'marital_status', 'in', marital, 'soft', 0.85)

    occs = _j(scheme.allowed_occupations)
    if occs:
        _add(conds, 'occupation', 'in', occs, 'soft', 0.85)

    if scheme.disability_requirement and scheme.disability_requirement.lower() not in ('any', ''):
        val = scheme.disability_requirement.lower() == 'yes'
        _add(conds, 'is_disabled', 'boolean', val, 'hard', 0.85)

    if scheme.residence_requirement and scheme.residence_requirement.lower() not in ('any', ''):
        _add(conds, 'residence', 'eq', scheme.residence_requirement, 'soft', 0.80)

    fo = _j(scheme.allowed_father_occupations)
    if fo:
        _add(conds, 'father_occupation', 'in', fo, 'soft', 0.80)
    mo = _j(scheme.allowed_mother_occupations)
    if mo:
        _add(conds, 'mother_occupation', 'in', mo, 'soft', 0.80)

    rels = _j(scheme.allowed_religions)
    if rels:
        _add(conds, 'religion', 'in', rels, 'soft', 0.80)

    if scheme.land_type_requirement and scheme.land_type_requirement.lower() not in ('any', ''):
        _add(conds, 'land_type', 'eq', scheme.land_type_requirement, 'soft', 0.80)

    if scheme.orphan_requirement and scheme.orphan_requirement.lower() not in ('any', ''):
        val = scheme.orphan_requirement.lower() == 'yes'
        _add(conds, 'is_orphan', 'boolean', val, 'soft', 0.80)
    if scheme.tribal_requirement and scheme.tribal_requirement.lower() not in ('any', ''):
        val = scheme.tribal_requirement.lower() == 'yes'
        _add(conds, 'is_tribal', 'boolean', val, 'soft', 0.80)

    if scheme.minority_requirement and scheme.minority_requirement.lower() not in ('any', ''):
        val = scheme.minority_requirement.lower() == 'yes'
        _add(conds, 'is_minority', 'boolean', val, 'soft', 0.80)
    if scheme.senior_citizen_requirement and scheme.senior_citizen_requirement.lower() not in ('any', ''):
        val = scheme.senior_citizen_requirement.lower() == 'yes'
        _add(conds, 'is_senior_citizen', 'boolean', val, 'soft', 0.80)
    if scheme.widow_requirement and scheme.widow_requirement.lower() not in ('any', ''):
        val = scheme.widow_requirement.lower() == 'yes'
        _add(conds, 'is_widow', 'boolean', val, 'soft', 0.80)

    if scheme.disability_percentage_min is not None:
        _add(conds, 'disability_percentage', 'gte', scheme.disability_percentage_min, 'hard', 0.90)

    if scheme.bank_account_required and scheme.bank_account_required.lower() == 'yes':
        _add(conds, 'has_bank_account', 'boolean', True, 'acquirable', 0.95)
    if scheme.aadhaar_required and scheme.aadhaar_required.lower() == 'yes':
        _add(conds, 'has_aadhaar', 'boolean', True, 'acquirable', 0.95)

    rc_types = _j(scheme.allowed_ration_card_types)
    if rc_types:
        _add(conds, 'ration_card_type', 'in', rc_types, 'acquirable', 0.90)

    if scheme.min_education_level:
        _add(conds, 'education_level', 'gte', scheme.min_education_level, 'soft', 0.85)

    return conds


def run_migration(batch_size=100, dry_run=False):
    """Migrate all existing schemes to Condition rows."""
    with app.app_context():
        # Ensure conditions table exists
        db.create_all()

        total_schemes = Scheme.query.count()
        print(f"Total schemes: {total_schemes}")

        migrated = 0
        skipped = 0
        errors = 0

        schemes = Scheme.query.all()
        for scheme in schemes:
            # Check if already migrated
            existing = Condition.query.filter_by(scheme_id=scheme.id).first()
            if existing:
                skipped += 1
                continue

            try:
                conds = flat_columns_to_conditions(scheme)
                if not dry_run:
                    for cond in conds:
                        db.session.add(cond)
                    db.session.commit()
                migrated += 1
                print(f"  [{migrated}] {scheme.name[:50]}: {len(conds)} conditions")
            except Exception as e:
                errors += 1
                print(f"  ERROR {scheme.id} ({scheme.name[:30]}): {e}")
                db.session.rollback()

        print(f"\nMigration complete:")
        print(f"  Migrated: {migrated}")
        print(f"  Skipped (already migrated): {skipped}")
        print(f"  Errors: {errors}")
        return migrated, skipped, errors


if __name__ == '__main__':
    dry = '--dry-run' in sys.argv
    if dry:
        print("DRY RUN MODE — no changes will be written")
    run_migration(dry_run=dry)
