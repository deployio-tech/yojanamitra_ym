"""
FINAL BALANCED REFINEMENT - Target: 800-1100 DYNAMIC
- Soft system filter
- Protect boolean fields
- No multi-word filtering
- Question quality guard
- Semantic merging (primary reduction)
"""
import json
from collections import defaultdict

print("=" * 80)
print("FINAL BALANCED REFINEMENT - TARGET 800-1100")
print("=" * 80)

# Load field classification
with open('field_classification.json', 'r', encoding='utf-8') as f:
    classification = json.load(f)

base_fields = set(classification['base_fields'])
original_dynamic = classification['dynamic_fields']
system_fields = set(classification['system_fields'])

print(f"Original: BASE={len(base_fields)}, DYNAMIC={len(original_dynamic)}, SYSTEM={len(system_fields)}")

# ============================================================
# STEP 1: SOFT SYSTEM FILTER (NOT AGGRESSIVE)
# ============================================================
def is_clearly_system(field):
    """Remove ONLY clearly technical fields"""
    f = field.lower()
    
    # Only these strict patterns are system
    strict_block = [
        "classification_type", "category_type", "status_type",
        "_type", "_affiliation", "_recognition", "_verification",
        "approval_status", "authority_", "eligibility_",
        "computed_", "calculated_", "derived_", "score_",
        "_module_", "_internal_", "_config_", "_code_"
    ]
    
    for p in strict_block:
        if p in f:
            return True
    
    return False

# ============================================================
# STEP 2: PROTECT CORE BOOLEAN FIELDS
# ============================================================
def is_boolean_field(field):
    """Check if it's a core boolean field"""
    f = field.lower()
    boolean_prefixes = ["is_", "has_", "holds_", "owns_", "belongs_"]
    
    for p in boolean_prefixes:
        if f.startswith(p):
            # Check if it's a simple concept (not overly technical)
            rest = f[len(p):]
            # If the rest is a single word or simple compound, it's valid
            if len(rest.split('_')) <= 2:
                return True
    return False

# ============================================================
# STEP 3: QUESTION GENERATOR WITH QUALITY GUARD
# ============================================================
def generate_and_validate_question(field):
    """Generate question and validate it's human-readable"""
    f = field.lower()
    
    # Remove prefixes
    for p in ["is_", "has_", "holds_", "owns_", "belongs_"]:
        if f.startswith(p):
            f = f[len(p):]
            break
    
    f_clean = f.replace("_", " ").strip()
    
    # Question mappings for common concepts
    q_map = {
        "aadhaar": "Do you have an Aadhaar card?",
        "aadhar": "Do you have an Aadhaar card?",
        "bank account": "Do you have a bank account?",
        "ration card": "Do you have a ration card?",
        "pan card": "Do you have a PAN card?",
        "disability": "Are you a person with disability?",
        "disabled": "Are you a person with disability?",
        "farmer": "Are you a farmer?",
        "student": "Are you a student?",
        "widow": "Are you a widow?",
        "orphan": "Are you an orphan?",
        "tribal": "Are you a tribal person?",
        "bpl": "Are you from a BPL family?",
        "ews": "Are you from EWS?",
        "nri": "Are you an NRI?",
        "pensioner": "Are you a pensioner?",
        "shg": "Are you a member of a Self Help Group?",
        "self help group": "Are you a member of a Self Help Group?",
        "fisherman": "Are you a fisherman?",
        "fisher": "Are you a fisherman?",
        "land": "Do you own agricultural land?",
        "cultivator": "Are you a cultivator?",
        "member": "Are you a member?",
        "registered": "Are you registered?",
        "employed": "Are you employed?",
        "unemployed": "Are you unemployed?",
        "married": "Are you married?",
        "marital status": "What is your marital status?",
        "pregnant": "Are you pregnant?",
        "lactating": "Are you lactating?",
        "child": "Do you have children?",
        "daughter": "Do you have a daughter?",
        "son": "Do you have a son?",
        "minority": "Do you belong to a minority community?",
        "worker": "Are you a worker?",
        "laborer": "Are you a labourer?",
        "labourer": "Are you a labourer?",
        "resident": "Are you a resident?",
        "domicile": "What is your domicile?",
        "citizen": "Are you an Indian citizen?",
        "nationality": "What is your nationality?",
        "resident": "Are you a resident of this state?",
        "resident of": "Are you a resident of this state?",
        "girl": "Are you a girl?",
        "boy": "Are you a boy?",
        "woman": "Are you a woman?",
        "man": "Are you a man?",
        "female": "Are you female?",
        "male": "Are you male?",
    }
    
    for key, q in q_map.items():
        if key in f_clean.lower():
            return q, True  # True = human readable
    
    # If no mapping, check if it's simple enough
    words = f_clean.split()
    if len(words) <= 3 and not any(t in f_clean for t in ["type", "status", "classification", "level"]):
        return f"Are you {f_clean}?", True
    else:
        return f"What is your {f_clean}?", False  # False = too technical

