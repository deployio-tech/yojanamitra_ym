"""
Add missing columns to the database
"""
import sqlite3

conn = sqlite3.connect('instance/yojanamitra.db')
cursor = conn.cursor()

# Add missing columns
migrations = [
    'ALTER TABLE scheme ADD COLUMN is_verified INTEGER DEFAULT 0',
    'ALTER TABLE scheme ADD COLUMN verified_by TEXT',
    'ALTER TABLE scheme ADD COLUMN verified_at TEXT',
    'ALTER TABLE scheme ADD COLUMN verification_notes TEXT',
    'ALTER TABLE scheme ADD COLUMN extraction_confidence TEXT DEFAULT "unprocessed"',
    'ALTER TABLE scheme ADD COLUMN raw_conditions_backup TEXT',
    'ALTER TABLE scheme ADD COLUMN condition_source TEXT DEFAULT "ai_unverified"'
]

for sql in migrations:
    try:
        cursor.execute(sql)
        print(f'OK: {sql[:50]}')
    except sqlite3.OperationalError as e:
        if 'duplicate' in str(e).lower() or 'already exists' in str(e).lower():
            print(f'SKIP: Already exists')
        else:
            print(f'ERROR: {e}')

conn.commit()

# Verify
cursor.execute('SELECT COUNT(*) FROM scheme')
print(f'\nTotal schemes: {cursor.fetchone()[0]}')

# Check column count
cursor.execute('PRAGMA table_info(scheme)')
cols = cursor.fetchall()
print(f'Total columns: {len(cols)}')

conn.close()
print('\nDone!')
