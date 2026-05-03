import os, sqlite3

files = [
    'yojanamitra.db',
    'instance/yojanamitra.db', 
    'instance/yojanamitra_empty.db',
    'instance/yojanamitra_backup_pre_json_merge.db',
    'yojana.db'
]

for f in files:
    if os.path.exists(f):
        sz = os.path.getsize(f)
        print(f"FOUND: {f} = {sz:,} bytes ({sz/1024:.1f} KB)")
        try:
            conn = sqlite3.connect(f)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM scheme")
            cnt = c.fetchone()[0]
            print(f"  -> Schemes: {cnt}")
            conn.close()
        except Exception as e:
            print(f"  -> Error: {e}")
    else:
        print(f"MISSING: {f}")
