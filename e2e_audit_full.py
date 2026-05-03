"""
END-TO-END AUDIT: Eligibility + Adaptive Questioning System
==========================================================
Tests the full pipeline with minimal user profile.
"""
import sys
sys.path.insert(0, '.')
from app import app, Scheme
from app.engine.eligibility import (
    EligibilityEngine, get_canonical_field, get_profile_value,
    evaluate_single, UNKNOWN_C, FAIL_R, PASS_R, ELIGIBLE, INELIGIBLE, POSSIBLE
)
from app.engine.questions import is_user_answerable, QuestionEngine
import json
import datetime

output_file = f"e2e_audit_full_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

# Load field_to_concept for mapping display
with open('concept_registry.json', 'r') as f:
    registry = json.load(f)
FIELD_TO_CONCEPT = registry.get('field_to_concept', {})

# Open output file
f_out = open(output_file, 'w', encoding='utf-8')

def log(msg):
    print(msg)
    f_out.write(msg + '\n')

log("=" * 100)
log("END-TO-END AUDIT: Eligibility + Adaptive Questioning System")
log("=" * 100)

# STEP 1: Create minimal test user
log("\n" + "=" * 80)
log("STEP 1: CREATE TEST USER (MINIMAL PROFILE)")
log("=" * 80)

MINIMAL_PROFILE = {
    "age": 30,
    "gender": "male",
    "state": "karnataka"
}

log("\nProfile fields (MINIMAL - all others UNKNOWN):")
for k, v in MINIMAL_PROFILE.items():
    log(f"  {k}: {v}")
log("\nAll other fields are UNKNOWN (None)")

# STEP 2: INITIAL EVALUATION
log("\n" + "=" * 80)
log("STEP 2: INITIAL EVALUATION (FULL TRACE)")
log("=" * 80)

class DummyUser:
    def __init__(self, profile):
        self.id = 999
        self.profile = profile
        self.profile_version = "v1"
    def get_profile_dict(self):
        return self.profile.copy()

engine = EligibilityEngine()
qe = QuestionEngine()
user = DummyUser(MINIMAL_PROFILE)

