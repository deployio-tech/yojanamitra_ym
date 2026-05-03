"""
QUESTION COVERAGE AUDIT
========================

Verify that questions are being asked for ALL missing information
that could potentially affect eligibility.

Test:
1. Load user profile with 57 unknown fields
2. Evaluate schemes to find POSSIBLE results
3. Generate questions from POSSIBLE schemes
4. Verify coverage - which missing fields are being asked about
5. Identify gaps - missing fields NOT being asked about
6. Analyze why some fields not asked (non-answerable, no templates, etc.)
"""

import os
import sys
import json
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Scheme, User
from app.engine.eligibility import EligibilityEngine
from app.engine.questions import QuestionEngine, QUESTION_TEMPLATES, NON_ANSWERABLE_FIELDS

print("\n" + "=" * 100)
print("QUESTION COVERAGE AUDIT - ALL MISSING FIELDS")
print("=" * 100)

with app.app_context():
    # Load user with missing fields
    user = User.query.filter_by(email='shreyas6504@gmail.com').first()
    
    if not user:
        print("❌ User not found!")
        sys.exit(1)
    
    print(f"\nUser: {user.name} (ID: {user.id})")
    
    profile = user.get_profile_dict()
    
    # Identify missing vs known fields
    known_fields = {k: v for k, v in profile.items() if v is not None}
    unknown_fields = [k for k, v in profile.items() if v is None]
    
    print(f"\n[1] USER PROFILE STATUS")
    print("-" * 100)
    print(f"Known fields: {len(known_fields)}")
    for k, v in known_fields.items():
        print(f"  • {k}: {v}")
    
    print(f"\nUnknown fields (missing): {len(unknown_fields)}")
    for i, f in enumerate(unknown_fields[:20], 1):
        print(f"  {i}. {f}")
    if len(unknown_fields) > 20:
        print(f"  ... and {len(unknown_fields) - 20} more")
    
    # Evaluate to find POSSIBLE schemes
    print(f"\n[2] FINDING SCHEMES IN POSSIBLE STATE")
    print("-" * 100)
    
    engine = EligibilityEngine()
    possible_schemes = []
    
    schemes = Scheme.query.limit(100).all()
    
    for scheme in schemes:
        result = engine.evaluate(scheme, profile)
        if result.result.lower() == 'possible':
            possible_schemes.append((scheme, result))
    
    print(f"Found {len(possible_schemes)} POSSIBLE schemes (from first 100 evaluated)")
    
    if not possible_schemes:
        print("❌ No POSSIBLE schemes found - cannot generate questions!")
        sys.exit(1)
    
    # Generate questions
    print(f"\n[3] GENERATING QUESTIONS")
    print("-" * 100)
    
    qengine = QuestionEngine()
    questions = qengine.select_questions(possible_schemes, profile)
    
    print(f"Generated {len(questions)} questions")
    
    # Map which fields are asked about
    asked_fields = set()
    question_map = defaultdict(list)
    
    for q in questions:
        field = q.field
        asked_fields.add(field)
        question_map[field].append({
            'text': q.text,
            'concept': q.concept,
            'type': q.field_type,
            'schemes': q.schemes_affected
        })
    
    print(f"\nQuestions breakdown:")
    for i, q in enumerate(questions[:10], 1):
        print(f"\n  [{i}] {q.field}")
        print(f"      Text: {q.text}")
        print(f"      Concept: {q.concept}")
        print(f"      Type: {q.field_type}")
        print(f"      Affects schemes: {len(q.schemes_affected)}")
    
    if len(questions) > 10:
        print(f"\n  ... and {len(questions) - 10} more questions")
    
    # Coverage analysis
    print(f"\n[4] COVERAGE ANALYSIS")
    print("-" * 100)
    
    # Which missing fields are asked about?
    missing_fields_asked = [f for f in unknown_fields if f in asked_fields]
    missing_fields_not_asked = [f for f in unknown_fields if f not in asked_fields]
    
    if unknown_fields:
        print(f"\nMissing fields being asked about: {len(missing_fields_asked)}/{len(unknown_fields)}")
        print(f"Coverage: {len(missing_fields_asked)/len(unknown_fields)*100:.1f}%")
        
        print(f"\nFields ASKED about ({len(missing_fields_asked)}):")
        if missing_fields_asked:
            for f in sorted(missing_fields_asked):
                q_info = question_map[f]
                print(f"  ✓ {f}")
                for q in q_info:
                    print(f"    → {q['text'][:60]}...")
        
        print(f"\nFields NOT asked about ({len(missing_fields_not_asked)}):")
        for i, f in enumerate(missing_fields_not_asked[:15], 1):
            status = "NON-ANSWERABLE" if f in NON_ANSWERABLE_FIELDS else "NO TEMPLATE"
            has_template = f in QUESTION_TEMPLATES
            print(f"  {i}. {f:40s} [{status}] template={has_template}")
        
        if len(missing_fields_not_asked) > 15:
            print(f"  ... and {len(missing_fields_not_asked) - 15} more")
    else:
        print(f"\n✓ All user fields are known! No missing fields in profile.")
        print(f"  Questions are being asked for scheme-specific conditions.")
        print(f"  Currently asking about: {', '.join(sorted(asked_fields))}")
    
    # Analyze why fields are not asked
    print(f"\n[5] WHY SOME FIELDS NOT ASKED")
    print("-" * 100)
    
    if unknown_fields:
        non_answerable_not_asked = [f for f in missing_fields_not_asked if f in NON_ANSWERABLE_FIELDS]
        no_template_not_asked = [f for f in missing_fields_not_asked if f not in QUESTION_TEMPLATES]
        
        print(f"\nNon-answerable fields (system/derived): {len(non_answerable_not_asked)}")
        for f in sorted(non_answerable_not_asked)[:10]:
            print(f"  • {f} (cannot be user-answered)")
        
        print(f"\nFields with no question template: {len(no_template_not_asked)}")
        for f in sorted(no_template_not_asked)[:10]:
            print(f"  • {f} (no template defined)")
    else:
        print("\nNo missing fields to analyze.")
    
    # Check scheme conditions to see what fields are actually needed
    print(f"\n[6] CONDITION FIELD REQUIREMENTS")
    print("-" * 100)
    
    required_fields = defaultdict(int)
    
    for scheme, result in possible_schemes:
        # Count conditions by field
        for cond in scheme.conditions:
            required_fields[cond.field] += 1
    
    print(f"\nFields required by POSSIBLE schemes (top 20):")
    for field, count in sorted(required_fields.items(), key=lambda x: -x[1])[:20]:
        is_asked = "✓ ASKED" if field in asked_fields else "✗ NOT ASKED"
        is_missing = "MISSING" if field in unknown_fields else "KNOWN"
        print(f"  {field:30s} - {count:3d} conditions | {is_asked} | {is_missing}")
    
    # Final statistics
    print(f"\n[7] QUESTION COVERAGE STATISTICS")
    print("-" * 100)
    
    # How many missing-but-required fields are being asked about?
    missing_required_fields = [f for f in required_fields.keys() if f in unknown_fields]
    missing_required_asked = [f for f in missing_required_fields if f in asked_fields]
    
    print(f"\nTotal unknown fields in profile: {len(unknown_fields)}")
    print(f"Total fields required by schemes: {len(required_fields)}")
    
    if unknown_fields:
        print(f"Missing fields required by schemes: {len(missing_required_fields)}")
        print(f"Missing required fields being asked: {len(missing_required_asked)}")
        if missing_required_fields:
            print(f"Required field coverage: {len(missing_required_asked)}/{len(missing_required_fields)} ({len(missing_required_asked)/len(missing_required_fields)*100:.1f}%)")
    
    print(f"\nQuestion statistics:")
    print(f"  Total questions generated: {len(questions)}")
    print(f"  Unique fields targeted: {len(asked_fields)}")
    
    if unknown_fields:
        print(f"  Missing field coverage: {len(missing_fields_asked)}/{len(unknown_fields)} ({len(missing_fields_asked)/len(unknown_fields)*100:.1f}%)")
        non_answerable_not_asked = [f for f in missing_fields_not_asked if f in NON_ANSWERABLE_FIELDS]
        no_template_not_asked = [f for f in missing_fields_not_asked if f not in QUESTION_TEMPLATES]
        print(f"  Non-answerable fields skipped: {len(non_answerable_not_asked)}")
        print(f"  Fields with no template: {len(no_template_not_asked)}")
    else:
        print(f"  Profile completeness: 100% (all fields known)")
        print(f"  Questions are for condition-specific clarifications")

print("\n" + "=" * 100)
print("QUESTION COVERAGE AUDIT COMPLETE")
print("=" * 100)
