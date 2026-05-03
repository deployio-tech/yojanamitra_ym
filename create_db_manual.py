#!/usr/bin/env python
"""Manually create database tables using raw SQL"""
import os
import sqlite3

# Delete old database in root directory only
db_file = 'yojanamitra.db'
if os.path.exists(db_file):
    try:
        os.remove(db_file)
        print(f"✓ Deleted {db_file}")
    except Exception as e:
        print(f"Warning: Could not delete {db_file}: {e}")

# Create the database
db_path = 'yojanamitra.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print(f"✓ Creating database at {os.path.abspath(db_path)}")

# Create user table with all columns
cursor.execute('''
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    mobile VARCHAR(15),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    age INTEGER,
    gender VARCHAR(20),
    occupation VARCHAR(100),
    income INTEGER,
    caste VARCHAR(50),
    state VARCHAR(50),
    education VARCHAR(50),
    marital_status VARCHAR(20),
    disability VARCHAR(10),
    residence VARCHAR(20),
    father_occupation VARCHAR(100),
    mother_occupation VARCHAR(100),
    religion VARCHAR(50),
    land_type VARCHAR(20),
    is_orphan VARCHAR(10),
    is_tribal VARCHAR(10),
    dob VARCHAR(20),
    aadhaar_available VARCHAR(10),
    district VARCHAR(100),
    block_taluk VARCHAR(100),
    domicile_status VARCHAR(10),
    family_type VARCHAR(20),
    total_family_members INTEGER,
    is_head_of_family VARCHAR(10),
    annual_family_income INTEGER,
    income_slab VARCHAR(50),
    income_certificate_available VARCHAR(10),
    sub_caste VARCHAR(100),
    minority_status VARCHAR(10),
    ews_status VARCHAR(10),
    ration_card_available VARCHAR(10),
    ration_card_type VARCHAR(20),
    education_status VARCHAR(50),
    highest_education_level VARCHAR(50),
    current_course VARCHAR(100),
    institution_type VARCHAR(50),
    employment_status VARCHAR(50),
    govt_employee_in_family VARCHAR(10),
    is_farmer VARCHAR(10),
    own_agricultural_land VARCHAR(10),
    land_size_acres REAL,
    is_tenant_farmer VARCHAR(10),
    disability_percentage INTEGER,
    is_widow_single_woman VARCHAR(10),
    is_senior_citizen VARCHAR(10),
    bank_account_available VARCHAR(10),
    aadhaar_linked_bank VARCHAR(10),
    mobile_linked_bank VARCHAR(10),
    income_cert_last_1_year VARCHAR(10),
    scheme_previously_availed VARCHAR(10),
    willing_to_submit_docs VARCHAR(10),
    documents_available TEXT,
    achievement_certificates TEXT,
    is_pensioner VARCHAR(10),
    num_daughters INTEGER,
    has_pucca_house VARCHAR(10),
    house_type VARCHAR(30),
    is_landless VARCHAR(10),
    is_bocw_registered VARCHAR(10),
    is_school_dropout VARCHAR(10),
    is_first_gen_student VARCHAR(10),
    child_age INTEGER,
    education_milestones TEXT,
    career_goal VARCHAR(100),
    is_citizen VARCHAR(10),
    is_urban VARCHAR(10),
    has_bank_account VARCHAR(10),
    residence_type VARCHAR(50),
    verified_scheme_ids TEXT,
    verified_schemes_data TEXT,
    profile_version INTEGER DEFAULT 1,
    question_answers TEXT DEFAULT '{}'
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS admin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS scheme (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255),
    description TEXT,
    eligibility_criteria TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

conn.commit()
conn.close()

# Verify
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = sorted([row[0] for row in cursor.fetchall()])
print(f"\n✓ Tables created: {tables}")

if 'user' in tables:
    cursor.execute("PRAGMA table_info(user)")
    cols = sorted([row[1] for row in cursor.fetchall()])
    print(f"✓ User table has {len(cols)} columns!")
    
    required = ['profile_version', 'question_answers', 'is_citizen', 'is_urban', 'has_bank_account']
    for col in required:
        status = "✓" if col in cols else "✗"
        print(f"  {status} {col}")

conn.close()

print("\n✅ Database created successfully!")
print(f"📁 Location: {os.path.abspath(db_path)}")
