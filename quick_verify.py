import sys
sys.path.insert(0, '.')
from app import app, User, Scheme
from app.engine.eligibility import (
    EligibilityEngine, 
    get_canonical_field,
    discover_all_required_fields, 
    validate_and_normalize, 
    simulate_answer
)
from app.engine.questions import is_user_answerable

def generate_question(field):
    return {'field': field}

with app.app_context():
    user = User.query.filter_by(email='shreyas6504@gmail.com').first()
    profile = user.get_profile_dict()
    
    engine = EligibilityEngine()
    all_schemes = Scheme.query.filter_by(is_active=True).all()
    
    print('=== PHASE 1: DISCOVERY ===')
    fields = discover_all_required_fields(engine, all_schemes, profile, max_depth=5)
    print(f'Discovered fields: {len(fields)}')
    
    print('')
    print('=== PHASE 2: QUESTIONS ===')
    questions = [generate_question(f) for f in fields]
    print(f'Questions: {len(questions)}')
    
    print('')
    print('=== PHASE 3: ANSWERS ===')
    answers = {}
    for q in questions:
        answers[q['field']] = simulate_answer(q['field'], profile)
    print(f'Answers: {len(answers)}')
    
    print('')
    print('=== PHASE 4: EVALUATION ===')
    final_profile = dict(profile)
    for field, value in answers.items():
        canonical = get_canonical_field(field)
        final_profile[canonical] = validate_and_normalize(canonical, value)
    
    results = {'eligible': 0, 'possible': 0, 'ineligible': 0}
    missing_after = 0
    
    for scheme in all_schemes:
        eo = engine.evaluate(scheme, final_profile)
        results[eo.result] += 1
        
        remaining = [get_canonical_field(f) for f in eo.missing_fields if is_user_answerable(f)]
        if remaining:
            missing_after += 1
    
    print(f'ELIGIBLE: {results["eligible"]}')
    print(f'POSSIBLE: {results["possible"]}')
    print(f'INELIGIBLE: {results["ineligible"]}')
    print(f'Schemes with remaining missing: {missing_after}')
    
    if missing_after == 0:
        print('')
        print('=== SUCCESS: NO MISSING AFTER USER ANSWERS! ===')