import sys
sys.path.insert(0, '.')
from app import app, User, Scheme
from app.engine.eligibility import (
    EligibilityEngine, 
    get_canonical_field, 
    validate_and_normalize,
    discover_all_required_fields,
    simulate_answer
)
from app.engine.questions import is_user_answerable, QUESTION_TEMPLATES
import time

def generate_question(field):
    """Generate a question for a field."""
    text = QUESTION_TEMPLATES.get(field) or f"Do you qualify as: {field.replace('_', ' ')}?"
    return {"field": field, "text": text}

def run_complete_evaluation(profile):
    """
    FINAL 3-PHASE SYSTEM:
    Phase 1: Global discovery of ALL required fields
    Phase 2: Generate ALL questions at once
    Phase 3: Final evaluation with real answers
    """
    with app.app_context():
        engine = EligibilityEngine()
        
        all_schemes = Scheme.query.filter_by(is_active=True).all()
        
        print(f"Total schemes: {len(all_schemes)}")
        
        # === PHASE 1: GLOBAL FIELD DISCOVERY ===
        print("\n=== PHASE 1: GLOBAL FIELD DISCOVERY ===")
        start = time.time()
        
        all_discovered_fields = discover_all_required_fields(
            engine, all_schemes, profile, max_depth=5
        )
        
        print(f"Discovered {len(all_discovered_fields)} unique fields")
        print(f"Fields: {sorted(all_discovered_fields)}")
        print(f"Time: {time.time() - start:.1f}s")
        
        # === PHASE 2: GENERATE ALL QUESTIONS ===
        print("\n=== PHASE 2: GENERATE ALL QUESTIONS ===")
        
        questions = []
        for field in all_discovered_fields:
            questions.append(generate_question(field))
        
        print(f"Generated {len(questions)} questions")
        
        # === PHASE 3: SIMULATE USER ANSWERS (for testing) ===
        print("\n=== PHASE 3: USER ANSWERS (simulated) ===")
        
        user_answers = {}
        for q in questions:
            # EDGE FIX 1: Normalize answers
            user_answers[q["field"]] = simulate_answer(q["field"], profile)
        
        print(f"User answered {len(user_answers)} questions")
        
        # === PHASE 4: FINAL EVALUATION ===
        print("\n=== PHASE 4: FINAL EVALUATION ===")
        
        # Update profile with REAL answers (no simulation)
        final_profile = dict(profile)
        for field, value in user_answers.items():
            canonical = get_canonical_field(field)
            final_profile[canonical] = validate_and_normalize(canonical, value)
        
        results = {"eligible": 0, "possible": 0, "ineligible": 0}
        missing_after_answers = []
        
        for scheme in all_schemes:
            eo = engine.evaluate(scheme, final_profile)
            results[eo.result] += 1
            
            # === ULTIMATE CORRECTNESS TEST ===
            remaining_missing = [
                get_canonical_field(f)
                for f in eo.missing_fields
                if is_user_answerable(f)
            ]
            if remaining_missing:
                missing_after_answers.append((scheme.name, remaining_missing))
        
        print(f"\n=== VALIDATION RESULTS ===")
        print(f"ELIGIBLE: {results['eligible']}")
        print(f"POSSIBLE: {results['possible']}")
        print(f"INELIGIBLE: {results['ineligible']}")
        print(f"TOTAL: {results['eligible'] + results['possible'] + results['ineligible']}")
        
        if missing_after_answers:
            print(f"\n⚠️ WARNING: {len(missing_after_answers)} schemes still have missing fields:")
            for name, fields in missing_after_answers[:10]:
                print(f"  {name}: {fields}")
        else:
            print(f"\n✅ SUCCESS: NO MISSING FIELDS AFTER USER ANSWERS!")
        
        return results, missing_after_answers

# === RUN FOR ORIGINAL USER ===
print("=" * 70)
print("COMPLETE FIELD DISCOVERY SYSTEM - ORIGINAL USER")
print("=" * 70)

with app.app_context():
    user = User.query.filter_by(email='shreyas6504@gmail.com').first()
    profile = user.get_profile_dict()
    
    print("\nUser Profile:")
    for k, v in list(profile.items())[:10]:
        print(f"  {k}: {v}")
    print("  ...")

results, missing = run_complete_evaluation(profile)

print("\n" + "=" * 70)
print("FINAL RESULT")
print("=" * 70)
print(f"ELIGIBLE: {results['eligible']}")
print(f"POSSIBLE: {results['possible']}")
print(f"INELIGIBLE: {results['ineligible']}")
print("=" * 70)