import sys
sys.path.insert(0, '.')
from app import app, db, Condition

with app.app_context():
    # First check existing
    existing = Condition.query.filter_by(scheme_id=4338).all()
    print('Existing conditions:', len(existing))
    for c in existing:
        print(f'  {c.field} {c.operator} {c.value}')
    
    # Add the title-augmented condition
    c = Condition(
        scheme_id=4338,
        field='occupation',
        operator='eq',
        value='"faculty"',
        condition_type='hard',
        confidence=0.9,
        source='title_inference',
        source_fragment='title_inference'
    )
    db.session.add(c)
    db.session.commit()
    print('\nAdded occupation = faculty condition')
    
    # Verify
    updated = Condition.query.filter_by(scheme_id=4338).all()
    print('\nUpdated conditions:', len(updated))
    for c in updated:
        print(f'  {c.field} {c.operator} {c.value}')
