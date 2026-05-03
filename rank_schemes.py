import sqlite3  
conn=sqlite3.connect('instance/yojanamitra.db')  
cur=conn.cursor()  
cur.execute('''SELECT c.scheme_id, COUNT(*) as cond_count, SUM(CASE WHEN c.condition_type='hard' THEN 1 ELSE 0 END) as hard_count, COUNT(DISTINCT c.field) as field_count FROM conditions c INNER JOIN gemini_prefill g ON c.scheme_id=g.scheme_id WHERE c.source='production_v3_turbo' GROUP BY c.scheme_id ORDER BY cond_count DESC''')  
results=cur.fetchall()  
for r in results[:100]: print(r[0],r[1],r[2],r[3])  
print('Total:',len(results))  
conn.close() 
