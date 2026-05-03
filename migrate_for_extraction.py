"""
Migrations for the Gemini extraction pipeline.
Run this once to set up the database tables needed for the new extraction system.

Usage:
    python -c "from migrate_for_extraction import run_migrations; run_migrations()"
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'yojanamitra.db')


def run_migrations():
    """Run all migrations for the extraction pipeline."""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    migrations = []
    
    # Migration 1: Add verification columns to scheme table
    migrations.append("""
        ALTER TABLE scheme ADD COLUMN is_verified INTEGER DEFAULT 0;
    """)
    
    migrations.append("""
        ALTER TABLE scheme ADD COLUMN verified_by TEXT;
    """)
    
    migrations.append("""
        ALTER TABLE scheme ADD COLUMN verified_at TEXT;
    """)
    
    migrations.append("""
        ALTER TABLE scheme ADD COLUMN verification_notes TEXT;
    """)
    
    migrations.append("""
        ALTER TABLE scheme ADD COLUMN extraction_confidence TEXT DEFAULT 'unprocessed';
    """)
    
    migrations.append("""
        ALTER TABLE scheme ADD COLUMN raw_conditions_backup TEXT;
    """)
    
    migrations.append("""
        ALTER TABLE scheme ADD COLUMN condition_source TEXT DEFAULT 'ai_unverified';
    """)
    
    # Migration 2: Create gemini_prefill staging table
    migrations.append("""
        CREATE TABLE IF NOT EXISTS gemini_prefill (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheme_id INTEGER NOT NULL UNIQUE,
            extracted_json TEXT NOT NULL,
            raw_response TEXT,
            confidence TEXT,
            extraction_notes TEXT,
            conditions_found_in TEXT,
            status TEXT DEFAULT 'pending',
            retry_count INTEGER DEFAULT 0,
            error_type TEXT,
            error_message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (scheme_id) REFERENCES scheme(id)
        );
    """)
    
    # Migration 3: Create hard_guard_fields table
    migrations.append("""
        CREATE TABLE IF NOT EXISTS hard_guard_fields (
            field_name TEXT PRIMARY KEY,
            form_label TEXT,
            input_type TEXT,
            is_active INTEGER DEFAULT 1
        );
    """)
    
    # Migration 4: Create eligibility_test_cases table
    migrations.append("""
        CREATE TABLE IF NOT EXISTS eligibility_test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheme_id INTEGER NOT NULL,
            user_profile_json TEXT NOT NULL,
            expected_result TEXT NOT NULL,
            test_description TEXT,
            created_by TEXT,
            last_run_result TEXT,
            last_run_passed INTEGER,
            last_run_at TEXT,
            FOREIGN KEY (scheme_id) REFERENCES scheme(id)
        );
    """)
    
    # Migration 5: Create condition_change_log table
    migrations.append("""
        CREATE TABLE IF NOT EXISTS condition_change_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheme_id INTEGER NOT NULL,
            changed_by TEXT,
            changed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            before_json TEXT,
            after_json TEXT,
            change_reason TEXT,
            FOREIGN KEY (scheme_id) REFERENCES scheme(id)
        );
    """)
    
    # Migration 6: Seed hard_guard_fields with known profile fields
    migrations.append("""
        INSERT OR IGNORE INTO hard_guard_fields (field_name, form_label, input_type, is_active)
        VALUES 
            ('age', 'Age', 'age', 1),
            ('gender', 'Gender', 'gender', 1),
            ('caste', 'Caste/Category', 'caste', 1),
            ('income', 'Annual Income', 'income', 1),
            ('state', 'State', 'state', 1),
            ('occupation', 'Occupation', 'occupation', 1),
            ('is_student', 'Student Status', 'boolean', 1),
            ('is_farmer', 'Farmer Status', 'boolean', 1),
            ('is_bpl', 'BPL Card Holder', 'boolean', 1),
            ('is_disabled', 'Disability Status', 'boolean', 1),
            ('is_widow', 'Widow Status', 'boolean', 1),
            ('is_minority', 'Minority Status', 'boolean', 1),
            ('education', 'Education Level', 'education', 1),
            ('marital_status', 'Marital Status', 'marital', 1),
            ('has_bank_account', 'Bank Account', 'boolean', 1),
            ('has_aadhaar', 'Aadhaar Card', 'boolean', 1),
            ('is_urban', 'Urban Residence', 'boolean', 1),
            ('is_rural', 'Rural Residence', 'boolean', 1),
            ('employment_status', 'Employment Status', 'employment', 1),
            ('domicile_status', 'Domicile Status', 'boolean', 1);
    """)
    
    executed = 0
    failed = 0
    
    for i, migration in enumerate(migrations):
        try:
            cursor.execute(migration)
            executed += 1
            print(f"✓ Migration {i+1} executed")
        except sqlite3.OperationalError as e:
            if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
                print(f"⚠ Migration {i+1} skipped (already exists)")
            else:
                print(f"✗ Migration {i+1} failed: {e}")
                failed += 1
        except Exception as e:
            print(f"✗ Migration {i+1} error: {e}")
            failed += 1
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*50}")
    print(f"Migrations complete: {executed} executed, {failed} failed")
    print(f"{'='*50}")


if __name__ == "__main__":
    run_migrations()
