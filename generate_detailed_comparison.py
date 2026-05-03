import sys
sys.path.insert(0, '.')
from app import app, User, Scheme
from app.engine.eligibility import EligibilityEngine, get_canonical_field, get_profile_value, evaluate_single
from app.engine.context import ContextualReasoner
from app.engine.questions import QuestionEngine, is_user_answerable
import time

def simulate_answer(field, profile):
    if field in ["citizenship"]:
        return True
    if field in ["bank_account"]:
        return True
    if field in ["consent"]:
        return True
    if field in profile and profile[field] is not None:
        return profile[field]
    return True

def resolve_with_iterations(engine, qengine, scheme, base_profile, max_iter=2):
    profile = dict(base_profile)
    for _ in range(max_iter):
        eo = engine.evaluate(scheme, profile)
        hard_missing = [get_canonical_field(f) for f in eo.missing_fields if is_user_answerable(f)]
        if not hard_missing:
            return eo
        for q in eo.missing_fields[:3]:
            canonical = get_canonical_field(q)
            if canonical not in profile:
                profile[canonical] = simulate_answer(canonical, profile)
    return eo

def run_full_audit():
    output = []
    
    with app.app_context():
        # Get original user
        user = User.query.filter_by(email='shreyas6504@gmail.com').first()
        profile = user.get_profile_dict()
        
        # User details header
        output.append("=" * 100)
        output.append("USER PROFILE DETAILS")
        output.append("=" * 100)
        for key, value in sorted(profile.items()):
            if value is not None:
                output.append(f"{key}: {value}")
        
        output.append("")
        output.append("=" * 100)
        output.append("SCHEME ELIGIBILITY EVALUATION - DETAILED CONDITIONS")
        output.append("=" * 100)
        
        # Initialize
        engine = EligibilityEngine()
        qengine = QuestionEngine()
        ctx = ContextualReasoner()
        
        all_schemes = Scheme.query.filter_by(is_active=True).all()
        print(f"Total schemes: {len(all_schemes)}")
        
        total_schemes = 0
        false_eligible_count = 0
        
        for scheme in all_schemes:
            total_schemes += 1
            
            # Resolve with iterations
            eo = resolve_with_iterations(engine, qengine, scheme, profile, max_iter=2)
            
            output.append(f"\n{'='*100}")
            output.append(f"SCHEME: {scheme.name} (ID: {scheme.id})")
            output.append(f"RESULT: {eo.result.upper()} | CONFIDENCE: {eo.confidence}")
            output.append(f"MISSING FIELDS: {eo.missing_fields}")
            
            output.append(f"\n{'FIELD':40} | {'TYPE':6} | {'COND':5} | {'OP':10} | {'EXPECTED':25} | {'ACTUAL':20} | {'STATUS'}")
            output.append("-" * 130)
            
            rows = []
            for cond in scheme.conditions:
                field = cond.field
                operator = cond.operator
                expected = cond.value
                
                actual = get_profile_value(field, profile)
                field_type = "USER" if is_user_answerable(field) else "SYSTEM"
                
                cond_type = getattr(cond, 'condition_type', None)
                if not cond_type:
                    cond_type = "HARD" if getattr(cond, 'is_hard', False) else "SOFT"
                cond_type = cond_type.upper()
                
                if actual is None:
                    status = "MISSING"
                else:
                    raw = evaluate_single(cond, profile)
                    if raw.status == 'pass':
                        status = "PASS"
                    elif raw.status == 'fail':
                        status = "FAIL"
                    else:
                        status = "MISSING"
                
                rows.append({
                    "field": field,
                    "field_type": field_type,
                    "condition_type": cond_type,
                    "result": status,
                    "expected": expected,
                    "actual": actual
                })
                
                output.append(f"{field[:40]:40} | {field_type:6} | {cond_type:5} | {operator:10} | {str(expected)[:25]:25} | {str(actual)[:20]:20} | {status}")
                
                if actual is None and field_type == "USER":
                    output.append(f"  ⚠️ USER FIELD NOT FOUND IN PROFILE: {field}")
            
            hard_user_pass = sum(1 for r in rows if r["field_type"] == "USER" and r["condition_type"] == "HARD" and r["result"] == "PASS")
            hard_user_fail = sum(1 for r in rows if r["field_type"] == "USER" and r["condition_type"] == "HARD" and r["result"] == "FAIL")
            soft_user_fail = sum(1 for r in rows if r["field_type"] == "USER" and r["condition_type"] == "SOFT" and r["result"] == "FAIL")
            system_missing = sum(1 for r in rows if r["field_type"] == "SYSTEM" and r["result"] == "MISSING")
            
            false_eligible = eo.result == "eligible" and hard_user_fail > 0
            if false_eligible:
                false_eligible_count += 1
            
            output.append(f"\nSUMMARY:")
            output.append(f"  HARD USER PASS: {hard_user_pass}")
            output.append(f"  HARD USER FAIL: {hard_user_fail}")
            output.append(f"  SOFT USER FAIL: {soft_user_fail}")
            output.append(f"  SYSTEM MISSING: {system_missing}")
            output.append(f"  MISSING FIELDS (after resolution): {len(eo.missing_fields)}")
            
            if false_eligible:
                hard_fail_fields = [r["field"] for r in rows if r["field_type"] == "USER" and r["condition_type"] == "HARD" and r["result"] == "FAIL"]
                output.append(f"\n🚨 FALSE ELIGIBLE DETECTED - HARD USER FAILS: {hard_fail_fields}")
            
            if total_schemes % 100 == 0:
                print(f"Processed {total_schemes} schemes...")
        
        # Final statistics
        output.append(f"\n{'='*100}")
        output.append(f"FINAL STATISTICS")
        output.append(f"{'='*100}")
        output.append(f"Total Schemes Evaluated: {total_schemes}")
        output.append(f"False Eligible (HARD USER FAIL): {false_eligible_count}")
        
        # Calculate final results
        print("\nCalculating final results...")
        
        # Re-run to get counts
        eligible = 0
        possible = 0
        ineligible = 0
        
        for scheme in all_schemes:
            eo = resolve_with_iterations(engine, qengine, scheme, profile, max_iter=2)
            if eo.result == "eligible":
                eligible += 1
            elif eo.result == "possible":
                possible += 1
            else:
                ineligible += 1
        
        output.append(f"\nFINAL COUNTS:")
        output.append(f"  ELIGIBLE: {eligible}")
        output.append(f"  POSSIBLE: {possible}")
        output.append(f"  INELIGIBLE: {ineligible}")
        output.append(f"  TOTAL: {eligible + possible + ineligible}")
        
        # Save to file
        output_file = "full_condition_comparison_original_user_detailed.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output))
        
        print(f"\nResults saved to: {output_file}")
        print(f"Total lines: {len(output)}")
        print(f"\nFINAL COUNTS: ELIGIBLE={eligible}, POSSIBLE={possible}, INELIGIBLE={ineligible}")

if __name__ == "__main__":
    run_full_audit()