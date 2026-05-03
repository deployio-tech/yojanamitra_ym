#!/usr/bin/env python3
"""
Auto-generate profile_field_registry.json from existing sources.
Reads PROFILE_FORM_FIELDS, FIELD_MAP, and concept_registry.json.
"""
import ast, json, re, sys, os
from pathlib import Path

# Use script location to determine root
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent

def extract_profile_form_fields(source: str) -> set:
    """Extract PROFILE_FORM_FIELDS set/dict from questions.py source."""
    match = re.search(r'PROFILE_FORM_FIELDS\s*=\s*(\{[^}]+\})', source, re.DOTALL)
    if not match:
        sys.exit("ERROR: Could not find PROFILE_FORM_FIELDS in questions.py")
    return set(ast.literal_eval(match.group(1)))

def extract_field_map(source: str) -> dict:
    """Extract FIELD_MAP dict from eligibility.py source."""
    match = re.search(r'FIELD_MAP\s*=\s*(\{[^}]+\})', source, re.DOTALL)
    if not match:
        sys.exit("ERROR: Could not find FIELD_MAP in eligibility.py")
    return ast.literal_eval(match.group(1))

def to_camel_case(snake: str) -> str:
    parts = snake.split('_')
    return parts[0] + ''.join(p.title() for p in parts[1:])

def infer_type(field: str) -> str:
    if field.startswith('is_') or field.startswith('has_'):
        return 'boolean'
    if any(x in field for x in ['acres', 'income', 'age', 'percentage', 'count']):
        return 'integer'
    return 'string'

def generate_form_mappings(canonical: str) -> list:
    mappings = [canonical]
    camel = to_camel_case(canonical)
    if camel != canonical:
        mappings.append(camel)
    return mappings

def generate_registry():
    try:
        questions_src = (ROOT / 'app/engine/questions.py').read_text()
        eligibility_src = (ROOT / 'app/engine/eligibility.py').read_text()
        concept_data = json.loads((ROOT / 'concept_registry.json').read_text())
    except FileNotFoundError as e:
        sys.exit(f"ERROR: Source file not found: {e}")

    profile_form_fields = extract_profile_form_fields(questions_src)
    field_map = extract_field_map(eligibility_src)
    field_to_concept = concept_data.get('field_to_concept', {})

    registry = {
        "_comment": "DO NOT EDIT — generated from scripts/generate_profile_registry.py",
        "version": "1.0",
        "profile_fields": {}
    }
    uncertain = []

    all_fields = profile_form_fields | set(field_map.values())

    for field in sorted(all_fields):
        concepts = []
        if field in field_to_concept:
            concepts.append(field_to_concept[field])

        # Find all form_mappings pointing to this canonical field
        extra_mappings = [
            cond for cond, canonical in field_map.items()
            if canonical == field and cond != field
        ]
        if not concepts:
            uncertain.append({
                "field": field,
                "reason": "No concept mapping found in field_to_concept"
            })

        mappings = generate_form_mappings(field) + extra_mappings
        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for m in mappings:
            if m not in seen:
                seen.add(m)
                deduped.append(m)

        registry["profile_fields"][field] = {
            "type": infer_type(field),
            "concepts": concepts or ["other"],
            "form_mappings": deduped,
            "derives": {}
        }

    out_path = ROOT / 'profile_field_registry.json'
    out_path.write_text(json.dumps(registry, indent=2))
    print(f"✓ Generated {out_path} with {len(registry['profile_fields'])} fields")

    if uncertain:
        u_path = ROOT / 'uncertain_mappings.json'
        u_path.write_text(json.dumps(uncertain, indent=2))
        print(f"⚠️  {len(uncertain)} fields need manual review → uncertain_mappings.json")

if __name__ == "__main__":
    generate_registry()
