"""
Data Integrity Fixes - Step 2 Cleanup
=====================================
Fixes identified issues:
1. Remove "Sri Lanka" corrupted boolean
2. Normalize booleans to lowercase
3. Remove invalid gender values
4. Remove absurd income outliers
5. Normalize gender casing
"""
import sys
sys.path.insert(0, '.')
from app import app, db

with app.app_context():
    print("=" * 60)
    print("DATA INTEGRITY FIXES - STEP 2 CLEANUP")
    print("=" * 60)
    
    # FIX 1: Remove "Sri Lanka" corrupted value
    print("\n[1] Removing 'Sri Lanka' corrupted boolean...")
    result = db.session.execute(db.text(
        "DELETE FROM conditions WHERE value = :val"
    ), {"val": '"Sri Lanka"'})
    print(f"    Deleted: {result.rowcount} rows")
    
    # FIX 2: Normalize booleans to lowercase 'true'
    print("\n[2] Normalizing boolean 'true' values...")
    result = db.session.execute(db.text(
        "UPDATE conditions SET value = 'true' WHERE LOWER(value) = 'true'"
    ))
    print(f"    Updated: {result.rowcount} rows")
    
    # FIX 2b: Normalize booleans to lowercase 'false'
    print("\n[2b] Normalizing boolean 'false' values...")
    result = db.session.execute(db.text(
        "UPDATE conditions SET value = 'false' WHERE LOWER(value) = 'false'"
    ))
    print(f"    Updated: {result.rowcount} rows")
    
    # FIX 3: Remove invalid gender values (keep only MALE, FEMALE)
    print("\n[3] Removing invalid gender values...")
    # Get invalid gender values first
    invalid_genders = db.session.execute(db.text(
        "SELECT DISTINCT value FROM conditions WHERE field = 'gender'"
    )).fetchall()
    deleted = 0
    for (val,) in invalid_genders:
        if val and not any(x in str(val).upper() for x in ['MALE', 'FEMALE', 'TRANSGENDER']):
            result = db.session.execute(db.text(
                "DELETE FROM conditions WHERE field = 'gender' AND value = :val"
            ), {"val": val})
            deleted += result.rowcount
            print(f"    Deleted: {val}")
    print(f"    Total deleted: {deleted} invalid gender values")
    
    # FIX 4: Remove absurd income outliers (cap at 10 crore = 100,000,000)
    print("\n[4] Removing absurd income outliers (cap at 10 Crore)...")
    # Get income values to check
    incomes = db.session.execute(db.text(
        "SELECT DISTINCT value FROM conditions WHERE field = 'annual_income'"
    )).fetchall()
    deleted = 0
    for (val,) in incomes:
        try:
            clean_val = val.replace('"', '').replace("'", "")
            num_val = float(clean_val)
            if num_val > 100000000:
                result = db.session.execute(db.text(
                    "DELETE FROM conditions WHERE field = 'annual_income' AND value = :val"
                ), {"val": val})
                deleted += result.rowcount
                print(f"    Deleted: {val} ({num_val:,.0f})")
        except (ValueError, TypeError):
            pass
    print(f"    Total deleted: {deleted} income outliers")
    
    # FIX 5: Normalize gender casing
    print("\n[5] Normalizing gender casing...")
    # Get all gender values
    genders = db.session.execute(db.text(
        "SELECT id, value FROM conditions WHERE field = 'gender'"
    )).fetchall()
    for cond_id, val in genders:
        if val:
            val_str = str(val).strip()
            if val_str.lower() == '"female"' or val_str.lower() == "'female'" or val_str.lower() == 'female':
                db.session.execute(db.text(
                    "UPDATE conditions SET value = '\"FEMALE\"' WHERE id = :id"
                ), {"id": cond_id})
            elif val_str.lower() == '"male"' or val_str.lower() == "'male'" or val_str.lower() == 'male':
                db.session.execute(db.text(
                    "UPDATE conditions SET value = '\"MALE\"' WHERE id = :id"
                ), {"id": cond_id})
    print("    Gender casing normalized")
    
    db.session.commit()
    
    # POST-FIX VERIFICATION
    print("\n" + "=" * 60)
    print("POST-FIX VERIFICATION")
    print("=" * 60)
    
    # Total count
    total = db.session.execute(db.text("SELECT COUNT(*) FROM conditions")).scalar()
    print(f"\nTotal conditions: {total}")
    
    # Gender values
    print("\nGender values:")
    genders = db.session.execute(db.text(
        "SELECT DISTINCT value FROM conditions WHERE field = 'gender'"
    )).fetchall()
    for (val,) in genders:
        print(f"  {val}")
    
    # Boolean values
    print("\nBoolean values (is_* fields):")
    bools = db.session.execute(db.text(
        "SELECT DISTINCT value FROM conditions WHERE operator = 'eq' AND field LIKE 'is_%'"
    )).fetchall()
    for (val,) in bools:
        print(f"  {val}")
    
    print("\n" + "=" * 60)
    print("FIXES COMPLETE")
    print("=" * 60)
