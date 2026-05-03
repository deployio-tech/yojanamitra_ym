#!/usr/bin/env python
"""Recreate the database from scratch with all tables"""
import sys
import os
import importlib.util

# Delete old database if exists
if os.path.exists('yojanamitra.db'):
    os.remove('yojanamitra.db')
    print("✓ Deleted old database")

# Import app.py directly (not through the package)
_app_py = os.path.join(os.path.dirname(__file__), 'app.py')
if os.path.dirname(__file__) not in sys.path:
    sys.path.insert(0, os.path.dirname(__file__))

_spec = importlib.util.spec_from_file_location("flask_app", _app_py)
_flask_app_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_flask_app_mod)

app = _flask_app_mod.app
db = _flask_app_mod.db

print("Creating database tables...")
with app.app_context():
    db.create_all()
    print("✓ Tables created")
    print("✓ Tables created")
    
    # Verify tables
    import sqlite3
    conn = sqlite3.connect('yojanamitra.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = sorted([row[0] for row in cursor.fetchall()])
    print(f"\n✓ Tables created: {', '.join(tables)}")
    
    # Check user table columns
    cursor.execute("PRAGMA table_info(user)")
    user_cols = sorted([row[1] for row in cursor.fetchall()])
    print(f"✓ User table columns: {len(user_cols)}")
    
    # Verify new columns
    required = ['profile_version', 'question_answers', 'is_citizen', 'is_urban', 'has_bank_account']
    for col in required:
        status = "✓" if col in user_cols else "✗"
        print(f"  {status} {col}")
    
    conn.close()

print("\n✓ Database ready!")
