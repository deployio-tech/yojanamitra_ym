import sqlite3, json
conn = sqlite3.connect('instance/yojanamitra.db')
conn.row_factory = sqlite3.Row
r = conn.execute("SELECT * FROM user WHERE email = 'shreyas6504@gmail.com'").fetchone()
if r:
    print(json.dumps(dict(r), indent=2))
conn.close()
