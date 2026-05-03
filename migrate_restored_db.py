#!/usr/bin/env python3
"""
Migrate restored database to current schema
Adds missing columns that were added after the backup was created
"""
import sqlite3
import os

db_path = "instance/yojanamitra.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Migrating restored database to current schema...")
print("=" * 60)

# Check existing columns
cursor.execute("PRAGMA table_info(user)")
existing_cols = {row[1] for row in cursor.fetchall()}

# New columns to add
new_columns = [
    ("is_citizen", "VARCHAR(10)"),
    ("is_urban", "VARCHAR(10)"),
    ("has_bank_account", "VARCHAR(10)"),
    ("residence_type", "VARCHAR(50)"),
    ("verified_scheme_ids", "TEXT"),
    ("verified_schemes_data", "TEXT"),
    ("profile_version", "INTEGER"),
    ("question_answers", "TEXT"),
]

# Add missing columns
for col_name, col_type in new_columns:
    if col_name not in existing_cols:
        try:
            if col_name == "profile_version":
                cursor.execute(f"ALTER TABLE user ADD COLUMN {col_name} {col_type} DEFAULT 1")
            elif col_name == "question_answers":
                cursor.execute(f"ALTER TABLE user ADD COLUMN {col_name} {col_type} DEFAULT '{{}}'")
            else:
                cursor.execute(f"ALTER TABLE user ADD COLUMN {col_name} {col_type}")
            print(f"✓ Added column: {col_name}")
        except Exception as e:
            print(f"✗ Failed to add {col_name}: {e}")
    else:
        print(f"✓ Column already exists: {col_name}")

conn.commit()

# Verify
cursor.execute("PRAGMA table_info(user)")
final_cols = cursor.fetchall()
print(f"\n✓ User table now has {len(final_cols)} columns")

# Count records preserved
cursor.execute("SELECT COUNT(*) FROM user")
user_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM scheme")
scheme_count = cursor.fetchone()[0]

print(f"\n✓ Data preserved: {user_count} users, {scheme_count} schemes")

conn.close()

print("\n" + "=" * 60)
print("✓ Migration complete!")
