#!/usr/bin/env python3
"""
Database initialization using Flask-SQLAlchemy create_all()
This bypasses the module import issues by running within proper Flask app context.
"""
import sys
import os

# Set up path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Delete old database
db_path = "instance/yojanamitra.db"
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"✓ Removed old database: {db_path}")

# Ensure instance folder exists
os.makedirs("instance", exist_ok=True)

# Import app and db within Flask context
from app import app, db

print("\nInitializing database with Flask-SQLAlchemy...")
print("=" * 60)

with app.app_context():
    # Create all tables from the models
    db.create_all()
    print("✓ All tables created")
    
    # Verify tables
    inspector_query = """
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name NOT LIKE 'sqlite_%'
    ORDER BY name
    """
    
    from sqlalchemy import text, inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    print(f"\n✓ Tables created: {len(tables)}")
    for table in tables:
        cols = inspector.get_columns(table)
        print(f"  • {table}: {len(cols)} columns")
    
    # Additional verification
    user_cols = inspector.get_columns('user')
    print(f"\n✓ User table: {len(user_cols)} columns")
    
    scheme_cols = inspector.get_columns('scheme')
    print(f"✓ Scheme table: {len(scheme_cols)} columns")
    
    print("\n" + "=" * 60)
    print("✅ DATABASE SUCCESSFULLY INITIALIZED")
    print("=" * 60)
    print(f"Location: {db_path}")
    print(f"File size: {os.path.getsize(db_path)} bytes")
    print("\nReady for application startup!")

