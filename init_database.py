#!/usr/bin/env python3
"""
Initialize database - creates all tables from models
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Initializing database...")

from app import app, db

with app.app_context():
    # Drop all tables first (clean slate)
    print("Dropping existing tables...")
    db.drop_all()
    
    # Create all tables based on models
    print("Creating all tables from models...")
    db.create_all()
    
    # Verify
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    print(f"\n✓ Database initialized with {len(tables)} tables:")
    for table in sorted(tables):
        cols = inspector.get_columns(table)
        print(f"  • {table}: {len(cols)} columns")
    
    # Create default admin
    from app import Admin
    from werkzeug.security import generate_password_hash
    
    existing_admin = Admin.query.first()
    if not existing_admin:
        admin = Admin(
            email='admin@yojanamitra.gov.in',
            password_hash=generate_password_hash('admin123')
        )
        db.session.add(admin)
        db.session.commit()
        print(f"\n✓ Default admin created: admin@yojanamitra.gov.in")
    else:
        print(f"\n✓ Admin already exists")
    
    print("\n✓ Database initialization complete!")
