"""
derived_fields.py
Deterministic derivation of computed fields from base profile data.

Runs automatically before evaluation and after each answer.
Critical distinction: is_bpl = False (user is NOT BPL) vs is_bpl absent from dict (UNKNOWN).

Usage:
    from derived_fields import enrich_profile, get_derived_fields
    
    # Before evaluation
    enriched = enrich_profile(user_profile)
    
    # Get list of derivable fields
    derivable = get_derived_fields()
"""
import logging
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Derivation rules: (derived_field, dependencies, function)
# Topologically sorted - dependencies must be resolvable first
DERIVED_RULES: List[tuple[str, List[str], Callable]] = [
    # Age-based derivations
    (
        "is_minor",
        ["age"],
        lambda p: p.get("age") is not None and int(p.get("age", 0)) < 18
    ),
    (
        "is_senior_citizen",
        ["age"],
        lambda p: p.get("age") is not None and int(p.get("age", 0)) >= 60
    ),
    (
        "is_adult",
        ["age"],
        lambda p: p.get("age") is not None and 18 <= int(p.get("age", 0)) < 60
    ),
    (
        "is_working_age",
        ["age"],
        lambda p: p.get("age") is not None and 18 <= int(p.get("age", 0)) <= 60
    ),
    
    # Income-based derivations
    (
        "is_bpl",
        ["income", "annual_family_income"],
        lambda p: (p.get("income") is not None and int(p.get("income", 0)) < 100000) or 
                 (p.get("annual_family_income") is not None and int(p.get("annual_family_income", 0)) < 100000)
    ),
    (
        "is_above_poverty_line",
        ["income", "annual_family_income"],
        lambda p: (p.get("income") is not None and int(p.get("income", 0)) >= 100000) or
                 (p.get("annual_family_income") is not None and int(p.get("annual_family_income", 0)) >= 100000)
    ),
    
    # Caste-based derivations
    (
        "is_sc_st",
        ["caste", "category"],
        lambda p: p.get("caste", p.get("category", "")).upper() in ["SC", "ST"]
    ),
    (
        "is_obc",
        ["caste", "category"],
        lambda p: p.get("caste", p.get("category", "")).upper() == "OBC"
    ),
    (
        "is_general",
        ["caste", "category"],
        lambda p: p.get("caste", p.get("category", "")).upper() == "GEN"
    ),
    (
        "is_ews",
        ["caste", "category"],
        lambda p: p.get("caste", p.get("category", "")).upper() == "EWS"
    ),
    
    # Gender + age combinations
    (
        "can_be_pregnant",
        ["gender", "age"],
        lambda p: p.get("gender", "").upper() == "F" and 15 <= int(p.get("age", 0)) <= 50
    ),
    (
        "is_woman",
        ["gender"],
        lambda p: p.get("gender", "").upper() in ["F", "FEMALE"]
    ),
    
    # Disability-based derivations
    (
        "is_disabled",
        ["disability_percentage", "disability"],
        lambda p: (p.get("disability_percentage") is not None and int(p.get("disability_percentage", 0)) >= 40) or bool(p.get("disability"))
    ),
    (
        "is_severely_disabled",
        ["disability_percentage"],
        lambda p: p.get("disability_percentage") is not None and int(p.get("disability_percentage", 0)) >= 80
    ),
    (
        "is_mildly_disabled",
        ["disability_percentage"],
        lambda p: p.get("disability_percentage") is not None and 0 < int(p.get("disability_percentage", 0)) < 40
    ),
    
    # Land-based derivations
    (
        "is_landless",
        ["land_size_acres", "own_agricultural_land"],
        lambda p: p.get("land_size_acres") == 0 or p.get("own_agricultural_land") == 0
    ),
    (
        "is_marginal_farmer",
        ["land_size_acres"],
        lambda p: p.get("land_size_acres") is not None and 0 < float(p.get("land_size_acres", 0)) <= 2.5
    ),
    (
        "is_small_farmer",
        ["land_size_acres"],
        lambda p: p.get("land_size_acres") is not None and 2.5 < float(p.get("land_size_acres", 0)) <= 5.0
    ),
    (
        "is_large_farmer",
        ["land_size_acres"],
        lambda p: p.get("land_size_acres") is not None and float(p.get("land_size_acres", 0)) > 5.0
    ),
    
    # Residence-based derivations
    (
        "is_rural",
        ["residence"],
        lambda p: p.get("residence", "").lower() == "rural"
    ),
    (
        "is_urban",
        ["residence"],
        lambda p: p.get("residence", "").lower() == "urban"
    ),
    
    # Employment-based derivations
    (
        "is_employed",
        ["employment_status"],
        lambda p: p.get("employment_status", "").lower() in ["employed", "government employee", "private employee"]
    ),
    (
        "is_unemployed",
        ["employment_status"],
        lambda p: p.get("employment_status", "").lower() == "unemployed"
    ),
    (
        "is_self_employed",
        ["employment_status"],
        lambda p: p.get("employment_status", "").lower() == "self-employed"
    ),
    (
        "is_student",
        ["employment_status"],
        lambda p: p.get("employment_status", "").lower() == "student"
    ),
    (
        "is_retired",
        ["employment_status"],
        lambda p: p.get("employment_status", "").lower() == "retired"
    ),
    
    # Marital status derivations
    (
        "is_married",
        ["marital_status"],
        lambda p: p.get("marital_status", "").lower() == "married"
    ),
    (
        "is_single",
        ["marital_status"],
        lambda p: p.get("marital_status", "").lower() == "single"
    ),
    
    # Family composition
    (
        "has_children",
        ["num_daughters"],
        lambda p: p.get("num_daughters", 0) > 0
    ),
    (
        "has_many_children",
        ["num_daughters"],
        lambda p: p.get("num_daughters", 0) >= 3
    ),
]

