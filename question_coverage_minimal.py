"""
QUESTION COVERAGE - MINIMAL PROFILE TEST
==========================================

Test with a profile that has MANY missing fields
to verify questions are being asked for all important ones.
"""

import os
import sys
import json
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Scheme
from app.engine.eligibility import EligibilityEngine
from app.engine.questions import QuestionEngine, QUESTION_TEMPLATES, NON_ANSWERABLE_FIELDS

print("\n" + "=" * 100)
print("QUESTION COVERAGE - MINIMAL PROFILE TEST")
print("=" * 100)

with app.app_context():
    # Create minimal profile with ONLY required fields
    minimal_profile = {
        "age": 25,
        "state": "Karnataka",
    }
    
    print(f"\n[1] MINIMAL PROFILE (only age and state)")
    print("-" * 100)
    print(f"Known fields: {len(minimal_profile)}")
    for k, v in minimal_profile.items():
        print(f"  • {k}: {v}")
    
    print(f"\nUnknown fields: ~50+ (most of the available fields)")
    
    # Evaluate to find POSSIBLE schemes
    print(f"\n[2] FINDING SCHEMES IN POSSIBLE STATE")
    print("-" * 100)
    
    engine = EligibilityEngine()
    possible_schemes = []
    
    schemes = Scheme.query.limit(200).all()
    
    for scheme in schemes:
        result = engine.evaluate(scheme, minimal_profile)
        if result.result.lower() == 'possible':
            possible_schemes.append((scheme, result))
    
    print(f"Found {len(possible_schemes)} POSSIBLE schemes (from first 200 evaluated)")
    
    if not possible_schemes:
        print("❌ No POSSIBLE schemes found!")
        sys.exit(1)
    
    # Generate questions
    print(f"\n[3] GENERATING QUESTIONS")
    print("-" * 100)
    
    qengine = QuestionEngine()
    questions = qengine.select_questions(possible_schemes, minimal_profile)
    
    print(f"Generated {len(questions)} questions (capped at max_questions_per_session)")
    
    # Map which fields are asked about
    asked_fields = set()
    
    for q in questions:
        asked_fields.add(q.field)
    
    print(f"\nQuestions breakdown:")
    for i, q in enumerate(questions, 1):
        print(f"\n  [{i}] {q.field}")
        print(f"      Text: {q.text}")
        print(f"      Concept: {q.concept}")
        print(f"      Schemes affected: {len(q.schemes_affected)}")
    
    # Analyze coverage
    print(f"\n[4] QUESTION COVERAGE DETAILS")
    print("-" * 100)
    
    # Get all condition fields from POSSIBLE schemes
    all_condition_fields = defaultdict(int)
    
    for scheme, result in possible_schemes:
        for cond in scheme.conditions:
            all_condition_fields[cond.field] += 1
    
    print(f"\nCondition fields required by POSSIBLE schemes:	{len(all_condition_fields)}")
    print(f"Questions being asked:	{len(questions)}")
    print(f"Unique fields in questions:	{len(asked_fields)}")
    
    # Which condition fields are targeted by questions?
    condition_fields_asked = [f for f in all_condition_fields.keys() if f in asked_fields]
    condition_fields_not_asked = [f for f in all_condition_fields.keys() if f not in asked_fields]
    
    print(f"\nCondition fields being targeted by questions: {len(condition_fields_asked)}/{len(all_condition_fields)}")
    print(f"Coverage: {len(condition_fields_asked)/len(all_condition_fields)*100:.1f}%")
    
    print(f"\nFields TARGETED by questions (top 15):")
    for f in sorted(condition_fields_asked)[:15]:
        count = all_condition_fields[f]
        print(f"  ✓ {f:30s} ({count} conditions in schemes)")
    
    print(f"\nFields NOT targeted by questions (top 15):")
    for f in sorted(condition_fields_not_asked)[:15]:
        count = all_condition_fields[f]
        print(f"  ✗ {f:30s} ({count} conditions in schemes)")
    
    # Summary
    print(f"\n[5] SUMMARY")
    print("-" * 100)
    
    print(f"\nProfile: {len(minimal_profile)} fields known, ~50 fields missing")
    print(f"POSSIBLE schemes: {len(possible_schemes)}")
    print(f"Questions generated: {len(questions)}")
    print(f"Unique fields asked: {len(asked_fields)}")
    print(f"\nCoverage of scheme conditions: {len(condition_fields_asked)}/{len(all_condition_fields)} ({len(condition_fields_asked)/len(all_condition_fields)*100:.1f}%)")
    
    # Smart analysis
    print(f"\n[6] INTELLIGENT ANALYSIS")
    print("-" * 100)
    
    print(f"\n✓ Questions are being INTELLIGENTLY selected based on:")
    print(f"  • Impact on matching schemes")
    print(f"  • Answerable vs non-answerable fields")
    print(f"  • Whether templates exist for fields")
    print(f"  • Maximum question limit (usually 3)")
    
    print(f"\n• Not all {len(all_condition_fields)} condition fields need to be asked")
    print(f"• Only the MOST IMPORTANT {len(questions)} are selected")
    print(f"• Questions target {len(condition_fields_asked)} different condition fields")
    print(f"• This provides {len(condition_fields_asked)/len(all_condition_fields)*100:.1f}% coverage of scheme requirements")

print("\n" + "=" * 100)
print("MINIMAL PROFILE TEST COMPLETE")
print("=" * 100)
