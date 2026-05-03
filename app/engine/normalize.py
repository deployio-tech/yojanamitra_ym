"""
Normalization utilities for user answers.
Handles boolean, number, single_choice, and multi_choice types.
"""
import json
import os

# TRUE/FALSE sets for boolean normalization
TRUE_SET = {"yes", "true", "1", "y", "t", "on"}
FALSE_SET = {"no", "false", "0", "n", "f", "off"}

# Path to concept registry
CONCEPT_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'concept_registry.json')

# Cache for loaded concept config
_concept_config = None


def _load_concept_config():
    """Load concept registry and return concept config dict."""
    global _concept_config
    if _concept_config is not None:
        return _concept_config
    
    try:
        with open(CONCEPT_REGISTRY_PATH, 'r') as f:
            data = json.load(f)
            # Build concept_name -> config mapping
            _concept_config = {}
            for c in data.get('concepts', []):
                _concept_config[c['concept']] = {
                    'type': c.get('type', 'boolean'),
                    'options': c.get('options'),
                    'input_hint': c.get('input_hint', ''),
                    'fields': c.get('fields', [])
                }
    except Exception as e:
        print(f"Warning: Could not load concept registry: {e}")
        _concept_config = {}
    
    return _concept_config


def clean_number(value):
    """
    Clean and convert number string to float.
    Handles: ₹, lakh, crore, commas, whitespace
    """
    if value is None:
        return None
    
    if isinstance(value, (int, float)):
        return float(value)
    
    # Convert to string and clean
    s = str(value).lower().strip()
    s = s.replace(",", "").replace("₹", "").replace("rs.", "").replace("rs", "").strip()
    
    # Handle lakh/crore
    multiplier = 1
    if "lakh" in s or "lac" in s:
        multiplier = 100000
        s = s.replace("lakh", "").replace("lac", "").strip()
    elif "crore" in s:
        multiplier = 10000000
        s = s.replace("crore", "").strip()
    
    try:
        return float(s) * multiplier
    except ValueError:
        return None


def normalize_multi_choice(answer):
    """
    Normalize multi-choice answer to a set of lowercase strings.
    Handles: comma-separated strings, lists, or sets.
    """
    if answer is None:
        return set()


def _normalize_typed(answer, data_type: str, bounds: dict, allowed: list = None):
    """Type-safe normalization using schema bounds and allowed values."""
    
    if answer is None:
        return None
    
    # Boolean
    if data_type == 'boolean':
        if isinstance(answer, bool):
            return answer
        s = str(answer).lower().strip()
        TRUE_VALUES = {'yes', 'true', '1', 'haan', 'ha', 'han', 'हाँ'}
        FALSE_VALUES = {'no', 'false', '0', 'nahi', 'nahin', 'naha', 'नहीं'}
        if s in TRUE_VALUES:
            return True
        if s in FALSE_VALUES:
            return False
        return None
    
    # Integer
    if data_type == 'integer':
        cleaned = str(answer).replace(',', '').replace('₹', '').replace('Rs', '').replace('Rs.', '').strip()
        try:
            value = int(float(cleaned))
            # Validate bounds
            if bounds.get('min') is not None and value < bounds['min']:
                return None
            if bounds.get('max') is not None and value > bounds['max']:
                return None
            return value
        except (ValueError, TypeError):
            return None
    
    # Float
    if data_type == 'float':
        cleaned = str(answer).replace(',', '').replace('₹', '').strip()
        try:
            value = float(cleaned)
            if bounds.get('min') is not None and value < bounds['min']:
                return None
            if bounds.get('max') is not None and value > bounds['max']:
                return None
            return value
        except (ValueError, TypeError):
            return None
    
    # Categorical
    if data_type == 'categorical' and allowed:
        s = str(answer).strip().upper()
        # Try exact match
        for opt in allowed:
            if s == opt.upper():
                return opt
        # Try partial match
        for opt in allowed:
            if s in opt.upper():
                return opt
        return None
    
    # Default: return as string
    return str(answer)
    
    if isinstance(answer, set):
        return {str(x).lower().strip() for x in answer if x}
    
    if isinstance(answer, list):
        return {str(x).lower().strip() for x in answer if x}
    
    if isinstance(answer, str):
        # Split by comma or semicolon
        parts = answer.replace(";", ",").split(",")
        return {x.lower().strip() for x in parts if x.strip()}
    
    return set()