# Index: derived field -> its dependencies
# Use set() to deduplicate
DERIVED_DEPENDENCIES: Dict[str, Set[str]] = {}
for derived, deps, _ in DERIVED_RULES:
    DERIVED_DEPENDENCIES[derived] = set(deps)

# Index: base field -> derived fields that depend on it
BASE_TO_DERIVED: Dict[str, Set[str]] = {}
for derived, deps, _ in DERIVED_RULES:
    for dep in deps:
        if dep not in BASE_TO_DERIVED:
            BASE_TO_DERIVED[dep] = set()
        BASE_TO_DERIVED[dep].add(derived)


def get_derived_fields() -> List[str]:
    """Get list of all derivable fields."""
    return [d[0] for d in DERIVED_RULES]


def get_dependencies(field: str) -> Set[str]:
    """Get dependencies for a derived field."""
    return DERIVED_DEPENDENCIES.get(field, set())


def get_derived_from_base(base_field: str) -> Set[str]:
    """Get derived fields that depend on a base field."""
    return BASE_TO_DERIVED.get(base_field, set())


def can_derive(profile: dict, derived_field: str) -> bool:
    """Check if we have all dependencies to derive a field."""
    deps = get_dependencies(derived_field)
    if not deps:
        return False
    return all(profile.get(d) is not None for d in deps)


def enrich_profile(profile: dict) -> dict:
    """
    Run the DAG to compute all derivable fields.
    
    If a field is explicitly set by user, NEVER override it.
    If a field is absent from dict (None), compute it from dependencies.
    
    The key distinction:
    - is_bpl = False (user answered: NOT BPL)
    - is_bpl absent from dict (we don't know yet)
    """
    enriched = dict(profile)
    
    for derived_field, deps, derive_fn in DERIVED_RULES:
        # SKIP if user explicitly set this field
        if derived_field in enriched and enriched[derived_field] is not None:
            continue
        
        # SKIP if we can't derive (missing dependencies)
        if not can_derive(enriched, derived_field):
            continue
        
        try:
            result = derive_fn(enriched)
            enriched[derived_field] = result
            logger.debug(f"Derived {derived_field} = {result} from {deps}")
        except Exception as e:
            logger.warning(f"Derivation error for {derived_field}: {e}")
            continue
    
    return enriched


def get_field_value(profile: dict, field: str) -> Any:
    """
    Get a field value, computing derived fields if needed.
    
    Priority:
    1. Explicitly set by user (highest priority)
    2. Derived from dependencies
    3. Base value
    """
    # Direct value
    if field in profile and profile[field] is not None:
        return profile[field]
    
    # Try to derive
    if field in DERIVED_DEPENDENCIES and can_derive(profile, field):
        for derived, deps, fn in DERIVED_RULES:
            if derived == field:
                try:
                    return fn(profile)
                except:
                    pass
    
    return None


def validate_required_fields(profile: dict) -> List[str]:
    """
    Validate that critical fields are present.
    Returns list of missing required fields.
    """
    required = [
        "age", "gender", "state", "income", "caste",
        "occupation", "education", "marital_status", "residence"
    ]
    
    missing = []
    for field in required:
        if profile.get(field) is None:
            missing.append(field)
    
    return missing


if __name__ == "__main__":
    # Test derivation
    logging.basicConfig(level=logging.INFO)
    
    # Test profile
    test_profile = {
        "age": 25,
        "gender": "F",
        "income": 50000,
        "caste": "SC",
        "residence": "Rural",
        "employment_status": "Student",
        "marital_status": "Single",
        "disability_percentage": 0,
    }
    
    enriched = enrich_profile(test_profile)
    
    print("Original profile:")
    for k, v in test_profile.items():
        print(f"  {k}: {v}")
    
    print("\nDerived fields:")
    derived_keys = [k for k in enriched.keys() if k not in test_profile]
    for k in sorted(derived_keys):
        print(f"  {k}: {enriched[k]}")
    
    print("\nMissing required fields for:", validate_required_fields({}))