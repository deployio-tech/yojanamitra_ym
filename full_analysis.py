import sqlite3  
conn=sqlite3.connect('instance/yojanamitra.db')  
cur=conn.cursor()  
cur.execute('''SELECT c.scheme_id, COUNT(*) as cond_count, SUM(CASE WHEN c.condition_type='hard' THEN 1 ELSE 0 END) as hard_count, COUNT(DISTINCT c.field) as field_count, s.name FROM conditions c INNER JOIN gemini_prefill g ON c.scheme_id=g.scheme_id JOIN scheme s ON c.scheme_id=s.id WHERE c.source='production_v3_turbo' GROUP BY c.scheme_id ORDER BY cond_count DESC''')  
results=cur.fetchall()  
scored=[]  
for r in results: score=r[1]*1+r[2]*2+r[3]*3; scored.append((r[0],r[4][:55],r[1],r[2],r[3],score))  
scored.sort(key=lambda x:x[5],reverse=True)  
for i,r in enumerate(scored[:50],1): print(i,r[0],r[1],'conds:',r[2],'hard:',r[3],'fields:',r[4],'score:',r[5])  
print('Total gemini_prefill schemes:',len(scored))  
conn.close() 