def normalize_answer(answer, concept_name):
    """
    Normalize user answer based on field type from canonical_field_registry.
    
    Args:
        answer: Raw user answer (string, bool, int, list, set)
        concept_name: Canonical field name (e.g., 'age', 'gender', 'is_farmer')
    
    Returns:
        Normalized value:
        - boolean: True/False
        - integer: int
        - float: float
        - categorical: str (lowercase)
        - string: str
    """
    # Try canonical_field_registry first (authoritative)
    try:
        from app.engine.canonical_field_registry import get_field_schema
        schema = get_field_schema(concept_name)
        if schema:
            data_type = schema.get('data_type', 'string')
            bounds = {'min': schema.get('min'), 'max': schema.get('max')}
            allowed = schema.get('allowed_values')
            
            return _normalize_typed(answer, data_type, bounds, allowed)
    except ImportError:
        pass
    
    # Fallback to concept config
    config = _load_concept_config().get(concept_name, {})
    concept_type = config.get('type', 'boolean')
    
    if answer is None:
        return None
    
    # Boolean type
    if concept_type == 'boolean':
        if isinstance(answer, bool):
            return answer
        s = str(answer).lower().strip()
        if s in TRUE_SET:
            return True
        if s in FALSE_SET:
            return False
        return None
    
    # Number type
    elif concept_type == 'number':
        return clean_number(answer)
    
    # Single choice type
    elif concept_type == 'single_choice':
        if isinstance(answer, str):
            return answer.lower().strip()
        return str(answer).lower().strip()
    
    # Multi choice type
    elif concept_type == 'multi_choice':
        return normalize_multi_choice(answer)
    
    # Default: return as-is
    return answer


def get_concept_type(concept_name):
    """Get the type of a concept."""
    config = _load_concept_config().get(concept_name, {})
    return config.get('type', 'boolean')


def get_concept_options(concept_name):
    """Get the valid options for a concept."""
    config = _load_concept_config().get(concept_name, {})
    return config.get('options')


def get_concept_hint(concept_name):
    """Get the input hint for a concept."""
    config = _load_concept_config().get(concept_name, {})
    return config.get('input_hint', '')


# Test function
if __name__ == "__main__":
    # Test boolean
    print("Boolean tests:")
    print(f"  'yes' -> {normalize_answer('yes', 'aadhaar')}")  # True
    print(f"  'true' -> {normalize_answer('true', 'aadhaar')}")  # True
    print(f"  'no' -> {normalize_answer('no', 'aadhaar')}")  # False
    print(f"  '1' -> {normalize_answer('1', 'aadhaar')}")  # True
    print(f"  'invalid' -> {normalize_answer('invalid', 'aadhaar')}")  # None
    
    print("\nNumber tests:")
    print(f"  '150000' -> {normalize_answer('150000', 'annual_income')}")  # 150000.0
    print(f"  '₹1.5 lakh' -> {normalize_answer('₹1.5 lakh', 'annual_income')}")  # 150000.0
    print(f"  '2.5 crore' -> {normalize_answer('2.5 crore', 'annual_income')}")  # 25000000.0
    
    print("\nSingle choice tests:")
    print(f"  'MALE' -> {normalize_answer('MALE', 'gender')}")  # 'male'
    print(f"  'General' -> {normalize_answer('General', 'category')}")  # 'general'
    
    print("\nMulti choice tests:")
    print(f"  'sc, st, obc' -> {normalize_answer('sc, st, obc', 'categories')}")  # {'sc', 'st', 'obc'}
    print(f"  ['sc', 'st'] -> {normalize_answer(['sc', 'st'], 'categories')}")  # {'sc', 'st'}