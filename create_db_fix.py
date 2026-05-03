#!/usr/bin/env python
"""Create database tables using Metadata.create_all instead"""
import sys
import os
import importlib.util

# Delete old database
if os.path.exists('yojanamitra.db'):
    os.remove('yojanamitra.db')
    print("✓ Deleted oldatabase")

# Load app
_app_py = os.path.join(os.path.dirname(__file__), 'app.py')
sys.path.insert(0, os.path.dirname(__file__))

_spec = importlib.util.spec_from_file_location("flask_app", _app_py)
_flask_app_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_flask_app_mod)

app = _flask_app_mod.app
db = _flask_app_mod.db

print("Creating database using Metadata.create_all...")
with app.app_context():
    # Use the metadata directly
    from sqlalchemy import create_engine
    engine = db.engine
    
    print(f"Engine: {engine}")
    print(f"Engine URL: {engine.url}")
    
    # Create all tables
    db.metadata.create_all(bind=engine)
    print("✓ Created database structure")
    
    # Verify
    import sqlite3
    conn = sqlite3.connect('yojanamitra.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = sorted([row[0] for row in cursor.fetchall()])
    print(f"\n✓ Tables created: {tables}")
    
    if 'user' in tables:
        cursor.execute("PRAGMA table_info(user)")
        cols = [row[1] for row in cursor.fetchall()]
        print(f"✓ User table has {len(cols)} columns!")
        
        required = ['profile_version', 'question_answers', 'is_citizen', 'is_urban']
        for col in required:
            status = "✓" if col in cols else "✗"
            print(f"  {status} {col}")
    
    conn.close()

print("\n✅ Database created successfully!")
