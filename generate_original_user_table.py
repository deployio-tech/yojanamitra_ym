import sys
sys.path.insert(0, '.')
from app import app, User, Scheme
from app.engine.eligibility import EligibilityEngine, get_canonical_field, get_profile_value, evaluate_single
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

print("Generating full condition comparison for Original User...")
print("=" * 70)

output_lines = []
output_lines.append("ID|SCHEME_NAME|RESULT|CONFIDENCE|HARD_USER_PASS|HARD_USER_FAIL|SOFT_USER_FAIL|SYSTEM_MISSING|FALSE_ELIGIBLE")

with app.app_context():
    # Get original user profile
    user = User.query.filter_by(email='shreyas6504@gmail.com').first()
    profile = user.get_profile_dict()
    
    print(f"User: {user.email}")
    print(f"Profile keys: {list(profile.keys())[:10]}...")
    
    engine = EligibilityEngine()
    qengine = QuestionEngine()
    
    all_schemes = Scheme.query.filter_by(is_active=True).all()
    total = len(all_schemes)
    print(f"Total schemes to evaluate: {total}")
    
    false_eligible_count = 0
    
    for i, scheme in enumerate(all_schemes):
        eo = resolve_with_iterations(engine, qengine, scheme, profile, max_iter=2)
        
        # Calculate stats
        hard_user_pass = 0
        hard_user_fail = 0
        soft_user_fail = 0
        system_missing = 0
        
        for cond in scheme.conditions:
            actual = get_profile_value(cond.field, profile)
            field_type = "USER" if is_user_answerable(cond.field) else "SYSTEM"
            cond_type = getattr(cond, 'condition_type', 'soft')
            
            if actual is None:
                result = "MISSING"
            else:
                raw = evaluate_single(cond, profile)
                result = raw.status
            
            if field_type == "USER" and cond_type == "hard":
                if result == "pass":
                    hard_user_pass += 1
                elif result == "fail":
                    hard_user_fail += 1
            elif field_type == "USER" and cond_type == "soft":
                if result == "fail":
                    soft_user_fail += 1
            elif field_type == "SYSTEM" and result == "MISSING":
                system_missing += 1
        
        # Check false eligible
        is_false_eligible = "N"
        if eo.result == "eligible" and hard_user_fail > 0:
            is_false_eligible = "Y"
            false_eligible_count += 1
        
        # Write line
        name = scheme.name[:60].replace('|', '-')
        output_lines.append(f"{scheme.id}|{name}|{eo.result.upper()}|{eo.confidence}|{hard_user_pass}|{hard_user_fail}|{soft_user_fail}|{system_missing}|{is_false_eligible}")
        
        if (i + 1) % 500 == 0:
            print(f"  Processed {i+1}/{total}...")

# Write to file
with open('full_condition_comparison_original_user.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))

print(f"\nDone! Saved to full_condition_comparison_original_user.txt")
print(f"Total lines: {len(output_lines)}")

# Print summary
import re
content = '\n'.join(output_lines)
eligible = len(re.findall(r'\|ELIGIBLE\|', content))
possible = len(re.findall(r'\|POSSIBLE\|', content))
ineligible = len(re.findall(r'\|INELIGIBLE\|', content))
false_elig = len(re.findall(r'\|Y\|', content))

print()
print("=" * 50)
print("SUMMARY - ORIGINAL USER (shreyas6504@gmail.com)")
print("=" * 50)
print(f"ELIGIBLE:        {eligible}")
print(f"POSSIBLE:        {possible}")
print(f"INELIGIBLE:      {ineligible}")
print(f"TOTAL:           {eligible + possible + ineligible}")
print(f"FALSE ELIGIBLE:  {false_elig}")
print("=" * 50)