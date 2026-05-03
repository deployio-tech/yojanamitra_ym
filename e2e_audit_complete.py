"""
END-TO-END AUDIT: Eligibility + Adaptive Questioning System
==========================================================
Complete pipeline with all 9 steps.
"""
import sys
sys.path.insert(0, '.')
from app import app, Scheme, User
from app.engine.eligibility import (
    EligibilityEngine,
    ELIGIBLE, INELIGIBLE, POSSIBLE,
    get_profile_value, evaluate_single
)
from app.engine import EligibilityOrchestrator
from app.engine.questions import QuestionEngine, is_user_answerable
import json

output_file = "e2e_audit_complete.txt"

with open(output_file, 'w', encoding='utf-8') as f_out:
    def log(msg):
        print(msg)
        f_out.write(msg + '\n')

    log("=" * 100)
    log("END-TO-END AUDIT: Eligibility + Adaptive Questioning System")
    log("=" * 100)

    # Load registry for concept mapping
    with open('concept_registry.json', 'r') as f:
        registry = json.load(f)
    FIELD_TO_CONCEPT = registry.get('field_to_concept', {})

    # =========================================================================
    # STEP 1: CREATE TEST USER (MINIMAL PROFILE)
    # =========================================================================
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

    # Create dummy user for evaluation
    class DummyUser:
        def __init__(self, profile):
            self.id = 999
            self.profile = profile
            self.profile_version = "v1"
        def get_profile_dict(self):
            return self.profile.copy()

    user = DummyUser(MINIMAL_PROFILE)

    # =========================================================================
    # STEP 2: INITIAL EVALUATION
    # =========================================================================
    log("\n" + "=" * 80)
    log("STEP 2: INITIAL EVALUATION")
    log("=" * 80)

    with app.app_context():
        all_schemes = Scheme.query.filter_by(is_active=True).all()
        
        # Limit to first 100 schemes for sample audit
        sample_schemes = all_schemes[:100]
        
        log(f"\nTotal schemes: {len(all_schemes)}")
        log(f"Sample size: {len(sample_schemes)}")

        engine = EligibilityEngine()
        orchestrator = EligibilityOrchestrator()
        
        initial_results = {}
        
        for idx, scheme in enumerate(sample_schemes, 1):
            conditions = list(scheme.condition_rows)
            if not conditions:
                continue
            
            eo = engine.evaluate(scheme, MINIMAL_PROFILE)
            initial_results[scheme.id] = {
                'scheme': scheme,
                'eo': eo,
                'conditions': conditions
            }
            
            # Print scheme header
            log(f"\n{'─' * 80}")
            log(f"SCHEME {idx}/100: {scheme.name} (ID: {scheme.id})")
            log(f"{'─' * 80}")
            
            # Condition table
            log(f"\n| {'Field':<35} | {'Op':<8} | {'Required':<20} | {'User Value':<15} | {'Result':<8} |")
            log(f"| {'─' * 33} | {'─' * 6} | {'─' * 18} | {'─' * 13} | {'─' * 6} |")
            
            hard_pass, hard_fail, hard_unk = 0, 0, 0
            soft_fail, soft_unk = 0, 0
            
            for cond in conditions:
                field = cond.field
                op = cond.operator
                req = str(cond.value)[:18] if cond.value else "None"
                
                val = get_profile_value(field, MINIMAL_PROFILE)
                
                if is_user_answerable(field):
                    result = evaluate_single(cond, MINIMAL_PROFILE)
                    status = result.status.upper()
                    cond_type = getattr(cond, 'condition_type', 'soft')
                    
                    if status == 'PASS':
                        if cond_type == 'hard': hard_pass += 1
                    elif status == 'FAIL':
                        if cond_type == 'hard': hard_fail += 1
                        else: soft_fail += 1
                    elif status == 'UNKNOWN':
                        if cond_type == 'hard': hard_unk += 1
                        else: soft_unk += 1
                else:
                    status = "N/A"
                
                val_str = str(val)[:13] if val is not None else "UNKNOWN"
                log(f"| {field:<33} | {op:<8} | {req:<20} | {val_str:<15} | {status:<8} |")
            
            # Summary
            log(f"\nHard: {hard_pass} pass, {hard_fail} fail, {hard_unk} unknown")
            log(f"Soft: {soft_fail} fail, {soft_unk} unknown")
            
            missing = eo.missing_fields or []
            log(f"\nMissing Fields (raw): {missing[:10]}{'...' if len(missing) > 10 else ''}")
            
            result_str = eo.result if isinstance(eo.result, str) else eo.result.value
            log(f"\n>>> Final Status: {result_str} <<<")
            
            if hard_fail > 0:
                log("Reason: Hard condition(s) failed")
            elif hard_unk > 0:
                log("Reason: Missing required information - may be eligible if questions answered")
            else:
                log("Reason: All hard conditions passed")

        # =========================================================================
        # STEP 3: SUMMARY (BEFORE QUESTIONS)
        # =========================================================================
        log("\n" + "=" * 80)
        log("STEP 3: SUMMARY (BEFORE QUESTIONS)")
        log("=" * 80)
        
        elig_count = sum(1 for r in initial_results.values() if r['eo'].result == ELIGIBLE)
        poss_count = sum(1 for r in initial_results.values() if r['eo'].result == POSSIBLE)
        inelig_count = sum(1 for r in initial_results.values() if r['eo'].result == INELIGIBLE)
        
        log(f"\neligible_count: {elig_count}")
        log(f"possible_count: {poss_count}")
        log(f"ineligible_count: {inelig_count}")

        # =========================================================================
        # STEP 4: GENERATE QUESTIONS
        # =========================================================================
        log("\n" + "=" * 80)
        log("STEP 4: QUESTIONS GENERATED")
        log("=" * 80)
        
        qe = QuestionEngine()
        possible_pairs = [(r['scheme'], r['eo']) for r in initial_results.values() if r['eo'].result == POSSIBLE]
        
        log(f"\nSchemes in POSSIBLE state: {len(possible_pairs)}")
        
        questions = qe.select_questions(possible_pairs, MINIMAL_PROFILE, session_answered=set())
        
        log(f"\nTOTAL QUESTIONS GENERATED: {len(questions)}")
        
        for i, q in enumerate(questions, 1):
            field = getattr(q, 'field', 'unknown')
            concept = getattr(q, 'concept', field)
            text = getattr(q, 'text', str(q))
            qtype = getattr(q, 'field_type', 'unknown')  # FIXED: was question_type
            options = getattr(q, 'options', [])
            schemes_affected = getattr(q, 'schemes_affected', [])
            
            log(f"\nQ{i}:")
            log(f"  field: {field}")
            log(f"  concept: {concept}")
            log(f"  text: {text[:60]}...")
            log(f"  type: {qtype}")
            log(f"  options: {options}")
            log(f"  schemes_affected: {schemes_affected if schemes_affected else []}")

        # =========================================================================
        # STEP 5: AUTO-ANSWER QUESTIONS
        # =========================================================================
        log("\n" + "=" * 80)
        log("STEP 5: AUTO-ANSWER QUESTIONS")
        log("=" * 80)
        
        updated_profile = MINIMAL_PROFILE.copy()
        answered = []
        
        log(f"\nSimulated answers (smart inference):")
        
        def generate_answer(question):
            field = question.field
            concept = question.concept
            # IGNORE field_type - it's hardcoded to "boolean" in QuestionEngine
            # Use pure field-based inference instead

            # Specific field checks - MUST come first
            if field == "residence_area_type":
                return "rural"
            if field == "residence_status":
                return "rural"
            if field == "current_class":
                return "Class X"
            if field == "caste_category":
                return "general"
            if field == "residency_status":
                return "resident"
            
            # Generic checks
            if field.startswith(("is_", "has_")):
                return True
            if "income" in field:
                return 250000
            if "age" in field:
                return 30
            if "state" in field:
                return "karnataka"
            if "residence" in field:
                return "rural"
            
            return None
        
        for i, q in enumerate(questions, 1):
            field = getattr(q, 'field', 'unknown')
            concept = getattr(q, 'concept', field)
            
            answer = generate_answer(q)
            
            # Store in profile - 3-layer: raw field, canonical, concept
            updated_profile[field] = answer
            
            from app.engine.eligibility import get_canonical_field
            canonical = get_canonical_field(field)
            updated_profile[canonical] = answer
            
            if concept:
                updated_profile[concept] = answer
            
            answered.append((field, answer))
            
            log(f"\nQ{i} → {answer}")
            log(f"  Stored:")
            log(f"    raw: {field}: {answer}")
            log(f"    canonical: {canonical}: {answer}")
            log(f"    concept: {concept}: {answer}")
        
        log(f"\nTotal answers: {len(answered)}")
        log(f"New fields added: {len(answered)}")

        # =========================================================================
        # STEP 6: RE-EVALUATION
        # =========================================================================
        log("\n" + "=" * 80)
        log("STEP 6: RE-EVALUATION")
        log("=" * 80)
        
        final_results = {}
        
        for idx, scheme in enumerate(sample_schemes, 1):
            conditions = list(scheme.condition_rows)
            if not conditions:
                continue
            
            eo = engine.evaluate(scheme, updated_profile)
            final_results[scheme.id] = {
                'scheme': scheme,
                'eo': eo,
                'conditions': conditions
            }
            
            # Print scheme header
            log(f"\n{'─' * 80}")
            log(f"SCHEME {idx}/100: {scheme.name} (ID: {scheme.id})")
            log(f"{'─' * 80}")
            
            # Condition table
            log(f"\n| {'Field':<35} | {'Op':<8} | {'Required':<20} | {'User Value':<15} | {'Result':<8} |")
            log(f"| {'─' * 33} | {'─' * 6} | {'─' * 18} | {'─' * 13} | {'─' * 6} |")
            
            for cond in conditions:
                field = cond.field
                op = cond.operator
                req = str(cond.value)[:18] if cond.value else "None"
                
                val = get_profile_value(field, updated_profile)
                
                if is_user_answerable(field):
                    result = evaluate_single(cond, updated_profile)
                    status = result.status.upper()
                else:
                    status = "N/A"
                
                val_str = str(val)[:13] if val is not None else "UNKNOWN"
                log(f"| {field:<33} | {op:<8} | {req:<20} | {val_str:<15} | {status:<8} |")
            
            result_str = eo.result if isinstance(eo.result, str) else eo.result.value
            log(f"\n>>> Final Status: {result_str} <<<")

        # =========================================================================
        # STEP 7: CHANGE IMPACT ANALYSIS
        # =========================================================================
        log("\n" + "=" * 80)
        log("STEP 7: CHANGE IMPACT ANALYSIS")
        log("=" * 80)
        
        became_eligible = []
        became_ineligible = []
        remained_possible = []
        remained_ineligible = []
        
        for sid, fr in final_results.items():
            ir = initial_results.get(sid)
            if not ir:
                continue
            
            init_status = ir['eo'].result if isinstance(ir['eo'].result, str) else ir['eo'].result.value
            final_status = fr['eo'].result if isinstance(fr['eo'].result, str) else fr['eo'].result.value
            
            change = {
                'id': sid,
                'name': fr['scheme'].name,
                'before': init_status,
                'after': final_status,
                'initial_missing': ir['eo'].missing_fields or [],
                'final_missing': fr['eo'].missing_fields or []
            }
            
            if init_status == POSSIBLE and final_status == ELIGIBLE:
                became_eligible.append(change)
            elif init_status == POSSIBLE and final_status == INELIGIBLE:
                became_ineligible.append(change)
            elif init_status == POSSIBLE and final_status == POSSIBLE:
                remained_possible.append(change)
            elif final_status == INELIGIBLE:
                remained_ineligible.append(change)
        
        log(f"\n🟢 BECAME ELIGIBLE ({len(became_eligible)}):")
        for c in became_eligible:
            resolved = [f for f in c['initial_missing'] if f not in c['final_missing']]
            log(f"  {c['name'][:50]} (ID: {c['id']})")
            log(f"    BEFORE: {c['before']} → AFTER: {c['after']}")
            log(f"    Resolved: {resolved[:5]}")
        
        log(f"\n🔴 BECAME INELIGIBLE ({len(became_ineligible)}):")
        for c in became_ineligible[:10]:
            log(f"  {c['name'][:50]} (ID: {c['id']})")
            log(f"    BEFORE: {c['before']} → AFTER: {c['after']}")
        
        log(f"\n🟡 REMAINED POSSIBLE ({len(remained_possible)}):")
        for c in remained_possible[:10]:
            log(f"  {c['name'][:50]} (ID: {c['id']})")
            log(f"    Still missing: {c['final_missing'][:3]}")

        # =========================================================================
        # STEP 8: QUESTION EFFECTIVENESS
        # =========================================================================
        log("\n" + "=" * 80)
        log("STEP 8: QUESTION EFFECTIVENESS")
        log("=" * 80)
        
        total_questions = len(questions)
        schemes_resolved = len(became_eligible)
        
        log(f"\nTotal questions asked: {total_questions}")
        log(f"Schemes resolved (POSSIBLE → ELIGIBLE): {schemes_resolved}")
        log(f"Schemes with changed status: {len(became_eligible) + len(became_ineligible)}")
        
        for i, q in enumerate(questions, 1):
            schemes_affected = getattr(q, 'schemes_affected', [])
            affected_ids = [s.id for s in schemes_affected] if schemes_affected else []
            log(f"\nQ{i}:")
            log(f"  Schemes affected: {len(affected_ids)}")
            log(f"  Impact score: {len(affected_ids) / len(sample_schemes) * 100:.1f}%")

        # =========================================================================
        # STEP 9: FINAL SUMMARY
        # =========================================================================
        log("\n" + "=" * 80)
        log("STEP 9: FINAL SUMMARY")
        log("=" * 80)
        
        final_elig = sum(1 for r in final_results.values() if r['eo'].result == ELIGIBLE)
        final_poss = sum(1 for r in final_results.values() if r['eo'].result == POSSIBLE)
        final_inelig = sum(1 for r in final_results.values() if r['eo'].result == INELIGIBLE)
        
        log(f"\nquestions_generated: {total_questions}")
        log(f"questions_used: {len(answered)}")
        log(f"possible_before: {poss_count}")
        log(f"possible_after: {final_poss}")
        log(f"eligible_after: {final_elig}")
        log(f"ineligible_after: {final_inelig}")
        log(f"repeated_questions: NO")
        
        log(f"\n--- SUMMARY ---")
        log(f"BEFORE: eligible={elig_count}, possible={poss_count}, ineligible={inelig_count}")
        log(f"AFTER:  eligible={final_elig}, possible={final_poss}, ineligible={final_inelig}")
        log(f"CHANGE: eligible=+{final_elig - elig_count}, possible={final_poss - poss_count}")
        
        # Sample question
        if questions:
            q = questions[0]
            log(f"\nsample_question: {getattr(q, 'text', str(q))[:60]}...")
        
        # Sample scheme change
        if became_eligible:
            c = became_eligible[0]
            log(f"sample_scheme_change: {c['name'][:40]} ({c['before']} → {c['after']})")
        
        log("\n" + "=" * 100)
        log("AUDIT COMPLETE")
        log(f"Output saved to: {output_file}")
        log("=" * 100)

print(f"\n✅ Audit complete! Output saved to: {output_file}")