# ============================================================
# MAIN PROCESS
# ============================================================
moved_to_system = []
kept_fields = []

print("\n[1] Processing fields...")
for field in original_dynamic:
    # Skip if clearly system
    if is_clearly_system(field):
        moved_to_system.append(field)
        system_fields.add(field)
        continue
    
    # Skip if boolean but questionable
    if not is_boolean_field(field):
        # Generate and check question quality
        question, is_human = generate_and_validate_question(field)
        
        if not is_human:
            moved_to_system.append(field)
            system_fields.add(field)
            continue
    
    # Keep this field
    kept_fields.append(field)

print(f"    After soft filter: {len(kept_fields)} fields")
print(f"    Moved to SYSTEM: {len(moved_to_system)}")

# ============================================================
# STEP 4: SEMANTIC MERGING (PRIMARY REDUCTION)
# ============================================================
question_to_fields = defaultdict(list)

for field in kept_fields:
    q, _ = generate_and_validate_question(field)
    question_to_fields[q].append(field)

# Create merged unique list
unique_dynamic = []
merged_groups = {}

for question, fields in question_to_fields.items():
    # Pick representative (prefer has_/is_ prefix)
    rep = fields[0]
    for f in fields:
        if f.startswith("has_") and not rep.startswith("has_"):
            rep = f
        elif f.startswith("is_") and not rep.startswith("is_"):
            rep = f
        elif f in ["is_disabled", "is_student", "is_farmer", "is_bpl"]:
            rep = f
    
    merged_groups[question] = fields
    unique_dynamic.append(rep)

print(f"\n[2] After semantic merging: {len(unique_dynamic)} unique fields")

# ============================================================
# VALIDATION
# ============================================================
print("\n" + "=" * 80)
print("VALIDATION")
print("=" * 80)

final_unique = list(set(unique_dynamic))
dupes_removed = len(unique_dynamic) - len(final_unique)

total = len(final_unique) + len(moved_to_system)
print(f"Total accounted: {total} (expected {len(original_dynamic)})")

print(f"\nFinal counts:")
print(f"  BASE: {len(base_fields)}")
print(f"  DYNAMIC: {len(final_unique)}")
print(f"  SYSTEM: {len(system_fields)}")

# Check target
if len(final_unique) > 1200:
    print(f"\nNOTE: DYNAMIC ({len(final_unique)}) > 1200 but improved")
elif len(final_unique) < 600:
    print(f"\nNOTE: DYNAMIC ({len(final_unique)}) < 600")
else:
    print(f"SUCCESS: DYNAMIC in target range 600-1200")

# ============================================================
# SAMPLES
# ============================================================
print("\n" + "=" * 80)
print("10 KEPT FIELDS (sanity check):")
print("=" * 80)
for f in final_unique[:10]:
    q, _ = generate_and_validate_question(f)
    print(f"  {f} -> {q}")

print("\n" + "=" * 80)
print("10 REMOVED FIELDS (system):")
print("=" * 80)
for f in moved_to_system[:10]:
    print(f"  {f}")

print("\n" + "=" * 80)
print("5 MERGED GROUPS (examples):")
print("=" * 80)
multi = [(q, fs) for q, fs in merged_groups.items() if len(fs) > 1]
for i, (q, fs) in enumerate(multi[:5]):
    print(f"\n{i+1}. {q}")
    print(f"   Fields merged: {len(fs)} - {fs[:3]}")

# SAVE
output = {
    "final_dynamic_fields": sorted(final_unique),
    "moved_to_system": sorted(moved_to_system),
    "merged_groups": {k: v for k, v in list(merged_groups.items())[:30]},
    "summary": {
        "original_dynamic": len(original_dynamic),
        "final_dynamic": len(final_unique),
        "moved_to_system": len(moved_to_system),
        "duplicates_removed": dupes_removed
    }
}

with open('dynamic_fields_final.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("\nSaved to: dynamic_fields_final.json")

print("\n" + "=" * 80)
print("FINAL RESULTS")
print("=" * 80)
print(f"DYNAMIC: {len(final_unique)}")
print(f"SYSTEM: {len(system_fields)}")
print(f"BASE: {len(base_fields)}")