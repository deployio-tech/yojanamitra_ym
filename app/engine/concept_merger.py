"""
Concept Merger - merges duplicate/similar concepts into canonical forms.
Uses 3-layer strategy:
  Layer 1: Exact normalization
  Layer 2: Keyword stripping
  Layer 3: Semantic grouping (AI-assisted)
"""
import json
import os
import re
from collections import defaultdict


REGISTRY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'concept_registry.json')

# Noise words to strip from concepts
NOISE_WORDS = {
    'is_', 'has_', 'does_', 'can_', 'will_',
    'active_', 'inactive_', 'registered_', 'unregistered_',
    'owns_', 'holding_', 'being_', 'becoming_',
    'beneficiary_', 'recipient_', 'eligible_', 'ineligible_',
    'new_', 'old_', 'current_', 'former_', 'previous_',
    '_status', '_type', '_category', '_classification',
}

# Semantic groupings - manually curated equivalent concepts
SEMANTIC_GROUPS = {
    'fisherman': ['fisherman', 'fisher', 'marine_fisherman', 'fishing', 'fish'],
    'farmer': ['farmer', 'agriculture', 'cultivator', 'agriculturist'],
    'student': ['student', 'studying', 'studier', 'learner'],
    'artisan': ['artisan', 'craftsman', 'craftsperson', 'handicraft'],
    'weaver': ['weaver', 'handloom', 'khadi'],
    'business': ['business', 'entrepreneur', 'enterprise', 'trader'],
    'worker': ['worker', 'labourer', 'laborer', 'employee'],
    'owner': ['owner', 'holder', 'possessor'],
    'member': ['member', 'participant', 'enrollee'],
    'vendor': ['vendor', 'seller', 'trader', 'hawker'],
}


