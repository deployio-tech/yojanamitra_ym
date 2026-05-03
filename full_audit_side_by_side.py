"""
FULL SIDE-BY-SIDE CONDITION VS USER DATA AUDIT (NO FILTERING)
User: spoorthi k gowda (ID: 8)
"""
import sys
sys.path.insert(0, '.')
from app import app, User, Scheme
from app.engine.eligibility import (
    EligibilityEngine, get_canonical_field, get_profile_value, 
    evaluate_single, normalize_condition_value
)
from app.engine.questions import is_user_answerable
import datetime

output_file = f"spoorthi_k_gowda_audit_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

print("=" * 120)
print("FULL SIDE-BY-SIDE CONDITION VS USER DATA AUDIT (NO FILTERING)")
print("User: spoorthi k gowda (ID: 8)")
print("=" * 120)

# Open output file
with open(output_file, 'w', encoding='utf-8') as f_out:
    f_out.write("=" * 120 + "\n")
    f_out.write("FULL SIDE-BY-SIDE CONDITION VS USER DATA AUDIT (NO FILTERING)\n")
    f_out.write("User: spoorthi k gowda (ID: 8)\n")
    f_out.write("=" * 120 + "\n\n")

with app.app_context():
    # Get user by ID
    user = User.query.get(8)
    
    if not user:
        print("User not found!")
        sys.exit(1)
    
    profile = user.get_profile_dict()
    
    # Show user profile summary
    print("\n=== USER PROFILE ===")
    for key in sorted(profile.keys()):
        if profile[key] is not None:
            print(f"  {key}: {repr(profile[key])[:60]}")
    
    # Write profile to file
    with open(output_file, 'a', encoding='utf-8') as f_out:
        f_out.write("\n=== USER PROFILE ===\n")
        for key in sorted(profile.keys()):
            if profile[key] is not None:
                f_out.write(f"  {key}: {repr(profile[key])[:60]}\n")
        f_out.write("\n")
    
    # Get all active schemes
    all_schemes = Scheme.query.filter_by(is_active=True).all()
    
    # Build profile with all conditions covered
    all_condition_fields = set()
    for scheme in all_schemes:
        for cond in scheme.conditions:
            if is_user_answerable(cond.field):
                if getattr(cond, 'condition_type', None) == 'hard':
                    canonical = get_canonical_field(cond.field)
                    all_condition_fields.add(canonical)
    
    strict_profile = {}
    for key, value in profile.items():
        if value is not None:
            canonical = get_canonical_field(key)
            strict_profile[canonical] = value
    
    from app.engine.eligibility import simulate_answer
    for field in all_condition_fields:
        if field not in strict_profile or strict_profile[field] is None:
            strict_profile[field] = simulate_answer(field, profile)
    
    engine = EligibilityEngine()
    
    # Track global stats
    total_schemes = len(all_schemes)
    total_conditions = 0
    total_pass = 0
    total_fail = 0
    false_eligible_count = 0
    false_ineligible_count = 0
    
    false_eligible_schemes = []
    false_ineligible_schemes = []
    
    # Process ALL schemes
    print(f"\n=== PROCESSING {total_schemes} SCHEMES ===\n")
    
    for idx, scheme in enumerate(all_schemes):
        eo = engine.evaluate(scheme, strict_profile)
        
        # Get ALL conditions (no filtering)
        conditions = list(scheme.condition_rows)
        
        if not conditions:
            continue
        
        # Count pass/fail for this scheme
        scheme_pass = 0
        scheme_fail = 0
        scheme_hard_fail = 0
        scheme_hard_total = 0
        
        # Print scheme header
        print("\n" + "=" * 120)
        print(f"SCHEME: {scheme.name[:90]} (ID: {scheme.id})")
        print(f"FINAL RESULT: {eo.result.upper()}")
        print("-" * 120)
        print(f"{'FIELD':<45} {'TYPE':<7} {'COND_TYPE':<10} {'OPERATOR':<15} {'EXPECTED':<25} {'ACTUAL':<25} {'RESULT':<6}")
        print("-" * 120)
        
        # Write to file
        with open(output_file, 'a', encoding='utf-8') as f_out:
            f_out.write("\n" + "=" * 120 + "\n")
            f_out.write(f"SCHEME: {scheme.name[:90]} (ID: {scheme.id})\n")
            f_out.write(f"FINAL RESULT: {eo.result.upper()}\n")
            f_out.write("-" * 120 + "\n")
            f_out.write(f"{'FIELD':<45} {'TYPE':<7} {'COND_TYPE':<10} {'OPERATOR':<15} {'EXPECTED':<25} {'ACTUAL':<25} {'RESULT':<6}\n")
            f_out.write("-" * 120 + "\n")
        
        # Print EVERY condition (NO FILTERING)
        for cond in conditions:
            field = cond.field
            cond_type = getattr(cond, 'condition_type', 'soft')
            operator = cond.operator
            expected_val = cond.value
            field_type = "USER" if is_user_answerable(field) else "SYSTEM"
            
            if cond_type == 'hard':
                scheme_hard_total += 1
            
            # Get actual value from profile
            actual_val = get_profile_value(field, strict_profile)
            
            # Evaluate this single condition
            cr = evaluate_single(cond, strict_profile)
            result = cr.status.upper()
            
            total_conditions += 1
            if result == 'PASS':
                scheme_pass += 1
                total_pass += 1
            else:
                scheme_fail += 1
                total_fail += 1
                if cond_type == 'hard':
                    scheme_hard_fail += 1
            
            # Truncate for display
            expected_str = str(expected_val)[:25] if expected_val else 'None'
            actual_str = str(actual_val)[:25] if actual_val is not None else 'None'
            
            print(f"{field:<45} {field_type:<7} {cond_type:<10} {operator:<15} {expected_str:<25} {actual_str:<25} {result:<6}")
            
            # Write to file
            with open(output_file, 'a', encoding='utf-8') as f_out:
                f_out.write(f"{field:<45} {field_type:<7} {cond_type:<10} {operator:<15} {expected_str:<25} {actual_str:<25} {result:<6}\n")
        
        # Summary for this scheme
        print("-" * 120)
        print(f"SUMMARY: TOTAL: {len(conditions)} | PASS: {scheme_pass} | FAIL: {scheme_fail}")
        
        # Write to file
        with open(output_file, 'a', encoding='utf-8') as f_out:
            f_out.write("-" * 120 + "\n")
            f_out.write(f"SUMMARY: TOTAL: {len(conditions)} | PASS: {scheme_pass} | FAIL: {scheme_fail}\n")
        
        # Check for false results
        if eo.result == 'eligible' and scheme_hard_fail > 0:
            false_eligible_count += 1
            false_eligible_schemes.append((scheme.name[:60], scheme_hard_fail))
            print("🚨 FALSE ELIGIBLE - Has HARD conditions that FAILED!")
            with open(output_file, 'a', encoding='utf-8') as f_out:
                f_out.write("🚨 FALSE ELIGIBLE - Has HARD conditions that FAILED!\n")
        
        if eo.result == 'ineligible' and scheme_hard_fail == 0 and scheme_hard_total > 0:
            # Check if ALL hard conditions passed
            all_hard_pass = True
            for c in conditions:
                if getattr(c, 'condition_type', 'soft') == 'hard':
                    cr = evaluate_single(c, strict_profile)
                    if cr.status != 'pass':
                        all_hard_pass = False
                        break
            if all_hard_pass:
                false_ineligible_count += 1
                false_ineligible_schemes.append(scheme.name[:60])
                print("🚨 FALSE INELIGIBLE - ALL HARD conditions PASSED!")
                with open(output_file, 'a', encoding='utf-8') as f_out:
                    f_out.write("🚨 FALSE INELIGIBLE - ALL HARD conditions PASSED!\n")
    
    # Global summary
    print("\n" + "=" * 120)
    print("GLOBAL SUMMARY")
    print("=" * 120)
    print(f"TOTAL SCHEMES:    {total_schemes}")
    print(f"TOTAL CONDITIONS: {total_conditions}")
    print(f"TOTAL PASS:       {total_pass}")
    print(f"TOTAL FAIL:       {total_fail}")
    print(f"FALSE ELIGIBLE:   {false_eligible_count}")
    print(f"FALSE INELIGIBLE: {false_ineligible_count}")
    print("=" * 120)
    
    # Write to file
    with open(output_file, 'a', encoding='utf-8') as f_out:
        f_out.write("\n" + "=" * 120 + "\n")
        f_out.write("GLOBAL SUMMARY\n")
        f_out.write("=" * 120 + "\n")
        f_out.write(f"TOTAL SCHEMES:    {total_schemes}\n")
        f_out.write(f"TOTAL CONDITIONS: {total_conditions}\n")
        f_out.write(f"TOTAL PASS:       {total_pass}\n")
        f_out.write(f"TOTAL FAIL:       {total_fail}\n")
        f_out.write(f"FALSE ELIGIBLE:   {false_eligible_count}\n")
        f_out.write(f"FALSE INELIGIBLE: {false_ineligible_count}\n")
        f_out.write("=" * 120 + "\n")
    
    if false_eligible_schemes:
        print("\n🚨 FALSE ELIGIBLE SCHEMES (Hard conditions FAILED but result is ELIGIBLE):")
        for s, fail_count in false_eligible_schemes[:20]:
            print(f"  - {s} ({fail_count} hard fails)")
        with open(output_file, 'a', encoding='utf-8') as f_out:
            f_out.write("\n🚨 FALSE ELIGIBLE SCHEMES (Hard conditions FAILED but result is ELIGIBLE):\n")
            for s, fail_count in false_eligible_schemes[:20]:
                f_out.write(f"  - {s} ({fail_count} hard fails)\n")
    
    if false_ineligible_schemes:
        print("\n🚨 FALSE INELIGIBLE SCHEMES (All hard conditions PASSED but result is INELIGIBLE):")
        for s in false_ineligible_schemes[:20]:
            print(f"  - {s}")
        with open(output_file, 'a', encoding='utf-8') as f_out:
            f_out.write("\n🚨 FALSE INELIGIBLE SCHEMES (All hard conditions PASSED but result is INELIGIBLE):\n")
            for s in false_ineligible_schemes[:20]:
                f_out.write(f"  - {s}\n")

print("\n✅ Audit complete!")
print(f"Output saved to: {output_file}")