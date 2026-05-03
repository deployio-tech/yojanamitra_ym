import json  
data=json.load(open('all_conditions.json','r',encoding='utf-8')) 
schemes=data['schemes'] 
results=[] 
for scheme_id,scheme_data in schemes.items(): 
    conditions=scheme_data.get('conditions',[]) 
    total=len(conditions) 
    if total==0: continue 
    hard=len([c for c in conditions if c.get('required',False)]) 
    fields=len(set(c.get('field','') for c in conditions if c.get('field'))) 
    score=total*1+hard*2+fields*3 
    results.append({'scheme_id':scheme_id,'total':total,'hard':hard,'fields':fields,'score':score}) 
results.sort(key=lambda x:x['score'],reverse=True)
for i,r in enumerate(results[:100],1): print(i,r['scheme_id'],r['total'],r['hard'],r['fields'],r['score']) 
print(len(results)) 
print(sum(r['total']for r in results)/len(results))
