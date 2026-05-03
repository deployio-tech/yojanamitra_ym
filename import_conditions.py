"""
Import conditions from all_conditions.json into the database
"""
import json
import sys
sys.path.insert(0, '.')

# Import through the dynamically loaded app
import importlib.util
_root = '.'
_app_py = 'app.py'
_flask_app_mod = importlib.util.spec_from_file_location("flask_app", _app_py)
_flask_app = importlib.util.module_from_spec(_flask_app_mod)
_flask_app_mod.loader.exec_module(_flask_app)

app = _flask_app.app
db = _flask_app.db
Scheme = _flask_app.Scheme
Condition = _flask_app.Condition

def import_conditions():
    with app.app_context():
        # Load JSON
        print("Loading JSON file...")
        with open('all_conditions.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        schemes_data = data.get('schemes', {})
        print(f"Found {len(schemes_data)} schemes in JSON")
        
        # Track stats
        imported = 0
        skipped = 0
        errors = 0
        
        # Map JSON operators to engine operators
        operator_map = {
            'must_be': 'eq',
            'must_not_be': 'neq',
            'min': 'gte',
            'max': 'lte',
            'range': 'range',
        }
        
        for scheme_id_str, scheme_data in schemes_data.items():
            scheme_id = int(scheme_id_str)
            scheme = Scheme.query.get(scheme_id)
            
            if not scheme:
                skipped += 1
                continue
            
            conditions = scheme_data.get('conditions', [])
            
            for cond in conditions:
                try:
                    field = cond.get('field')
                    if not field:
                        continue
                    
                    # Map operator
                    json_op = cond.get('operator', 'must_be')
                    operator = operator_map.get(json_op, json_op)
                    
                    # Get value
                    value = cond.get('value')
                    
                    # Determine condition type
                    cond_type = 'hard'
                    if cond.get('required') is False:
                        cond_type = 'soft'
                    
                    # Confidence
                    confidence = cond.get('confidence', 0.7)
                    
                    # Skip low confidence
                    if confidence < 0.5:
                        continue
                    
                    # Create condition
                    c = Condition(
                        scheme_id=scheme.id,
                        field=field,
                        operator=operator,
                        value=str(value) if not isinstance(value, (list, dict)) else json.dumps(value),
                        condition_type=cond_type,
                        confidence=confidence,
                        is_ambiguous=not cond.get('_mapped', True),
                        source_fragment=cond.get('source_text', '')[:500],
                    )
                    db.session.add(c)
                    imported += 1
                    
                except Exception as e:
                    errors += 1
                    print(f"Error importing condition {field}: {e}")
        
        db.session.commit()
        
        print(f"\n=== IMPORT COMPLETE ===")
        print(f"Imported: {imported}")
        print(f"Skipped (no scheme): {skipped}")
        print(f"Errors: {errors}")
        
        # Verify
        total = sum(len(list(s.condition_rows)) for s in Scheme.query.filter_by(is_active=True).all())
        print(f"Total conditions in DB: {total}")

if __name__ == '__main__':
    import_conditions()
