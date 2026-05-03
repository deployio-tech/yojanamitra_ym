"""
find_db.py — finds your real SQLite database and prints its table structure.
Run: python find_db.py
"""
import sqlite3, os, glob, sys

print("=== Searching for SQLite databases ===\n")

# Search common locations
search_paths = [
    ".",
    "..",
    os.path.expanduser("~"),
    os.path.join(os.path.expanduser("~"), "AppData"),
]

found = []
for root, dirs, files in os.walk("."):
    # Skip node_modules, .git, __pycache__
    dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "__pycache__", "venv", ".venv")]
    for f in files:
        if f.endswith(".db") or f.endswith(".sqlite") or f.endswith(".sqlite3"):
            path = os.path.join(root, f)
            size = os.path.getsize(path)
            found.append((path, size))

if not found:
    print("No .db/.sqlite files found in current directory tree.")
    print("Checking environment variables for DATABASE_URL...")

# Also check .env file
for envfile in [".env", "../.env"]:
    if os.path.exists(envfile):
        with open(envfile) as f:
            for line in f:
                if "DATABASE" in line.upper() or "DB" in line.upper() or "SQLITE" in line.upper():
                    print(f"  {envfile}: {line.strip()}")

# Also check app.py for SQLALCHEMY_DATABASE_URI
for appfile in ["app.py", "../app.py"]:
    if os.path.exists(appfile):
        with open(appfile, encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f):
                if "DATABASE_URI" in line or "database_uri" in line or "sqlite" in line.lower():
                    print(f"  app.py line {i+1}: {line.strip()}")

print("\nFound DB files:")
for path, size in sorted(found, key=lambda x: -x[1]):
    print(f"  {path}  ({size:,} bytes)")
    if size > 0:
        try:
            conn = sqlite3.connect(path)
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            conn.close()
            print(f"    Tables: {tables}")
            if any("scheme" in t.lower() for t in tables):
                print(f"    *** THIS IS THE ONE ***")
        except Exception as e:
            print(f"    Error reading: {e}")
