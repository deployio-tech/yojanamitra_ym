"""
Final Refinement V2 - More Aggressive Filtering + Better Boolean Question Generation
"""
import json
from collections import defaultdict

print("=" * 80)
print("FINAL REFINEMENT V2 - AGGRESSIVE")
print("=" * 80)

# Load field classification
with open('field_classification.json', 'r', encoding='utf-8') as f:
    classification = json.load(f)

base_fields = set(classification['base_fields'])
original_dynamic = classification['dynamic_fields']
system_fields = set(classification['system_fields'])

print(f"Original: BASE={len(base_fields)}, DYNAMIC={len(original_dynamic)}, SYSTEM={len(system_fields)}")

# ============================================================
# VERY AGGRESSIVE SYSTEM FILTERS
# ============================================================
def is_system_field_aggressive(field):
    f = field.lower()
    
    # Block ALL these patterns
    block_patterns = [
        # Technical suffixes
        "_type", "_category", "_classification", "_status", "_level",
        "_stage", "_affiliation", "_recognition", "_approval", "_verification",
        "_certification", "_authority", "_component", "_segment",
        # Common keywords
        "type", "category", "classification", "status", "level", "stage",
        "affiliation", "recognition", "verification", "authority", "certification",
        "criteria", "requirement", "compliance", "eligibility", "scheme",
        # Institutional
        "registered_with", "approved_by", "recognized_by", "affiliated_to",
        "board_", "department_", "institution_", "authority_",
        # Technical
        "code", "number", "id", "serial", "module", "internal", "config"
    ]
    
    for p in block_patterns:
        if p in f:
            return True
    
    # Multi-word technical fields
    if f.count('_') >= 3:
        return True
        
    return False

# ============================================================
# IMPROVED BOOLEAN QUESTION GENERATOR
# ============================================================
def generate_better_question(field):
    """Generate better questions for boolean fields"""
    f = field.lower()
    
    # Remove common prefixes
    for p in ["is_", "has_", "holds_", "owns_", "belongs_"]:
        if f.startswith(p):
            f = f[len(p):]
            break
    
    # Clean up
    f = f.replace("_", " ").strip()
    
    # Better question patterns
    if "aadhaar" in f or "aadhar" in f:
        return "Do you have an Aadhaar card?"
    if "bank" in f and "account" in f:
        return "Do you have a bank account?"
    if "ration" in f:
        return "Do you have a ration card?"
    if "pan" in f:
        return "Do you have a PAN card?"
    if "disability" in f or "disabled" in f:
        return "Are you a person with disability?"
    if "farmer" in f:
        return "Are you a farmer?"
    if "student" in f:
        return "Are you a student?"
    if "widow" in f:
        return "Are you a widow?"
    if "orphan" in f:
        return "Are you an orphan?"
    if "tribal" in f or f == "st":
        return "Are you a tribal person?"
    if "bpl" in f:
        return "Are you from a BPL family?"
    if "ews" in f:
        return "Are you from EWS?"
    if "nri" in f:
        return "Are you an NRI?"
    if "pensioner" in f:
        return "Are you a pensioner?"
    if "shg" in f or "self help" in f:
        return "Are you a member of a Self Help Group?"
    if "fisherman" in f or "fisher" in f:
        return "Are you a fisherman?"
    if "land" in f or "cultivator" in f:
        return "Do you own agricultural land?"
    if "member" in f:
        return "Are you a member?"
    if "registered" in f:
        return "Are you registered?"
    if "employed" in f or "job" in f or "occupation" in f:
        return "Are you employed?"
    if "married" in f or "marital" in f:
        return "Are you married?"
    if "pregnant" in f or "lactating" in f:
        return "Are you pregnant or lactating?"
    if "child" in f or "daughter" in f or "son" in f:
        return "Do you have children?"
    if "minority" in f:
        return "Do you belong to a minority community?"
    if "worker" in f or "laborer" in f or "labour" in f:
        return "Are you a worker?"
    if "resident" in f or "domicile" in f:
        return "Are you a resident of this state?"
    if "citizen" in f or "nationality" in f:
        return "Are you an Indian citizen?"
    
    # Default: try yes/no format
    return f"Are you {f}?"

# ============================================================
# MAIN PROCESS
# ============================================================
moved_to_system = []
final_dynamic = []

# Aggressive filtering
for field in original_dynamic:
    if is_system_field_aggressive(field):
        moved_to_system.append(field)
        system_fields.add(field)
    else:
        final_dynamic.append(field)

print(f"\n[1] After aggressive filter: {len(final_dynamic)} fields")
print(f"    Moved to SYSTEM: {len(moved_to_system)}")

# Merge by question
question_to_fields = defaultdict(list)

for field in final_dynamic:
    q = generate_better_question(field)
    question_to_fields[q].append(field)

# Create final unique dynamic
unique_dynamic = []
merged_groups = {}

for question, fields in question_to_fields.items():
    # Pick representative
    rep = fields[0]
    for f in fields:
        if f.startswith("has_") and not rep.startswith("has_"):
            rep = f
        elif f.startswith("is_") and not rep.startswith("is_"):
            rep = f
        elif f == "is_disabled":
            rep = f
    
    merged_groups[question] = fields
    unique_dynamic.append(rep)

print(f"\n[2] After question merging: {len(unique_dynamic)} unique fields")

# ============================================================
# VALIDATION
# ============================================================
print("\n" + "=" * 80)
print("VALIDATION")
print("=" * 80)

final_unique = list(set(unique_dynamic))
dupes = len(unique_dynamic) - len(final_unique)

total = len(final_unique) + len(moved_to_system)
print(f"Total accounted: {total} (expected {len(original_dynamic)})")

print(f"\nFinal counts:")
print(f"  BASE: {len(base_fields)}")
print(f"  DYNAMIC: {len(final_unique)}")
print(f"  SYSTEM: {len(system_fields)}")

if len(final_unique) > 1200:
    print(f"\nWARNING: DYNAMIC ({len(final_unique)}) > 1200")
elif len(final_unique) < 600:
    print(f"\nWARNING: DYNAMIC ({len(final_unique)}) < 600")
else:
    print(f"OK: DYNAMIC in range")

# ============================================================
# SAMPLES
# ============================================================
print("\n" + "=" * 80)
print("10 FIELDS MOVED TO SYSTEM:")
print("=" * 80)
for f in moved_to_system[:10]:
    print(f"  {f}")

# Show groups with multiple fields
print("\n" + "=" * 80)
print("MERGED GROUPS (2+ fields):")
print("=" * 80)
multi = [(q, fs) for q, fs in merged_groups.items() if len(fs) > 1]
for i, (q, fs) in enumerate(multi[:15]):
    print(f"\n{i+1}. {q}")
    print(f"   Fields: {len(fs)} - {fs[:3]}")

print("\n" + "=" * 80)
print("10 SAMPLE QUESTIONS:")
print("=" * 80)
for q in list(set(generate_better_question(f) for f in final_unique))[:10]:
    print(f"  {q}")

# SAVE
output = {
    "final_dynamic_fields": sorted(final_unique),
    "moved_to_system": sorted(moved_to_system),
    "merged_groups": {k: v for k, v in list(merged_groups.items())[:30]},
    "summary": {
        "original_dynamic": len(original_dynamic),
        "final_dynamic": len(final_unique),
        "moved_to_system": len(moved_to_system)
    }
}

with open('dynamic_fields_final.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("\nSaved to: dynamic_fields_final.json")
print(f"\nFINAL: DYNAMIC={len(final_unique)}, SYSTEM={len(system_fields)}, BASE={len(base_fields)}")