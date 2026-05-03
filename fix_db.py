import sqlite3
import os

db_path = 'yojanamitra.db'
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check columns in 'user' table
try:
    cursor.execute("PRAGMA table_info(user)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Columns in 'user' table: {columns}")
    
    if 'year_of_study' not in columns:
        print("Adding 'year_of_study' column to 'user' table...")
        cursor.execute("ALTER TABLE user ADD COLUMN year_of_study TEXT")
        conn.commit()
        print("Column added successfully.")
    else:
        print("'year_of_study' column already exists.")
except Exception as e:
    print(f"Error checking/updating user table: {e}")

# Also check 'scholarship_application' if it exists (though not needed for now)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"Tables in DB: {tables}")

conn.close()