with app.app_context():
    all_schemes = Scheme.query.filter_by(is_active=True).all()
    
    # Store results for later comparison
    initial_results = {}
    
    log(f"\nTotal schemes to evaluate: {len(all_schemes)}")
    
    for idx, scheme in enumerate(all_schemes):
        conditions = list(scheme.condition_rows)
        if not conditions:
            continue
        
        profile = user.get_profile_dict()
        eo = engine.evaluate(scheme, profile)
        
        initial_results[scheme.id] = {
            'scheme': scheme,
            'eo': eo,
            'profile': profile.copy()
        }
        
        # Print scheme header
        log(f"\n{'─' * 80}")
        log(f"SCHEME {idx+1}/{len(all_schemes)}: {scheme.name} (ID: {scheme.id})")
        log(f"{'─' * 80}")
        
        # Condition-by-condition table
        log(f"\n{'| Field':<35} {'| Operator':<12} {'| Required':<20} {'| User Value':<15} {'| Result':<8}")
        log(f"| {'─' * 33} | {'─' * 10} | {'─' * 18} | {'─' * 13} | {'─' * 6}")
        
        hard_fails = 0
        hard_unknowns = 0
        hard_passes = 0
        soft_fails = 0
        soft_unknowns = 0
        
        for cond in conditions:
            field = cond.field
            operator = cond.operator
            required = str(cond.value)[:18] if cond.value else "None"
            
            # Get user value using concept lookup
            user_val = get_profile_value(field, profile)
            
            # Evaluate
            if is_user_answerable(field):
                result = evaluate_single(cond, profile)
                status = result.status.upper()
            else:
                user_val_str = "N/A (system)"
                status = "N/A"
            
            if user_val is not None:
                user_val_str = str(user_val)[:13]
            else:
                user_val_str = "UNKNOWN"
            
            if is_user_answerable(field):
                log(f"| {field:<33} | {operator:<12} | {required:<20} | {user_val_str:<15} | {status:<8}")
                
                # Count by type
                cond_type = getattr(cond, 'condition_type', 'soft')
                if status == 'PASS':
                    if cond_type == 'hard':
                        hard_passes += 1
                elif status == 'FAIL':
                    if cond_type == 'hard':
                        hard_fails += 1
                    else:
                        soft_fails += 1
                elif status == 'UNKNOWN':
                    if cond_type == 'hard':
                        hard_unknowns += 1
                    else:
                        soft_unknowns += 1
            else:
                log(f"| {field:<33} | {operator:<12} | {required:<20} | {user_val_str:<15} | {status:<8}")
        
        # Missing fields
        missing = eo.missing_fields or []
        missing_concepts = list(set(FIELD_TO_CONCEPT.get(f, f) for f in missing if is_user_answerable(f)))
        
        log(f"\nHard: {hard_passes} pass, {hard_fails} fail, {hard_unknowns} unknown")
        log(f"Soft: {soft_fails} fail, {soft_unknowns} unknown")
        log(f"\nMissing Fields (raw): {missing[:10]}{'...' if len(missing) > 10 else ''}")
        log(f"Missing Concepts (mapped): {missing_concepts[:10]}{'...' if len(missing_concepts) > 10 else ''}")
        
        # Final status
        result_str = eo.result if isinstance(eo.result, str) else eo.result.value
        log(f"\n>>> Final Status: {result_str} <<<")
        
        # Reason summary
        if hard_fails > 0:
            log(f"Reason: Hard condition(s) failed - cannot meet eligibility requirements")
        elif hard_unknowns > 0:
            log(f"Reason: Missing required information - may be eligible if questions answered")
        else:
            log(f"Reason: All hard conditions passed")
    
    # STEP 3: QUESTIONS GENERATED
    log("\n" + "=" * 80)
    log("STEP 3: QUESTIONS GENERATED")
    log("=" * 80)
    
    # Get possible schemes
    possible_schemes = [(r['scheme'], r['eo']) for r in initial_results.values() if r['eo'].result == POSSIBLE]
    
    log(f"\nSchemes with POSSIBLE status: {len(possible_schemes)}")
    
    if possible_schemes:
        questions = qe.select_questions(possible_schemes, MINIMAL_PROFILE, session_answered=set())
        
        log(f"\nTotal questions generated: {len(questions)}")
        log(f"\n{'| #':<3} {'| Question':<60} {'| Field':<25} {'| Concept':<20} {'| Type':<12} {'| Schemes'}")
        log(f"| {'─' * 1} | {'─' * 58} | {'─' * 23} | {'─' * 18} | {'─' * 10} | {'─' * 8}")
        
        for i, q in enumerate(questions, 1):
            field = getattr(q, 'field', 'unknown')
            concept = FIELD_TO_CONCEPT.get(field, field)
            qtype = getattr(q, 'question_type', 'unknown')
            schemes_affected = getattr(q, 'schemes_affected', 0)
            
            text = getattr(q, 'text', str(q))[:58]
            log(f"| {i:<2} | {text:<58} | {field:<25} | {concept:<20} | {qtype:<12} | {schemes_affected}")
        
        questions_list = questions
    else:
        log("\nNo questions generated (no schemes in POSSIBLE state)")
        questions_list = []
    
    # STEP 4: AUTOMATED ANSWERS
    log("\n" + "=" * 80)
    log("STEP 4: AUTOMATED ANSWERS")
    log("=" * 80)
    
    log(f"\n{'| Concept':<20} {'| Question':<55} {'| Answer':<15}")
    log(f"| {'─' * 18} | {'─' * 53} | {'─' * 13}")
    
    updated_profile = MINIMAL_PROFILE.copy()
    answered_fields = []
    
    for q in questions_list:
        field = getattr(q, 'field', 'unknown')
        concept = FIELD_TO_CONCEPT.get(field, field)
        text = getattr(q, 'text', str(q))[:53]
        
        # Auto-answer based on type
        qtype = getattr(q, 'question_type', 'unknown')
        options = getattr(q, 'options', None)
        
        if qtype == 'boolean' or field.startswith('is_') or field.startswith('has_'):
            answer = "yes"
        elif options and len(options) > 0:
            answer = options[0]
        else:
            answer = "300000"  # Default for numeric
        
        log(f"| {concept:<20} | {text:<55} | {answer:<15}")
        
        answered_fields.append(field)
        updated_profile[field] = answer
    
    log(f"\nTotal answers provided: {len(answered_fields)}")
    
    # STEP 5: PROFILE UPDATE
    log("\n" + "=" * 80)
    log("STEP 5: PROFILE UPDATE")
    log("=" * 80)
    
    log("\nOriginal profile keys:" + str(sorted(MINIMAL_PROFILE.keys())))
    log("Updated profile keys:" + str(sorted(updated_profile.keys())))
    log("\nNew keys added:" + str([k for k in updated_profile if k not in MINIMAL_PROFILE]))
    
    log("\nUpdated profile:")
    for k, v in sorted(updated_profile.items()):
        marker = " (NEW)" if k not in MINIMAL_PROFILE else ""
        log(f"  {k}: {v}{marker}")
    
    # STEP 6: RE-EVALUATION
    log("\n" + "=" * 80)
    log("STEP 6: RE-EVALUATION (FULL TRACE)")
    log("=" * 80)
    
    user2 = DummyUser(updated_profile)
    final_results = {}
    
    for idx, scheme in enumerate(all_schemes):
        conditions = list(scheme.condition_rows)
        if not conditions:
            continue
        
        profile = user2.get_profile_dict()
        eo = engine.evaluate(scheme, profile)
        
        final_results[scheme.id] = {
            'scheme': scheme,
            'eo': eo,
            'profile': profile.copy()
        }
        
        # Print scheme header
        log(f"\n{'─' * 80}")
        log(f"SCHEME {idx+1}/{len(all_schemes)}: {scheme.name} (ID: {scheme.id})")
        log(f"{'─' * 80}")
        
        # Condition-by-condition table
        log(f"\n{'| Field':<35} {'| Operator':<12} {'| Required':<20} {'| User Value':<15} {'| Result':<8}")
        log(f"| {'─' * 33} | {'─' * 10} | {'─' * 18} | {'─' * 13} | {'─' * 6}")
        
        hard_fails = 0
        hard_unknowns = 0
        hard_passes = 0
        
        for cond in conditions:
            field = cond.field
            operator = cond.operator
            required = str(cond.value)[:18] if cond.value else "None"
            
            user_val = get_profile_value(field, profile)
            
            if is_user_answerable(field):
                result = evaluate_single(cond, profile)
                status = result.status.upper()
            else:
                user_val_str = "N/A (system)"
                status = "N/A"
            
            if user_val is not None:
                user_val_str = str(user_val)[:13]
            else:
                user_val_str = "UNKNOWN"
            
            if is_user_answerable(field):
                log(f"| {field:<33} | {operator:<12} | {required:<20} | {user_val_str:<15} | {status:<8}")
                
                cond_type = getattr(cond, 'condition_type', 'soft')
                if status == 'PASS' and cond_type == 'hard':
                    hard_passes += 1
                elif status == 'FAIL' and cond_type == 'hard':
                    hard_fails += 1
                elif status == 'UNKNOWN' and cond_type == 'hard':
                    hard_unknowns += 1
            else:
                log(f"| {field:<33} | {operator:<12} | {required:<20} | {user_val_str:<15} | {status:<8}")
        
        # Missing fields
        missing = eo.missing_fields or []
        
        log(f"\nHard: {hard_passes} pass, {hard_fails} fail, {hard_unknowns} unknown")
        
        result_str = eo.result if isinstance(eo.result, str) else eo.result.value
        log(f"\n>>> Final Status: {result_str} <<<")
    
    # STEP 7: CHANGE IMPACT ANALYSIS
    log("\n" + "=" * 80)
    log("STEP 7: CHANGE IMPACT ANALYSIS")
    log("=" * 80)
    
    became_eligible = []
    remained_ineligible = []
    still_possible = []
    
    for sid, fr in final_results.items():
        ir = initial_results.get(sid)
        if not ir:
            continue
        
        initial_status = ir['eo'].result if isinstance(ir['eo'].result, str) else ir['eo'].result.value
        final_status = fr['eo'].result if isinstance(fr['eo'].result, str) else fr['eo'].result.value
        
        if initial_status == POSSIBLE and final_status == ELIGIBLE:
            became_eligible.append({
                'id': sid,
                'name': fr['scheme'].name,
                'initial': initial_status,
                'final': final_status
            })
        elif final_status == INELIGIBLE:
            remained_ineligible.append({
                'id': sid,
                'name': fr['scheme'].name,
                'missing': fr['eo'].missing_fields[:5]
            })
        elif final_status == POSSIBLE:
            still_possible.append({
                'id': sid,
                'name': fr['scheme'].name,
                'missing': fr['eo'].missing_fields[:5]
            })
    
    log(f"\n🟢 BECAME ELIGIBLE ({len(became_eligible)} schemes):")
    if became_eligible:
        for s in became_eligible:
            log(f"   - {s['name'][:60]} (ID: {s['id']})")
    else:
        log("   None")
    
    log(f"\n🔴 REMAINED INELIGIBLE ({len(remained_ineligible)} schemes):")
    for s in remained_ineligible[:50]:
        log(f"   - {s['name'][:50]} (ID: {s['id']}) - Missing: {s['missing'][:3]}")
    if len(remained_ineligible) > 50:
        log(f"   ... and {len(remained_ineligible) - 50} more")
    
    log(f"\n🟡 STILL POSSIBLE ({len(still_possible)} schemes):")
    for s in still_possible[:20]:
        log(f"   - {s['name'][:50]} (ID: {s['id']}) - Missing: {s['missing'][:3]}")
    if len(still_possible) > 20:
        log(f"   ... and {len(still_possible) - 20} more")
    
    # STEP 8: QUESTION EFFECTIVENESS
    log("\n" + "=" * 80)
    log("STEP 8: QUESTION EFFECTIVENESS")
    log("=" * 80)
    
    total_questions_asked = len(questions_list)
    total_missing_resolved = sum(1 for f in answered_fields if f in updated_profile)
    initial_missing = sum(len(r['eo'].missing_fields or []) for r in initial_results.values() if r['eo'].result == POSSIBLE)
    final_missing = sum(len(r['eo'].missing_fields or []) for r in final_results.values() if r['eo'].result == POSSIBLE)
    
    reduction_pct = ((initial_missing - final_missing) / initial_missing * 100) if initial_missing > 0 else 0
    
    log(f"\nTotal questions asked: {total_questions_asked}")
    log(f"Total missing fields resolved: {total_missing_resolved}")
    log(f"Initial missing fields (POSSIBLE schemes): {initial_missing}")
    log(f"Final missing fields (POSSIBLE schemes): {final_missing}")
    log(f"Reduction in missing fields: {reduction_pct:.1f}%")
    log(f"Repeated questions: NONE ✓" if len(answered_fields) == len(set(answered_fields)) else "WARNING: Duplicate questions detected")
    
    # STEP 9: FINAL SUMMARY
    log("\n" + "=" * 80)
    log("STEP 9: FINAL SUMMARY")
    log("=" * 80)
    
    eligible_count = sum(1 for r in final_results.values() if r['eo'].result == ELIGIBLE)
    possible_count = sum(1 for r in final_results.values() if r['eo'].result == POSSIBLE)
    ineligible_count = sum(1 for r in final_results.values() if r['eo'].result == INELIGIBLE)
    
    initial_eligible = sum(1 for r in initial_results.values() if r['eo'].result == ELIGIBLE)
    initial_possible = sum(1 for r in initial_results.values() if r['eo'].result == POSSIBLE)
    initial_ineligible = sum(1 for r in initial_results.values() if r['eo'].result == INELIGIBLE)
    
    log(f"\nBEFORE ANSWERS:")
    log(f"  ✓ Eligible: {initial_eligible}")
    log(f"  ? Possible: {initial_possible}")
    log(f"  ✗ Ineligible: {initial_ineligible}")
    
    log(f"\nAFTER ANSWERS:")
    log(f"  ✓ Eligible: {eligible_count} (was {initial_eligible})")
    log(f"  ? Possible: {possible_count} (was {initial_possible})")
    log(f"  ✗ Ineligible: {ineligible_count} (was {initial_ineligible})")
    
    log(f"\nQuestion Metrics:")
    log(f"  Questions generated: {total_questions_asked}")
    log(f"  Questions answered: {len(answered_fields)}")
    log(f"  Eligibility improvement: {'YES' if became_eligible else 'NO'}")
    
    log("\n" + "=" * 100)
    log("AUDIT COMPLETE")
    log(f"Output saved to: {output_file}")
    log("=" * 100)

f_out.close()
print(f"\nAudit complete! Output saved to: {output_file}")
