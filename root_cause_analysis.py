import sys
sys.path.insert(0, '.')
from app import app, Scheme
from app.engine.questions import is_user_answerable
from collections import Counter

print("=" * 70)
print("ROOT CAUSE ANALYSIS - ALL UNKNOWN CONDITIONS")
print("=" * 70)

with app.app_context():
    all_schemes = Scheme.query.filter_by(is_active=True).all()
    
    # Find all HARD USER conditions that result in UNKNOWN
    unknown_conditions = []
    
    for scheme in all_schemes:
        for cond in scheme.conditions:
            if not is_user_answerable(cond.field):
                continue
            if getattr(cond, 'condition_type', None) != 'hard':
                continue
            
            # Check if condition value is problematic
            is_problematic = False
            reason = ""
            
            # Check 1: operator is 'between' but value is 'None'
            if cond.operator == 'between' and cond.value == 'None':
                is_problematic = True
                reason = "between with None value"
            
            # Check 2: operator not supported
            supported_ops = {'lte', 'gte', 'eq', 'neq', 'in', 'one_of', 'not_in', 'not_one_of', 'boolean', 'range', 'between'}
            if cond.operator not in supported_ops:
                is_problematic = True
                reason = f"unsupported operator: {cond.operator}"
            
            # Check 3: value is 'None' string for non-between operators
            if cond.value == 'None' and cond.operator != 'between':
                is_problematic = True
                reason = "value is 'None' string"
            
            if is_problematic:
                unknown_conditions.append({
                    'scheme': scheme.name[:40],
                    'field': cond.field,
                    'operator': cond.operator,
                    'value': cond.value[:30] if cond.value else 'None',
                    'reason': reason
                })
    
    print(f"\nTotal problematic HARD USER conditions: {len(unknown_conditions)}")
    
    # Group by reason
    reasons = Counter([uc['reason'] for uc in unknown_conditions])
    print("\n=== BREAKDOWN BY REASON ===")
    for reason, count in reasons.most_common():
        print(f"  {reason}: {count}")
    
    # Group by operator
    ops = Counter([uc['operator'] for uc in unknown_conditions])
    print("\n=== BREAKDOWN BY OPERATOR ===")
    for op, count in ops.most_common():
        print(f"  {op}: {count}")
    
    # Group by field
    fields = Counter([uc['field'] for uc in unknown_conditions])
    print("\n=== TOP FIELDS ===")
    for field, count in fields.most_common(10):
        print(f"  {field}: {count}")

print("=" * 70)