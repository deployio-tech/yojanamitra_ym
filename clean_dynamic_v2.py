"""
Clean and Optimize DYNAMIC_FIELDS (IMPROVED MERGING)
"""
import json
from collections import defaultdict

print("=" * 80)
print("CLEANING DYNAMIC FIELDS (IMPROVED)")
print("=" * 80)

# Load field classification
with open('field_classification.json', 'r', encoding='utf-8') as f:
    classification = json.load(f)

base_fields = set(classification['base_fields'])
dynamic_fields = classification['dynamic_fields']
system_fields = set(classification['system_fields'])

print(f"Original: BASE={len(base_fields)}, DYNAMIC={len(dynamic_fields)}, SYSTEM={len(system_fields)}")

# ============================================================
# IMPROVED FILTERS
# ============================================================
def is_system_field(field):
    """Aggressive system field detection"""
    field_lower = field.lower()
    patterns = [
        "max", "min", "limit", "threshold", "cap",
        "score", "priority", "ranking", "grade", "level",
        "eligibility", "eligible", "qualified", "qualification",
        "computed", "calculated", "derived", "estimated",
        "criteria", "requirement", "condition", "compliance",
        "verification", "validation", "status_check",
        "approval", "authority", "certification", "accreditation",
        "type", "category", "classification", "component",
        "module", "internal", "config", "parameter",
        "code", "number", "id", "serial",
        "affiliation", "recognition", "membership_status"
    ]
    for p in patterns:
        if p in field_lower:
            return True
    return False

def get_base_concept(field):
    """Get the base concept for field"""
    field_lower = field.lower()
    concepts = {
        "aadhaar": "has_aadhaar",
        "aadhar": "has_aadhaar",
        "bank": "has_bank_account",
        "ration": "has_ration_card",
        "pan": "has_pan_card",
        "disability": "is_disabled",
        "farmer": "is_farmer",
        "student": "is_student",
        "widow": "is_widow",
        "orphan": "is_orphan",
        "minority": "is_minority",
        "tribal": "is_tribal",
        "bpl": "is_bpl",
        "ews": "is_ews",
        "nri": "is_nri",
        "pensioner": "is_pensioner",
        "land": "owns_land",
        "shg": "is_shg_member",
        "certificate": "has_certificate",
        "license": "has_license",
        "card": "has_card",
        "registration": "is_registered",
        "member": "is_member"
    }
    for key, concept in concepts.items():
        if key in field_lower:
            return concept
    return None

# ============================================================
# STEP 1: Filter system fields
# ============================================================
temp_dynamic = []
moved_to_system = []
moved_to_base = []

for field in dynamic_fields:
    if is_system_field(field):
        moved_to_system.append(field)
        system_fields.add(field)
    else:
        temp_dynamic.append(field)

print(f"\n[1] After system filter: {len(temp_dynamic)} fields")

# ============================================================
# STEP 2: Merge by semantic concept
# ============================================================
concept_to_fields = defaultdict(list)

for field in temp_dynamic:
    concept = get_base_concept(field)
    if concept:
        concept_to_fields[concept].append(field)
    else:
        # No concept match - keep as unique
        concept_to_fields[field].append(field)

# Create final dynamic fields - one per concept
final_dynamic = []
merged_groups = {}

for concept, fields in concept_to_fields.items():
    # Pick representative field
    representative = concept  # Use concept as the field name
    final_dynamic.append(representative)
    merged_groups[concept] = fields

print(f"\n[2] After semantic merging: {len(final_dynamic)} fields")

# ============================================================
# VALIDATION
# ============================================================
print("\n" + "=" * 80)
print("VALIDATION")
print("=" * 80)

# Check total
total = len(final_dynamic) + len(moved_to_system) + len(moved_to_base)
print(f"Total accounted: {total} (expected {len(dynamic_fields)})")

print(f"\nFinal counts:")
print(f"  BASE: {len(base_fields)}")
print(f"  DYNAMIC: {len(final_dynamic)}")
print(f"  SYSTEM: {len(system_fields)}")

# Show samples
print("\n" + "=" * 80)
print("SAMPLE MERGED GROUPS:")
print("=" * 80)
for i, (concept, fields) in enumerate(list(merged_groups.items())[:15]):
    print(f"\n{concept}:")
    print(f"  Original fields ({len(fields)}): {fields[:5]}")

print("\n" + "=" * 80)
print("FINAL DYNAMIC FIELDS:")
print("=" * 80)
for f in sorted(final_dynamic):
    print(f"  {f}")

# Save
output = {
    "final_dynamic_fields": sorted(final_dynamic),
    "moved_to_system": sorted(moved_to_system),
    "moved_to_base": sorted(moved_to_base),
    "merged_groups": merged_groups,
    "summary": {
        "original_dynamic": len(dynamic_fields),
        "final_dynamic": len(final_dynamic),
        "moved_to_system": len(moved_to_system),
        "moved_to_base": len(moved_to_base)
    }
}

with open('dynamic_fields_cleaned.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("\nSaved to: dynamic_fields_cleaned.json")