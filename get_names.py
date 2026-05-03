import sqlite3  
conn=sqlite3.connect('instance/yojanamitra.db')  
cur=conn.cursor()  
cur.execute('SELECT g.scheme_id, g.extracted_json, s.name FROM gemini_prefill g JOIN scheme s ON g.scheme_id=s.id ORDER BY g.scheme_id')  
rows=cur.fetchall()  
print('Total:',len(rows))  
for r in rows[:20]: print(r[0],str(r[2])[:60])  
conn.close() 
