import sys
sys.path.insert(0, '.')
from app import app, Scheme
from app.engine.eligibility import EligibilityEngine, get_canonical_field, get_profile_value, evaluate_single, FIELD_MAP
from app.engine.context import ContextualReasoner
from app.engine.questions import QuestionEngine, is_user_answerable

# Controlled simulation function
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

# Resolution orchestrator
def resolve_scheme_fully(engine, qengine, scheme, base_profile, max_iter=5):
    profile = dict(base_profile)
    for _ in range(max_iter):
        eo = engine.evaluate(scheme, profile)
        hard_missing = [
            get_canonical_field(f)
            for f in eo.missing_fields
            if is_user_answerable(f)
        ]
        if not hard_missing:
            return eo
        questions = qengine.select_questions([(scheme, eo)], profile)
        before = set(profile.keys())
        for q in questions:
            canonical = get_canonical_field(q.field)
            if canonical in profile:
                continue
            profile[canonical] = simulate_answer(canonical, profile)
        after = set(profile.keys())
        if before == after:
            break
    return eo

# Test profile
test_profile = {
    'age': 21,
    'state': 'Karnataka',
    'gender': 'male',
    'category': 'obc',
    'occupation': 'student',
    'annual_income': 200000,
    'education_level': 'graduation (ug)',
    'residence_area_type': 'rural',
    'has_bank_account': True,
    'is_student': True,
    'is_bpl': True,
    'is_disabled': False,
    'is_senior_citizen': False,
}

def run_full_audit():
    output = []
    
    with app.app_context():
        engine = EligibilityEngine()
        qengine = QuestionEngine()
        ctx = ContextualReasoner()
        
        all_schemes = Scheme.query.filter_by(is_active=True).all()
        
        total_schemes = 0
        false_eligible_count = 0
        false_ineligible_count = 0
        
        for scheme in all_schemes:
            total_schemes += 1
            
            # Use resolution loop
            eo = resolve_scheme_fully(engine, qengine, scheme, test_profile, max_iter=5)
            
            output.append(f"\n{'='*80}")
            output.append(f"SCHEME: {scheme.name} (ID: {scheme.id})")
            output.append(f"RESULT: {eo.result.upper()} | CONFIDENCE: {eo.confidence}")
            
            output.append(f"\n{'FIELD':35} | {'TYPE':6} | {'COND':5} | {'OP':8} | {'EXPECTED':20} | {'ACTUAL':15} | {'RESULT'}")
            output.append("-" * 120)
            
            rows = []
            for cond in scheme.conditions:
                field = cond.field
                operator = cond.operator
                expected = cond.value
                
                actual = get_profile_value(field, test_profile)
                field_type = "USER" if is_user_answerable(field) else "SYSTEM"
                
                cond_type = getattr(cond, 'condition_type', None)
                if not cond_type:
                    cond_type = "HARD" if getattr(cond, 'is_hard', False) else "SOFT"
                cond_type = cond_type.upper()
                
                if actual is None:
                    status = "MISSING"
                else:
                    raw = evaluate_single(cond, test_profile)
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
                
                output.append(f"{field[:35]:35} | {field_type:6} | {cond_type:5} | {operator:8} | {str(expected)[:20]:20} | {str(actual)[:15]:15} | {status}")
                
                if actual is None and field_type == "USER":
                    output.append(f"  ⚠️ USER FIELD NOT FOUND IN PROFILE: {field}")
            
            hard_user_pass = sum(1 for r in rows if r["field_type"] == "USER" and r["condition_type"] == "HARD" and r["result"] == "PASS")
            hard_user_fail = sum(1 for r in rows if r["field_type"] == "USER" and r["condition_type"] == "HARD" and r["result"] == "FAIL")
            soft_user_fail = sum(1 for r in rows if r["field_type"] == "USER" and r["condition_type"] == "SOFT" and r["result"] == "FAIL")
            system_missing = sum(1 for r in rows if r["field_type"] == "SYSTEM" and r["result"] == "MISSING")
            
            false_eligible = eo.result == "eligible" and hard_user_fail > 0
            if false_eligible:
                false_eligible_count += 1
            
            hard_user_conditions = [r for r in rows if r["field_type"] == "USER" and r["condition_type"] == "HARD"]
            all_hard_pass = len(hard_user_conditions) > 0 and all(r["result"] == "PASS" for r in hard_user_conditions)
            false_ineligible = eo.result == "ineligible" and all_hard_pass
            if false_ineligible:
                false_ineligible_count += 1
            
            output.append(f"\nSUMMARY:")
            output.append(f"  HARD USER PASS: {hard_user_pass}")
            output.append(f"  HARD USER FAIL: {hard_user_fail}")
            output.append(f"  SOFT USER FAIL: {soft_user_fail}")
            output.append(f"  SYSTEM MISSING: {system_missing}")
            
            if false_eligible:
                hard_fail_fields = [r["field"] for r in rows if r["field_type"] == "USER" and r["condition_type"] == "HARD" and r["result"] == "FAIL"]
                output.append(f"\n🚨 FALSE ELIGIBLE DETECTED - HARD USER FAILS: {hard_fail_fields}")
            
            if false_ineligible:
                output.append(f"\n🚨 FALSE INELIGIBLE DETECTED - ALL HARD USER CONDITIONS PASS")
        
        output.append(f"\n{'='*80}")
        output.append(f"FINAL STATISTICS")
        output.append(f"{'='*80}")
        output.append(f"Total Schemes: {total_schemes}")
        output.append(f"False Eligible (HARD USER FAIL): {false_eligible_count}")
        output.append(f"False Ineligible (ALL HARD PASS): {false_ineligible_count}")
        
        # Save to file
        output_file = "full_condition_comparison_with_resolution.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output))
        
        print(f"Results saved to: {output_file}")
        print(f"Total lines: {len(output)}")

if __name__ == "__main__":
    run_full_audit()