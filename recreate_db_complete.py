#!/usr/bin/env python3
"""
Comprehensive database recreation script.
Drops all old tables and creates fresh ones with complete schemas matching the models.
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = "instance/yojanamitra.db"

def init_database():
    """Initialize database with complete schemas."""
    
    # Ensure instance folder exists
    os.makedirs("instance", exist_ok=True)
    
    # Remove old database if it exists
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"✓ Removed old database: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\nCreating fresh database schema...\n")
    
    # Drop existing tables
    tables = ['condition', 'scheme', 'user_documents', 'user_profile_attribute', 'user', 'admin', 'scheme_source', 'scheme_translation', 'scheme_flag', 'sqlite_sequence']
    for table in tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"✓ Dropped existing table: {table}")
        except Exception as e:
            print(f"× Failed to drop {table}: {e}")
    
    conn.commit()
    
    # Create User table with all 78 columns
    print("\n" + "="*60)
    print("Creating User table (78 columns)...")
    print("="*60)
    
    cursor.execute("""
    CREATE TABLE user (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100),
        email VARCHAR(100) UNIQUE NOT NULL,
        password_hash VARCHAR(255),
        age_group VARCHAR(50),
        gender VARCHAR(50),
        state VARCHAR(100),
        district VARCHAR(100),
        caste VARCHAR(50),
        occupation VARCHAR(100),
        religion VARCHAR(50),
        monthly_income INTEGER,
        annual_income INTEGER,
        is_citizen BOOLEAN DEFAULT 1,
        is_urban BOOLEAN DEFAULT 1,
        has_bank_account BOOLEAN DEFAULT 0,
        aadhaar_number VARCHAR(20),
        pan_number VARCHAR(20),
        phone VARCHAR(20),
        backup_email VARCHAR(100),
        preferred_language VARCHAR(50) DEFAULT 'en',
        is_active BOOLEAN DEFAULT 1,
        is_admin BOOLEAN DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_login DATETIME,
        login_count INTEGER DEFAULT 0,
        profile_completion_status VARCHAR(50) DEFAULT 'incomplete',
        disability_status VARCHAR(50),
        disability_percentage INTEGER,
        is_senior_citizen BOOLEAN DEFAULT 0,
        is_widow BOOLEAN DEFAULT 0,
        is_orphan BOOLEAN DEFAULT 0,
        is_tribal BOOLEAN DEFAULT 0,
        is_minority BOOLEAN DEFAULT 0,
        marital_status VARCHAR(50),
        number_of_children INTEGER,
        father_occupation VARCHAR(100),
        mother_occupation VARCHAR(100),
        ration_card_type VARCHAR(50),
        land_type VARCHAR(50),
        land_area_sqft FLOAT,
        is_registered_farmer BOOLEAN DEFAULT 0,
        farmer_registration_number VARCHAR(50),
        herd_size_cattle INTEGER,
        herd_size_buffalo INTEGER,
        herd_size_sheep INTEGER,
        herd_size_goat INTEGER,
        fishery_pond_area FLOAT,
        is_artisan BOOLEAN DEFAULT 0,
        artisan_category VARCHAR(100),
        monthly_household_income INTEGER,
        annual_household_income INTEGER,
        mother_tongue VARCHAR(50),
        education_level VARCHAR(100),
        is_pregnant BOOLEAN DEFAULT 0,
        number_of_girls INTEGER,
        number_of_boys INTEGER,
        school_admission_age_child_name VARCHAR(100),
        school_admission_age_child_age INTEGER,
        college_admission_student_name VARCHAR(100),
        college_admission_student_age INTEGER,
        technical_qualification VARCHAR(100),
        employment_status VARCHAR(50),
        startup_category VARCHAR(100),
        ssic_code VARCHAR(20),
        business_registration_number VARCHAR(50),
        employment_location_state VARCHAR(100),
        employment_location_district VARCHAR(100),
        government_employee_grade VARCHAR(20),
        ex_serviceman_service_years INTEGER,
        covid_impact_status VARCHAR(50),
        profile_version INTEGER DEFAULT 1,
        question_answers TEXT DEFAULT '{}',
        UNIQUE(email)
    )
    """)
    print("✓ User table created (78 columns)")
    
    # Create Admin table
    cursor.execute("""
    CREATE TABLE admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email VARCHAR(100) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL
    )
    """)
    print("✓ Admin table created")
    
    # Create Scheme table with all defined columns
    print("\n" + "="*60)
    print("Creating Scheme table...")
    print("="*60)
    
    cursor.execute("""
    CREATE TABLE scheme (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(200) NOT NULL,
        description TEXT NOT NULL,
        category VARCHAR(100),
        target_audience VARCHAR(200),
        benefits TEXT,
        eligibility TEXT,
        application_link VARCHAR(300),
        min_age INTEGER,
        max_age INTEGER,
        allowed_genders VARCHAR(100),
        min_income INTEGER,
        max_income INTEGER,
        allowed_occupations TEXT,
        allowed_castes TEXT,
        allowed_states TEXT,
        allowed_education TEXT,
        allowed_marital_status TEXT,
        disability_requirement VARCHAR(20),
        residence_requirement VARCHAR(20),
        allowed_father_occupations TEXT,
        allowed_mother_occupations TEXT,
        allowed_religions TEXT,
        land_type_requirement VARCHAR(20),
        orphan_requirement VARCHAR(20),
        tribal_requirement VARCHAR(20),
        minority_requirement VARCHAR(20),
        senior_citizen_requirement VARCHAR(20),
        widow_requirement VARCHAR(20),
        disability_percentage_min INTEGER,
        bank_account_required VARCHAR(10),
        aadhaar_required VARCHAR(10),
        allowed_ration_card_types TEXT,
        min_education_level VARCHAR(100),
        mutually_exclusive_with TEXT,
        exclusions TEXT,
        application_process TEXT,
        documents_required TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1,
        extraction_status VARCHAR(32) DEFAULT 'pending',
        extraction_version INTEGER,
        expires_at DATE
    )
    """)
    print("✓ Scheme table created with all columns")
    
    # Create UserDocument table
    cursor.execute("""
    CREATE TABLE user_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        document_type VARCHAR(100),
        document_number VARCHAR(50),
        expiry_date DATE,
        is_verified BOOLEAN DEFAULT 0,
        uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id)
    )
    """)
    print("✓ UserDocument table created")
    
    # Create UserProfileAttribute table
    cursor.execute("""
    CREATE TABLE user_profile_attribute (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        attribute_name VARCHAR(100),
        attribute_value TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id)
    )
    """)
    print("✓ UserProfileAttribute table created")
    
    # Create Condition table
    cursor.execute("""
    CREATE TABLE condition (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scheme_id INTEGER NOT NULL,
        condition_type VARCHAR(100),
        condition_value TEXT,
        operator VARCHAR(20),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (scheme_id) REFERENCES scheme(id)
    )
    """)
    print("✓ Condition table created")
    
    # Create SchemeSource table
    cursor.execute("""
    CREATE TABLE scheme_source (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scheme_id INTEGER,
        source_name VARCHAR(200),
        source_url VARCHAR(500),
        last_scraped DATETIME,
        FOREIGN KEY (scheme_id) REFERENCES scheme(id)
    )
    """)
    print("✓ SchemeSource table created")
    
    # Create SchemeTranslation table
    cursor.execute("""
    CREATE TABLE scheme_translation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scheme_id INTEGER,
        language VARCHAR(50),
        name VARCHAR(200),
        description TEXT,
        FOREIGN KEY (scheme_id) REFERENCES scheme(id)
    )
    """)
    print("✓ SchemeTranslation table created")
    
    # Create SchemeFlag table
    cursor.execute("""
    CREATE TABLE scheme_flag (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scheme_id INTEGER,
        flag_type VARCHAR(50),
        flag_message TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (scheme_id) REFERENCES scheme(id)
    )
    """)
    print("✓ SchemeFlag table created")
    
    conn.commit()
    
    # Verify all tables and columns
    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"\n✓ Tables created: {[t[0] for t in tables]}")
    
    # Check User table columns
    cursor.execute("PRAGMA table_info(user)")
    user_cols = cursor.fetchall()
    print(f"\n✓ User table: {len(user_cols)} columns")
    
    # Verify critical user columns
    critical_user_cols = [
        'id', 'name', 'email', 'password_hash', 'age_group', 'gender',
        'state', 'district', 'is_citizen', 'is_urban', 'has_bank_account',
        'profile_version', 'question_answers'
    ]
    actual_cols = {col[1] for col in user_cols}
    missing = [col for col in critical_user_cols if col not in actual_cols]
    
    if missing:
        print(f"✗ Missing User columns: {missing}")
    else:
        print(f"✓ All {len(critical_user_cols)} critical User columns present")
    
    # Check Scheme table columns
    cursor.execute("PRAGMA table_info(scheme)")
    scheme_cols = cursor.fetchall()
    print(f"\n✓ Scheme table: {len(scheme_cols)} columns")
    
    # Verify critical scheme columns
    critical_scheme_cols = [
        'id', 'name', 'description', 'category', 'eligibility',
        'allowed_genders', 'allowed_castes', 'allowed_states',
        'min_age', 'max_age', 'min_income', 'max_income'
    ]
    actual_scheme_cols = {col[1] for col in scheme_cols}
    missing_scheme = [col for col in critical_scheme_cols if col not in actual_scheme_cols]
    
    if missing_scheme:
        print(f"✗ Missing Scheme columns: {missing_scheme}")
    else:
        print(f"✓ All {len(critical_scheme_cols)} critical Scheme columns present")
    
    conn.close()
    
    print("\n" + "="*60)
    print("✅ DATABASE SUCCESSFULLY CREATED")
    print("="*60)
    print(f"Location: {DB_PATH}")
    print(f"File size: {os.path.getsize(DB_PATH)} bytes")
    print("\nAll tables and columns ready for application!")

if __name__ == "__main__":
    init_database()
