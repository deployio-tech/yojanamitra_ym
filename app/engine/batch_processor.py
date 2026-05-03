"""
Batch Processor - orchestrates the unmapped field → concept generation pipeline.
DRY_RUN mode enabled by default for first verification.
"""
import json
import os
import sys

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import components
from app.engine.gemini_client import generate_concepts, build_prompt, call_gemini, parse_gemini_response
from app.engine.concept_validator import ConceptValidator
from app.engine.unmapped_logger import get_unmapped_summary, log_unmapped_fields, get_unmapped_fields_for_gemini


# Configuration
DRY_RUN = True  # Default True - must verify first before committing
BATCH_SIZE = 30  # Max fields per Gemini call (quality control)


def load_registry():
    """Load the concept registry."""
    registry_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'concept_registry.json')
    try:
        with open(registry_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading registry: {e}")
        return {"concepts": [], "field_to_concept": {}}


def save_registry(registry):
    """Save the concept registry."""
    registry_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'concept_registry.json')
    try:
        with open(registry_path, 'w') as f:
            json.dump(registry, f, indent=2)
        print(f"Registry saved successfully")
        return True
    except Exception as e:
        print(f"Error saving registry: {e}")
        return False


def add_to_registry(item, concept_name):
    """Add a new concept to the registry."""
    # Manual fix: normalize over-specific concepts
    concept_fixes = {
        'goat_farming_license': 'goat_farming',
        'poultry_farm': 'poultry_ownership',
        'cattle_ownership': 'livestock',
    }
    
    # Apply fix if exists
    if concept_name in concept_fixes:
        concept_name = concept_fixes[concept_name]
        print(f"  [FIX] Normalized concept to: {concept_name}")
    
    registry = load_registry()
    
    # Create new concept
    new_concept = {
        "concept": concept_name,
        "question": item.get("question", ""),
        "type": "boolean",  # Default type
        "options": ["yes", "no"],
        "input_hint": "yes/no",
        "type_group": "dynamic",
        "fields": [item.get("field", "")]
    }
    
    # Add to concepts
    registry["concepts"].append(new_concept)
    
    # Add to field_to_concept mapping
    registry["field_to_concept"][item.get("field", "")] = concept_name
    
    save_registry(registry)
    return True


def link_field_to_concept(field, concept_name):
    """Link an existing field to an existing concept."""
    registry = load_registry()
    
    if field in registry["field_to_concept"]:
        print(f"  Field '{field}' already mapped to '{registry['field_to_concept'][field]}'")
        return False
    
    # Add mapping
    registry["field_to_concept"][field] = concept_name
    
    # Also add to concept's fields list
    for c in registry["concepts"]:
        if c["concept"] == concept_name:
            if field not in c.get("fields", []):
                c["fields"].append(field)
            break
    
    save_registry(registry)
    return True


def process_unmapped_batch(batch_size=BATCH_SIZE, dry_run=DRY_RUN):
    """
    Process unmapped fields through the complete pipeline.
    
    Args:
        batch_size: Number of fields to process
        dry_run: If True, only print decisions without committing
    
    Returns:
        Dictionary with processing results
    """
    print("="*60)
    print("BATCH PROCESSOR - UNMAPPED FIELD CONCEPT GENERATION")
    print("="*60)
    
    print(f"\nConfiguration:")
    print(f"  Batch size: {batch_size}")
    print(f"  DRY_RUN: {dry_run}")
    
    # Step 1: Get unmapped fields
    print("\n[1] Fetching unmapped fields...")
    summary = get_unmapped_summary()
    
    if summary['total_entries'] == 0:
        print("  No unmapped fields to process. Exiting.")
        return {"status": "no_fields", "add": 0, "reuse": 0, "reject": 0}
    
    print(f"  Total unmapped fields: {summary['total_entries']}")
    print(f"  Unique fields: {len(summary['unique_fields'])}")
    
    # Get fields to process
    fields_to_process = summary['unique_fields'][:batch_size]
    print(f"  Processing batch: {len(fields_to_process)} fields")
    
    # Step 2: Call Gemini
    print("\n[2] Calling Gemini...")
    try:
        parsed_concepts = generate_concepts(fields_to_process, batch_size)
    except Exception as e:
        print(f"  ERROR: Gemini call failed: {e}")
        return {"status": "error", "message": str(e)}
    
    if not parsed_concepts:
        print("  ⚠️ Gemini returned no valid output")
        return {"status": "no_output", "add": 0, "reuse": 0, "reject": 0}
    
    print(f"  Parsed {len(parsed_concepts)} concepts from Gemini")
    
    # Step 3: Validate
    print("\n[3] Validating concepts...")
    validator = ConceptValidator()
    
    results = {
        "add": [],
        "reuse": [],
        "reject": []
    }
    
    for item in parsed_concepts:
        result = validator.validate(item)
        
        if result["action"] == "add":
            results["add"].append(result)
            if dry_run:
                print(f"  ADD: {result['concept']} ({result.get('field', '')})")
            else:
                # Actually add to registry
                add_to_registry(item, result['concept'])
                print(f"  ADDED: {result['concept']}")
        
        elif result["action"] == "reuse":
            results["reuse"].append(result)
            if dry_run:
                print(f"  REUSE: {result['concept']} (for {result.get('field', '')})")
            else:
                link_field_to_concept(result.get('field', ''), result['concept'])
                print(f"  LINKED: {result['concept']} -> {result.get('field', '')}")
        
        elif result["action"] == "reject":
            results["reject"].append(result)
            print(f"  REJECT: {result.get('field', '')} - {result['reason']}")
            # Log rejection
            validator.log_rejection(item, result['reason'])
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    print(f"  ADD (new concepts):   {len(results['add'])}")
    print(f"  REUSE (existing):     {len(results['reuse'])}")
    print(f"  REJECT (invalid):     {len(results['reject'])}")
    
    total = len(results['add']) + len(results['reuse']) + len(results['reject'])
    if total > 0:
        print(f"\n  Acceptance rate: {((len(results['add']) + len(results['reuse'])) / total * 100):.1f}%")
    
    if dry_run:
        print("\n  ⚠️ DRY_RUN MODE - No changes committed to registry")
        print("  To commit, set dry_run=False and run again")
    
    return {
        "status": "complete",
        "dry_run": dry_run,
        "add": len(results['add']),
        "reuse": len(results['reuse']),
        "reject": len(results['reject']),
        "details": results
    }


def run_with_commit():
    """Run the processor with commits enabled."""
    return process_unmapped_batch(dry_run=False)


if __name__ == "__main__":
    # Check if unmapped fields exist
    summary = get_unmapped_summary()
    
    if summary['total_entries'] == 0:
        print("No unmapped fields to process.")
        print("\nTo test the pipeline, create some unmapped entries:")
        print("  from app.engine.unmapped_logger import log_unmapped_fields")
        print("  log_unmapped_fields(['test_field_1', 'test_field_2'], scheme_id=1)")
    else:
        # Run in DRY_RUN mode by default
        result = process_unmapped_batch()
        
        print("\n" + "="*60)
        print("RUN COMPLETE")
        print("="*60)