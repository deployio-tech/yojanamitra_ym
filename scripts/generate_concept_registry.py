#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def generate():
    registry = json.loads((ROOT / 'profile_field_registry.json').read_text())

    concepts: list[dict] = []
    field_to_concept: dict[str, str] = {}
    concept_index: dict[str, dict] = {}

    for canonical, data in registry['profile_fields'].items():
        for concept in data.get('concepts', []):
            if concept not in concept_index:
                entry = {
                    "concept": concept,
                    "type": data.get('type', 'string'),
                    "fields": []
                }
                concept_index[concept] = entry
                concepts.append(entry)

            c = concept_index[concept]
            for f in [canonical] + data.get('form_mappings', []):
                if f not in c['fields']:
                    c['fields'].append(f)

            field_to_concept[canonical] = concept
            for m in data.get('form_mappings', []):
                field_to_concept[m] = concept

    output = {
        "_comment": "DO NOT EDIT — generated from scripts/generate_concept_registry.py",
        "concepts": concepts,
        "field_to_concept": field_to_concept
    }
    out = ROOT / 'concept_registry.json'
    out.write_text(json.dumps(output, indent=2))
    print(f"✓ concept_registry.json: {len(concepts)} concepts, "
          f"{len(field_to_concept)} field mappings")

if __name__ == "__main__":
    generate()
