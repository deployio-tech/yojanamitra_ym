"""
Migration: Add new profile fields to User table
Generated for: new_profile_fields.json (22 new top-level fields)

Run with:
    python migration_add_new_profile_fields.py

Safe to run multiple times — each ALTER is wrapped in a try/except.
For PostgreSQL (Supabase/Render) and SQLite.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

from app import app, db
from sqlalchemy import text

# ── Columns to add ────────────────────────────────────────────────────────────
# (column_name, sql_type)
NEW_COLUMNS = [
    # Financial
    ("annual_family_income_v2",   "INTEGER"),          # replaces split income fields; new canonical column
    ("is_bpl_v2",                 "VARCHAR(10)"),       # Yes/No  (replaces ration_card_type inference)

    # Personal / Demographics
    ("social_category",           "VARCHAR(80)"),       # SC / ST / OBC-NCL / OBC-CL / EWS / Minority / DNT
    ("date_of_birth_v2",          "VARCHAR(20)"),       # ISO date string; replaces dob
    ("gender_v2",                 "VARCHAR(20)"),       # Male / Female / Transgender  (replaces gender)
    ("marital_status_v2",         "VARCHAR(30)"),       # richer set; replaces marital_status

    # Disability
    ("disability_details",        "TEXT"),              # JSON list [{disability_type, disability_percentage}]

    # Employment / Occupation
    ("employment_status_v2",      "VARCHAR(50)"),       # richer set; replaces employment_status
    ("occupation_type",           "VARCHAR(80)"),       # Farmer / BOCW / Artisan / Vendor …

    # Land
    ("land_ownership_details",    "TEXT"),              # JSON list [{area_in_acres, land_type, is_irrigated}]

    # Family
    ("family_members",            "TEXT"),              # JSON list [{relation, date_of_birth, is_alive}]

    # Education
    ("education_details",         "TEXT"),              # JSON list [{education_level, stream, status, percentage_marks, year_of_passing, institute_type}]

    # Residency
    ("state_of_domicile",         "VARCHAR(80)"),       # canonical state (replaces state)
    ("residence_location_type",   "VARCHAR(20)"),       # Rural / Urban  (replaces residence)
    ("years_in_current_state",    "INTEGER"),

    # Special categories
    ("is_ex_serviceman_or_dependent", "VARCHAR(10)"),   # Yes/No
    ("is_shg_member",             "VARCHAR(10)"),       # Yes/No
    ("is_freedom_fighter_or_dependent", "VARCHAR(10)"), # Yes/No

    # Health
    ("has_critical_illness",      "VARCHAR(10)"),       # Yes/No
    ("is_pregnant",               "VARCHAR(10)"),       # Yes/No
    ("is_lactating_mother",       "VARCHAR(10)"),       # Yes/No

    # Financial
    ("has_bank_account_v2",       "VARCHAR(10)"),       # Yes/No  (replaces bank_account_available)
]
# ──────────────────────────────────────────────────────────────────────────────


def _is_postgres():
    url = os.getenv("DATABASE_URL", "sqlite:///yojanamitra.db")
    return url.startswith("postgres") or url.startswith("postgresql")


def add_columns():
    is_pg = _is_postgres()
    added = []
    skipped = []

    with app.app_context():
        with db.engine.connect() as conn:
            for col_name, col_type in NEW_COLUMNS:
                try:
                    if is_pg:
                        stmt = text(
                            f'ALTER TABLE "user" ADD COLUMN {col_name} {col_type};'
                        )
                    else:
                        stmt = text(
                            f"ALTER TABLE user ADD COLUMN {col_name} {col_type};"
                        )
                    conn.execute(stmt)
                    conn.commit()
                    added.append(col_name)
                    print(f"  ✅  Added   : {col_name} ({col_type})")
                except Exception as e:
                    conn.rollback()
                    # Column already exists — safe to skip
                    if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                        skipped.append(col_name)
                        print(f"  ⏭   Skipped : {col_name} (already exists)")
                    else:
                        print(f"  ❌  ERROR   : {col_name} — {e}", file=sys.stderr)
                        raise

    print(f"\nDone. Added {len(added)} column(s), skipped {len(skipped)} existing.")


if __name__ == "__main__":
    print("Running migration: add new profile fields…\n")
    add_columns()
    print("\nMigration complete.")
