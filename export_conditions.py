import sqlite3
import json

print("Exporting data from database...")

conn = sqlite3.connect('instance/yojanamitra.db')
rows = conn.execute("SELECT scheme_id, extracted_json, confidence, extraction_notes FROM gemini_prefill WHERE status='success'").fetchall()

data = {}
for row in rows:
    try:
        data[row[0]] = {
            'conditions': json.loads(row[1] if row[1] else "{}"),
            'confidence': row[2],
            'notes': row[3]
        }
    except Exception as e:
        print(f"Skipping scheme_id {row[0]} due to JSON error: {e}")

with open('all_extracted_conditions.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Done! Saved as all_extracted_conditions.json")