def load_registry():
    """Load the concept registry."""
    try:
        with open(REGISTRY_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading registry: {e}")
        return {"concepts": [], "field_to_concept": {}}


def save_registry(registry):
    """Save the concept registry."""
    try:
        with open(REGISTRY_PATH, 'w') as f:
            json.dump(registry, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving registry: {e}")
        return False


def normalize_concept(concept):
    """
    Layer 1 + 2: Exact normalization + keyword stripping.
    """
    # Convert to lowercase
    normalized = concept.lower().strip()
    
    # Replace underscores with spaces for processing
    normalized = normalized.replace('_', ' ')
    
    # Strip noise words
    for noise in sorted(NOISE_WORDS, key=len, reverse=True):
        if normalized.startswith(noise.replace('_', ' ')):
            normalized = normalized[len(noise.replace('_', ' ')):].strip()
    
    # Convert back to snake_case
    normalized = normalized.replace(' ', '_').strip()
    
    # Remove trailing _s for plurals
    if normalized.endswith('_s') and len(normalized) > 3:
        normalized = normalized[:-2]
    
    return normalized


def extract_core_concept(concept):
    """
    Extract the core concept by removing common suffixes and prefixes.
    """
    core = normalize_concept(concept)
    
    # Remove common endings that don't change meaning
    suffixes = ['_status', '_type', '_category', '_class', '_info', '_details']
    for suffix in suffixes:
        if core.endswith(suffix):
            core = core[:-len(suffix)]
    
    return core


def get_semantic_group(concept):
    """
    Layer 3: Get semantic group for a concept.
    Returns the canonical group name if found.
    """
    normalized = normalize_concept(concept)
    
    for canonical, keywords in SEMANTIC_GROUPS.items():
        if normalized in keywords:
            return canonical
    
    return None


def calculate_similarity(c1, c2):
    """
    Calculate similarity between two concepts.
    Returns float between 0 and 1.
    """
    # Layer 1: Exact match after normalization
    if normalize_concept(c1) == normalize_concept(c2):
        return 1.0
    
    # Layer 2: Core concept match
    if extract_core_concept(c1) == extract_core_concept(c2):
        return 0.9
    
    # Layer 3: Semantic group match
    group1 = get_semantic_group(c1)
    group2 = get_semantic_group(c2)
    if group1 and group2 and group1 == group2:
        return 0.85
    
    # Calculate character-level similarity (simple Jaccard)
    set1 = set(c1.lower().split('_'))
    set2 = set(c2.lower().split('_'))
    
    if not set1 or not set2:
        return 0.0
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    if union == 0:
        return 0.0
    
    return intersection / union


def find_merge_candidates(concepts, threshold=0.8):
    """
    Find concepts that should be merged.
    
    Args:
        concepts: List of concept objects
        threshold: Similarity threshold (default 0.8)
    
    Returns:
        Dictionary mapping canonical concept -> list of mergeable concepts
    """
    merge_groups = defaultdict(list)
    
    # Build index by normalized concept
    concept_list = [(c['concept'], c) for c in concepts]
    
    checked = set()
    
    for i, (c1_name, c1_data) in enumerate(concept_list):
        if c1_name in checked:
            continue
            
        group = [c1_name]
        
        for j, (c2_name, c2_data) in enumerate(concept_list):
            if i == j or c2_name in checked:
                continue
            
            # Calculate similarity
            similarity = calculate_similarity(c1_name, c2_name)
            
            if similarity >= threshold:
                group.append(c2_name)
                checked.add(c2_name)
        
        if len(group) > 1:
            # Pick the most general concept as canonical
            canonical = min(group, key=len)  # Shorter = more general
            merge_groups[canonical] = group
        
        checked.add(c1_name)
    
    return merge_groups


def merge_concepts(dry_run=True, threshold=0.8):
    """
    Main function to merge duplicate concepts.
    
    Args:
        dry_run: If True, only show merge suggestions without applying
        threshold: Similarity threshold for merging
    
    Returns:
        Dictionary with merge results
    """
    print("="*60)
    print("CONCEPT MERGER")
    print("="*60)
    print(f"\nConfiguration:")
    print(f"  DRY_RUN: {dry_run}")
    print(f"  Threshold: {threshold}")
    
    # Load registry
    registry = load_registry()
    concepts = registry.get('concepts', [])
    
    print(f"\nAnalyzing {len(concepts)} concepts...")
    
    # Find merge candidates
    merge_groups = find_merge_candidates(concepts, threshold)
    
    if not merge_groups:
        print("\n  No merge candidates found.")
        return {"status": "no_merges", "merges": []}
    
    print(f"\n  Found {len(merge_groups)} merge groups:")
    
    results = {
        "merges": [],
        "skipped": 0
    }
    
    for canonical, group in merge_groups.items():
        others = [g for g in group if g != canonical]
        
        print(f"\n  MERGE GROUP: {canonical}")
        print(f"    Keep: {canonical}")
        print(f"    Merge into it: {others}")
        
        if not dry_run:
            # Execute merge
            # Update canonical concept's fields
            for concept in concepts:
                if concept['concept'] == canonical:
                    # Add fields from merged concepts
                    for other in others:
                        for c in concepts:
                            if c['concept'] == other:
                                for field in c.get('fields', []):
                                    if field not in concept.get('fields', []):
                                        concept['fields'].append(field)
                    
                    # Update field_to_concept mappings
                    for other in others:
                        for c in concepts:
                            if c['concept'] == other:
                                for field in c.get('fields', []):
                                    registry['field_to_concept'][field] = canonical
            
            # Mark merged concepts for removal
            merged_concepts = [c for c in concepts if c['concept'] in others]
            
            print(f"    -> Updated fields for {canonical}")
        
        results["merges"].append({
            "canonical": canonical,
            "merged": others,
            "action": "merge" if not dry_run else "suggested"
        })
    
    if not dry_run:
        # Remove merged concepts
        concepts = [c for c in concepts if c['concept'] not in [g for group in merge_groups.values() for g in group if g != list(merge_groups.keys())[list(merge_groups.values()).index(group)]]]
        
        # Actually, let's keep them simpler - just update the canonical
        # and don't delete the others (fields are now mapped to canonical)
        
        save_registry(registry)
        print(f"\n  Registry saved with {len(concepts)} concepts")
    else:
        print(f"\n  ⚠️ DRY_RUN - No changes applied")
        print("  To apply merges, run with dry_run=False")
    
    return results


if __name__ == "__main__":
    # Run in DRY_RUN mode first
    result = merge_concepts(dry_run=True, threshold=0.8)
    
    print("\n" + "="*60)
    print("RESULT")
    print("="*60)
    print(f"Status: {result.get('status')}")
    print(f"Merges found: {len(result.get('merges', []))}")