#!/usr/bin/env python
"""Verify database and test endpoints"""
from app import app
import os
import sqlite3

print("=" * 60)
print("VERIFICATION: Database in instance folder")
print("=" * 60)

# Check file
db_path = 'instance/yojanamitra.db'
if os.path.exists(db_path):
    size = os.path.getsize(db_path)
    print(f"\n✓ Database exists: {db_path}")
    print(f"  Size: {size} bytes")
else:
    print(f"\n✗ Database NOT found at {db_path}")
    exit(1)

# Check schema
print("\n" + "=" * 60)
print("SCHEMA VERIFICATION")
print("=" * 60)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f"\n✓ Tables: {tables}")

cursor.execute("PRAGMA table_info(user)")
columns = [row[1] for row in cursor.fetchall()]
print(f"✓ User table: {len(columns)} columns")

required_cols = ['profile_version', 'question_answers', 'is_citizen', 'is_urban', 'has_bank_account']
missing = []
for col in required_cols:
    if col in columns:
        print(f"  ✓ {col}")
    else:
        print(f"  ✗ {col}")
        missing.append(col)

conn.close()

if missing:
    print(f"\n✗ Missing columns: {missing}")
    exit(1)

# Test with Flask app
print("\n" + "=" * 60)
print("API ENDPOINT TEST")
print("=" * 60)

with app.test_client() as client:
    resp = client.post('/api/login', 
        json={'email': 'test@example.com', 'password': 'test123'},
        content_type='application/json'
    )
    
    print(f"\nPOST /api/login status: {resp.status_code}")
    result = resp.get_json()
    
    if resp.status_code == 401 and 'error' in result:
        print("✓ LOGIN ENDPOINT WORKING!")
        print(f"  Response: {result['error']}")
    else:
        print(f"✗ Unexpected: {result}")
        exit(1)

print("\n" + "=" * 60)
print("✅ ALL SYSTEMS GO! System is ready for testing!")
print("=" * 60)
