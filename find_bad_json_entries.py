
import json
with open('all_conditions.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    for sid, entry in data.items():
        if not isinstance(entry, dict):
            print(f"Scheme {sid} entry is not a dict: {type(entry)}")
            continue
        
        conds = entry.get('conditions', [])
        if conds is None: conds = []
        if not isinstance(conds, list):
            print(f"Scheme {sid} conditions is not a list: {type(conds)}")
        else:
            for i, c in enumerate(conds):
                if not isinstance(c, dict):
                    print(f"Scheme {sid} condition {i} is not a dict: {type(c)}")
        
        disqs = entry.get('disqualifiers', [])
        if disqs is None: disqs = []
        if not isinstance(disqs, list):
            # The current code might not handle this if it expects a list
            pass
        else:
            for i, d in enumerate(disqs):
                if not isinstance(d, dict):
                    print(f"Scheme {sid} disqualifier {i} is not a dict: {type(d)}")
