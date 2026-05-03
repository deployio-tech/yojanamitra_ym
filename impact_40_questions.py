"""
IMPACT ANALYSIS: INCREASING QUESTION LIMIT FROM 20 TO 40
========================================================

Compare coverage with 20-question limit vs 40-question limit
"""

import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Scheme
from app.engine.eligibility import EligibilityEngine
from app.engine.questions import QuestionEngine

print("\n" + "=" * 120)
print("QUESTION LIMIT IMPACT ANALYSIS: 20 vs 40 QUESTIONS")
print("=" * 120)

with app.app_context():
    # Minimal profile with ~50 missing fields
    minimal_profile = {
        "age": 25,
        "state": "Karnataka",
    }
    
    print(f"\n[SETUP] Minimal profile: age=25, state=Karnataka (50+ fields missing)")
    
    # Find POSSIBLE schemes
    engine = EligibilityEngine()
    possible_schemes = []
    schemes = Scheme.query.limit(200).all()
    
    for scheme in schemes:
        result = engine.evaluate(scheme, minimal_profile)
        if result.result.lower() == 'possible':
            possible_schemes.append((scheme, result))
    
    print(f"[SETUP] Found {len(possible_schemes)} POSSIBLE schemes")
    
    # ========================================
    # TEST 1: Current behavior (20 questions)
    # ========================================
    print(f"\n" + "-" * 120)
    print(f"TEST 1: CURRENT BEHAVIOR (MAX 20 QUESTIONS)")
    print("-" * 120)
    
    qengine = QuestionEngine()
    questions_20 = qengine.select_questions(possible_schemes, minimal_profile)
    
    asked_fields_20 = {q.field for q in questions_20}
    
    print(f"\nQuestions generated: {len(questions_20)}")
    print(f"Fields targeted: {len(asked_fields_20)}")
    
    print(f"\nFields being asked (20-question limit):")
    for i, q in enumerate(questions_20, 1):
        print(f"  {i:2d}. {q.field:<25} ({q.schemes_affected} schemes affected)")
    
    # ========================================
    # TEST 2: Increased limit (40 questions)
    # ========================================
    print(f"\n" + "-" * 120)
    print(f"TEST 2: WITH 40-QUESTION LIMIT")
    print("-" * 120)
    
    # Patch QuestionEngine to use 40 max questions
    qengine.max_questions_per_session = 40
    questions_40 = qengine.select_questions(possible_schemes, minimal_profile)
    
    asked_fields_40 = {q.field for q in questions_40}
    
    print(f"\nQuestions generated: {len(questions_40)}")
    print(f"Fields targeted: {len(asked_fields_40)}")
    
    print(f"\nFields being asked (40-question limit):")
    for i, q in enumerate(questions_40, 1):
        if i <= 20:
            prefix = "  "
            label = i
        else:
            prefix = "  **NEW** "
            label = i
        print(f"{prefix}{label:2d}. {q.field:<25} ({q.schemes_affected} schemes affected)")
    
    # ========================================
    # COMPARISON
    # ========================================
    print(f"\n" + "=" * 120)
    print(f"COMPARISON: 20 vs 40 QUESTIONS")
    print("=" * 120)
    
    new_fields = asked_fields_40 - asked_fields_20
    
    print(f"\nQuestions:")
    print(f"  With 20-question limit:  {len(questions_20):2d} questions")
    print(f"  With 40-question limit:  {len(questions_40):2d} questions")
    print(f"  DIFFERENCE:              +{len(questions_40) - len(questions_20):2d} additional questions")
    
    print(f"\nFields covered:")
    print(f"  With 20-question limit:  {len(asked_fields_20):2d} fields")
    print(f"  With 40-question limit:  {len(asked_fields_40):2d} fields")
    print(f"  DIFFERENCE:              +{len(asked_fields_40) - len(asked_fields_20):2d} new fields")
    
    # Get all condition fields
    all_condition_fields = set()
    for scheme, _ in possible_schemes:
        for cond in scheme.conditions:
            all_condition_fields.add(cond.field)
    
    print(f"\nField coverage:")
    print(f"  Total condition fields:  {len(all_condition_fields)}")
    print(f"  With 20-question limit:  {len(asked_fields_20):2d} ({len(asked_fields_20)/len(all_condition_fields)*100:.1f}%)")
    print(f"  With 40-question limit:  {len(asked_fields_40):2d} ({len(asked_fields_40)/len(all_condition_fields)*100:.1f}%)")
    print(f"  Improvement:             +{len(asked_fields_40)-len(asked_fields_20):2d} fields (+{(len(asked_fields_40)-len(asked_fields_20))/len(all_condition_fields)*100:.1f}%)")
    
    # NEW FIELDS
    print(f"\n" + "-" * 120)
    print(f"NEW FIELDS ASKED WITH 40-QUESTION LIMIT")
    print("-" * 120)
    
    if new_fields:
        print(f"\nNew fields that would be asked:\n")
        
        # Get impact info for new fields
        new_field_impacts = []
        for scheme, _ in possible_schemes:
            for cond in scheme.conditions:
                if cond.field in new_fields:
                    new_field_impacts.append(cond.field)
        
        new_field_set = set(new_field_impacts)
        new_field_dict = defaultdict(int)
        for field in new_field_set:
            for scheme, _ in possible_schemes:
                for cond in scheme.conditions:
                    if cond.field == field:
                        new_field_dict[field] += 1
        
        ranked_new = sorted(new_field_dict.items(), key=lambda x: -x[1])
        
        for rank, (field, count) in enumerate(ranked_new, 1):
            print(f"  {rank}. {field:<25} would affect {count:2d} schemes")
        
        total_new_conditions = sum(count for _, count in ranked_new)
        print(f"\n  Total conditions covered by new fields: {total_new_conditions}")
    else:
        print("\n  No new fields would be asked with 40-question limit")
        print("  (All condition fields already covered with 20 questions)")
    
    # ========================================
    # SCHEME IMPACT
    # ========================================
    print(f"\n" + "=" * 120)
    print(f"SCHEME-LEVEL IMPACT")
    print("=" * 120)
    
    # For each scheme, count how many questions address it
    schemes_covered_20 = defaultdict(int)
    schemes_covered_40 = defaultdict(int)
    
    for scheme, _ in possible_schemes:
        for cond in scheme.conditions:
            if cond.field in asked_fields_20:
                schemes_covered_20[scheme.id] += 1
            if cond.field in asked_fields_40:
                schemes_covered_40[scheme.id] += 1
    
    # Count schemes by coverage level
    print(f"\nScheme coverage breakdown (20 questions):")
    coverage_20 = defaultdict(int)
    for scheme_id, count in schemes_covered_20.items():
        if count == 0:
            coverage_20['none'] += 1
        elif count == 1:
            coverage_20['1_question'] += 1
        elif count <= 3:
            coverage_20['2-3_questions'] += 1
        elif count <= 5:
            coverage_20['4-5_questions'] += 1
        else:
            coverage_20['5+_questions'] += 1
    
    for category in ['none', '1_question', '2-3_questions', '4-5_questions', '5+_questions']:
        count = coverage_20.get(category, 0)
        print(f"  {category:<20} {count:3d} schemes")
    
    print(f"\nScheme coverage breakdown (40 questions):")
    coverage_40 = defaultdict(int)
    for scheme_id, count in schemes_covered_40.items():
        if count == 0:
            coverage_40['none'] += 1
        elif count == 1:
            coverage_40['1_question'] += 1
        elif count <= 3:
            coverage_40['2-3_questions'] += 1
        elif count <= 5:
            coverage_40['4-5_questions'] += 1
        else:
            coverage_40['5+_questions'] += 1
    
    for category in ['none', '1_question', '2-3_questions', '4-5_questions', '5+_questions']:
        count = coverage_40.get(category, 0)
        print(f"  {category:<20} {count:3d} schemes")
    
    # ========================================
    # UNQUESTIONED ANALYSIS
    # ========================================
    print(f"\n" + "=" * 120)
    print(f"REMAINING UNQUESTIONED FIELDS (WITH 40-QUESTION LIMIT)")
    print("=" * 120)
    
    unquestioned_40 = all_condition_fields - asked_fields_40
    
    print(f"\nFields still NOT being asked: {len(unquestioned_40)}")
    
    if unquestioned_40:
        print(f"\nRemaining unquestioned fields:")
        
        unquestioned_dict = defaultdict(int)
        for field in unquestioned_40:
            for scheme, _ in possible_schemes:
                for cond in scheme.conditions:
                    if cond.field == field:
                        unquestioned_dict[field] += 1
        
        ranked = sorted(unquestioned_dict.items(), key=lambda x: -x[1])
        for field, count in ranked:
            print(f"  • {field:<25} affects {count:2d} schemes")
    
    # ========================================
    # SUMMARY
    # ========================================
    print(f"\n" + "=" * 120)
    print(f"EXECUTIVE SUMMARY")
    print("=" * 120)
    
    print(f"""
CURRENT STATE (20 questions):
  • Generates {len(questions_20)} questions
  • Covers {len(asked_fields_20)} fields
  • Covers {len(asked_fields_20)/len(all_condition_fields)*100:.1f}% of all condition fields

WITH 40 QUESTIONS:
  • Generates {len(questions_40)} questions
  • Covers {len(asked_fields_40)} fields
  • Covers {len(asked_fields_40)/len(all_condition_fields)*100:.1f}% of all condition fields
  
IMPROVEMENT:
  • +{len(questions_40) - len(questions_20)} additional questions
  • +{len(asked_fields_40) - len(asked_fields_20)} additional fields
  • +{(len(asked_fields_40) - len(asked_fields_20))/len(all_condition_fields)*100:.1f}% coverage improvement

USER EXPERIENCE:
  • 20 questions: Quick, focused, high-priority only
  • 40 questions: More comprehensive, covers edge cases, may feel longer

RECOMMENDATION:
  40 questions is reasonable if you can accommodate in UI/UX
  Covers {len(asked_fields_40)}/{len(all_condition_fields)} fields ({len(asked_fields_40)/len(all_condition_fields)*100:.1f}%)
  Only {len(unquestioned_40)} fields remain unquestioned after this
""")

print("=" * 120)
