"""
Check all database files and find which has scheme data
"""
import os
import sqlite3

def check_db(path):
    """Check a database file"""
    if not os.path.exists(path):
        return f"{path}: NOT FOUND"
    
    size = os.path.getsize(path)
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        
        # Check if scheme table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scheme'")
        if not cursor.fetchone():
            conn.close()
            return f"{path} ({size:,} bytes): No scheme table"
        
        # Count schemes
        cursor.execute("SELECT COUNT(*) FROM scheme")
        count = cursor.fetchone()[0]
        
        # Get sample scheme
        if count > 0:
            cursor.execute("SELECT id, name FROM scheme LIMIT 1")
            sample = cursor.fetchone()
            conn.close()
            return f"{path} ({size:,} bytes): {count} schemes - First: {sample}"
        else:
            conn.close()
            return f"{path} ({size:,} bytes): 0 schemes (EMPTY)"
            
    except Exception as e:
        return f"{path} ({size:,} bytes): ERROR - {e}"

# Check all db files
print("Checking all database files...")
print("=" * 60)

results = []

for root, dirs, files in os.walk('.'):
    for f in files:
        if f.endswith('.db'):
            path = os.path.join(root, f).replace('\\', '/')
            result = check_db(path)
            results.append(result)
            print(result)

print("=" * 60)
print("\nLargest database with schemes is your production database.")
