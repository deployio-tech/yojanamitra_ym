"""
Analyze schemes to find state with lowest number of schemes
"""
from app import app, db, Scheme, Condition
from collections import Counter
import json

with app.app_context():
    schemes = Scheme.query.all()
    print(f'Total schemes: {len(schemes)}')
    
    # Count schemes per state from Condition table
    state_counts = Counter()
    state_schemes = {}
    
    # Get all conditions related to state
    conditions = Condition.query.filter(Condition.field.like('%state%')).all()
    print(f'State conditions found: {len(conditions)}')
    
    for cond in conditions:
        try:
            val = cond.parsed_value
            if isinstance(val, list):
                for v in val:
                    state_counts[v] += 1
                    if v not in state_schemes:
                        state_schemes[v] = []
                    state_schemes[v].append(cond.scheme_id)
            else:
                state_counts[val] += 1
                if val not in state_schemes:
                    state_schemes[val] = []
                state_schemes[val].append(cond.scheme_id)
        except Exception as e:
            pass
    
    # Also check 'allowed_states' in old schema
    for scheme in schemes:
        if scheme.allowed_states:
            try:
                states = json.loads(scheme.allowed_states)
                for s in states:
                    state_counts[s] += 1
                    if s not in state_schemes:
                        state_schemes[s] = []
                    state_schemes[s].append(scheme.id)
            except:
                pass
    
    print('\nSchemes per state (sorted by count ascending):')
    sorted_states = sorted(state_counts.items(), key=lambda x: x[1])
    for state, count in sorted_states:
        print(f'  {state}: {count} schemes')
    
    if sorted_states:
        min_state = sorted_states[0][0]
        print(f'\nState with LOWEST schemes: {min_state} ({sorted_states[0][1]} schemes)')
        
        # Save to file for next step
        with open('lowest_state.txt', 'w') as f:
            f.write(min_state)
