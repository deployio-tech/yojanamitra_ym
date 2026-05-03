"""
UNQUESTIONED FIELDS IMPACT ANALYSIS
====================================

Detailed breakdown of:
1. Which fields are NOT being asked about
2. How many conditions rely on each unquestioned field
3. Which schemes are affected by unquestioned fields
4. Total impact across all unquestioned fields
"""

import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Scheme
from app.engine.eligibility import EligibilityEngine
from app.engine.questions import QuestionEngine

print("\n" + "=" * 120)
print("UNQUESTIONED FIELDS - DETAILED IMPACT ANALYSIS")
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
    
    # Generate questions
    qengine = QuestionEngine()
    questions = qengine.select_questions(possible_schemes, minimal_profile)
    
    asked_fields = {q.field for q in questions}
    
    print(f"[SETUP] Generated {len(questions)} questions targeting {len(asked_fields)} fields")
    
    # Get ALL condition fields from POSSIBLE schemes
    all_condition_fields = defaultdict(lambda: {'conditions': [], 'schemes': set()})
    
    for scheme, result in possible_schemes:
        for cond in scheme.conditions:
            all_condition_fields[cond.field]['conditions'].append({
                'scheme_id': scheme.id,
                'scheme_name': scheme.name,
                'field': cond.field,
                'operator': cond.operator,
                'value': cond.value,
                'type': cond.condition_type
            })
            all_condition_fields[cond.field]['schemes'].add(scheme.id)
    
    # Identify unquestioned fields
    unquestioned_fields = [f for f in all_condition_fields.keys() if f not in asked_fields]
    
    print(f"\n" + "=" * 120)
    print(f"UNQUESTIONED FIELDS ANALYSIS")
    print("=" * 120)
    
    print(f"\nTotal condition fields in POSSIBLE schemes: {len(all_condition_fields)}")
    print(f"Fields being ASKED about: {len(asked_fields)}")
    print(f"Fields NOT being asked about: {len(unquestioned_fields)}")
    print(f"Coverage: {len(asked_fields)}/{len(all_condition_fields)} ({len(asked_fields)/len(all_condition_fields)*100:.1f}%)")
    print(f"Unasked coverage: {len(unquestioned_fields)}/{len(all_condition_fields)} ({len(unquestioned_fields)/len(all_condition_fields)*100:.1f}%)")
    
    # Detailed breakdown of unquestioned fields
    print(f"\n" + "-" * 120)
    print(f"UNQUESTIONED FIELDS - DETAILED BREAKDOWN")
    print("-" * 120)
    
    total_conditions_unquestioned = 0
    total_schemes_affected = 0
    
    for i, field in enumerate(sorted(unquestioned_fields), 1):
        field_data = all_condition_fields[field]
        conditions = field_data['conditions']
        schemes_affected = field_data['schemes']
        
        total_conditions_unquestioned += len(conditions)
        total_schemes_affected += len(schemes_affected)
        
        print(f"\n[{i}] FIELD: {field}")
        print(f"    Conditions using this field: {len(conditions)}")
        print(f"    Schemes affected: {len(schemes_affected)}")
        print(f"    Condition types: hard={sum(1 for c in conditions if c['type']=='hard')}, soft={sum(1 for c in conditions if c['type']=='soft')}")
        
        print(f"\n    Conditions breakdown:")
        for j, cond in enumerate(conditions[:5], 1):
            print(f"      [{j}] {cond['scheme_name']:50s} | {cond['operator']:8s} | {str(cond['value'])[:20]:20s} | {cond['type']}")
        
        if len(conditions) > 5:
            print(f"      ... and {len(conditions) - 5} more conditions")
        
        print(f"\n    Schemes affected by this unquestioned field:")
        for j, scheme_id in enumerate(sorted(schemes_affected)[:5], 1):
            scheme = Scheme.query.get(scheme_id)
            print(f"      [{j}] ID {scheme_id:4d} - {scheme.name[:70]}")
        
        if len(schemes_affected) > 5:
            print(f"      ... and {len(schemes_affected) - 5} more schemes")
    
    # Summary statistics
    print(f"\n" + "=" * 120)
    print(f"IMPACT SUMMARY")
    print("=" * 120)
    
    print(f"\nUNQUESTIONED FIELDS: {len(unquestioned_fields)}")
    print(f"  Total conditions affected: {total_conditions_unquestioned}")
    print(f"  Total schemes affected: {total_schemes_affected} (out of {len(possible_schemes)} POSSIBLE)")
    print(f"  Percentage of schemes affected: {total_schemes_affected/len(possible_schemes)*100:.1f}%")
    
    # Calculate average
    avg_schemes_per_unquestioned = total_schemes_affected / len(unquestioned_fields) if unquestioned_fields else 0
    avg_conditions_per_unquestioned = total_conditions_unquestioned / len(unquestioned_fields) if unquestioned_fields else 0
    
    print(f"\nPer unquestioned field (averages):")
    print(f"  Avg schemes affected: {avg_schemes_per_unquestioned:.1f}")
    print(f"  Avg conditions: {avg_conditions_per_unquestioned:.1f}")
    
    # Compare with questioned fields
    questioned_fields_data = {f: all_condition_fields[f] for f in asked_fields if f in all_condition_fields}
    
    total_conditions_questioned = sum(len(d['conditions']) for d in questioned_fields_data.values())
    total_schemes_questioned = len(set().union(*[d['schemes'] for d in questioned_fields_data.values()]))
    
    print(f"\nQUESTIONED FIELDS: {len(asked_fields)}")
    print(f"  Total conditions affected: {total_conditions_questioned}")
    print(f"  Total schemes affected: {total_schemes_questioned}")
    print(f"  Percentage of schemes affected: {total_schemes_questioned/len(possible_schemes)*100:.1f}%")
    
    # Ranking by impact
    print(f"\n" + "-" * 120)
    print(f"UNQUESTIONED FIELDS RANKED BY SCHEME IMPACT")
    print("-" * 120)
    
    ranked = [(f, len(all_condition_fields[f]['schemes']), len(all_condition_fields[f]['conditions'])) 
              for f in unquestioned_fields]
    ranked.sort(key=lambda x: -x[1])  # Sort by schemes affected
    
    print(f"\n{'Rank':<6} {'Field':<25} {'Schemes':<10} {'Conditions':<12} {'Impact'}")
    print("-" * 120)
    
    for rank, (field, schemes_affected, conditions) in enumerate(ranked, 1):
        impact = f"{schemes_affected/len(possible_schemes)*100:.1f}%"
        print(f"{rank:<6} {field:<25} {schemes_affected:<10} {conditions:<12} {impact}")
    
    # Critical fields analysis
    print(f"\n" + "=" * 120)
    print(f"CRITICAL ANALYSIS")
    print("=" * 120)
    
    critical_unquestioned = [f for f, schemes, _ in ranked if schemes > 10]
    moderate_unquestioned = [f for f, schemes, _ in ranked if 5 <= schemes <= 10]
    low_impact_unquestioned = [f for f, schemes, _ in ranked if schemes < 5]
    
    print(f"\nUnquestioned fields by impact category:")
    print(f"  HIGH IMPACT (>10 schemes):    {len(critical_unquestioned)} fields")
    for f in critical_unquestioned:
        schemes = len(all_condition_fields[f]['schemes'])
        print(f"    • {f:<25} affects {schemes:3d} schemes")
    
    print(f"\n  MODERATE IMPACT (5-10 schemes): {len(moderate_unquestioned)} fields")
    for f in moderate_unquestioned:
        schemes = len(all_condition_fields[f]['schemes'])
        print(f"    • {f:<25} affects {schemes:3d} schemes")
    
    print(f"\n  LOW IMPACT (<5 schemes):       {len(low_impact_unquestioned)} fields")
    for f in low_impact_unquestioned:
        schemes = len(all_condition_fields[f]['schemes'])
        print(f"    • {f:<25} affects {schemes:3d} schemes")
    
    # Why not asked
    print(f"\n" + "=" * 120)
    print(f"WHY THESE FIELDS ARE NOT BEING ASKED")
    print("=" * 120)
    
    print(f"""
Possible reasons for not asking these fields:

1. QUESTION LIMIT: System caps questions at ~20 to avoid user fatigue
   - 19 most-impactful questions are selected
   - These 6 fields have lower combined impact

2. REDUNDANCY: Similar information covered by other questions
   - is_urban and is_rural are often complements
   - residence and is_rural partially overlap

3. ALREADY IN PROFILE: Some fields may have been answered
   - age is in minimal profile (not missing)
   - state is in minimal profile (not missing)

4. LOWER PRIORITY: These fields affect fewer POSSIBLE schemes

5. QUESTION TEMPLATES: May not have user-friendly templates available


RECOMMENDATION FOR IMPROVEMENT:

If you want to ask about more fields:
1. Can increase question limit (currently ~20)
2. Can add templates for missing fields
3. Can ask in follow-up rounds (ask 3, user answers, ask 3 more)
4. Can prioritize based on user responses (conditional questioning)
""")

print("=" * 120)
