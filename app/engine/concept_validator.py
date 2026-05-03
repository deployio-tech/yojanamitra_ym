"""
Concept Validator - validates Gemini output before registry update.
Enforces quality rules and prevents garbage from entering the registry.
"""
import json
import os


REGISTRY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'concept_registry.json')
REJECTED_LOG_PATH = 'rejected_concepts.json'


class ConceptValidator:
    """
    Validates Gemini-generated concepts against quality rules.
    
    Rules:
    1. Duplicate Concept -> reject
    2. Duplicate Question -> reuse
    3. Concept Quality Filter -> reject garbage
    4. Question Quality Filter -> reject bad questions
    5. Human Readability Check -> reject non-human
    """
    
    def __init__(self):
        self.registry = self._load_registry()
        self.existing_concepts = {c['concept'] for c in self.registry.get('concepts', [])}
        self.existing_questions = {self._normalize_question(q['question']) for q in self.registry.get('concepts', [])}
        self.field_to_concept = self.registry.get('field_to_concept', {})
    
    def _load_registry(self):
        """Load the concept registry."""
        try:
            with open(REGISTRY_PATH, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load registry: {e}")
            return {"concepts": [], "field_to_concept": {}}
    
    def _normalize_question(self, question):
        """Normalize question for comparison."""
        return question.lower().strip()
    
    def _normalize_concept(self, concept):
        """Normalize concept name."""
        return concept.strip().lower().replace(" ", "_")
    
    def _is_garbage_concept(self, concept):
        """Check if concept is garbage (quality filter)."""
        c = concept.lower().strip()
        
        # Rule: More than 4 words
        if len(c.split()) > 4:
            return True
        
        # Rule: Banned technical terms
        banned = {
            "status", "type", "classification", "indicator", 
            "flag", "metadata", "identifier", "category_type"
        }
        if any(b in c for b in banned):
            return True
        
        # Rule: Too short
        if len(c) < 3:
            return True
        
        return False
    
    def _is_bad_question(self, question, field=None):
        """Check if question is poor quality."""
        q = question.lower().strip()
        
        # Rule: "What is your..." with few words
        if q.startswith("what is your") and len(q.split()) <= 4:
            return True
        
        # Rule: Repeats raw field name
        if field:
            field_normalized = field.replace("_", " ")
            if field_normalized in q:
                return True
        
        # Rule: Technical terms
        banned = {"metadata", "identifier", "classification", "code", "parameter"}
        if any(b in q for b in banned):
            return True
        
        # Rule: Too short
        if len(q) < 8:
            return True
        
        return False
    
    def _is_human_readable(self, question):
        """Check if question is human-readable."""
        return (
            "?" in question and
            3 <= len(question.split()) <= 15
        )
    
    def validate(self, item):
        """
        Validate a single concept object.
        
        Args:
            item: {"field": "...", "concept": "...", "question": "..."}
        
        Returns:
            {
                "valid": True/False,
                "concept": cleaned_concept,
                "action": "add"/"reuse"/"reject",
                "reason": "..."
            }
        """
        field = item.get("field", "")
        concept = self._normalize_concept(item.get("concept", ""))
        question = item.get("question", "").strip()
        
        # Rule 1: Duplicate concept check
        if concept in self.existing_concepts:
            return {
                "valid": False,
                "concept": concept,
                "action": "reject",
                "reason": "duplicate_concept",
                "field": field
            }
        
        # Rule 2: Duplicate question check
        norm_q = self._normalize_question(question)
        if norm_q in self.existing_questions:
            # Find existing concept for this question
            for c in self.registry.get('concepts', []):
                if self._normalize_question(c.get('question', '')) == norm_q:
                    return {
                        "valid": True,
                        "concept": c['concept'],
                        "action": "reuse",
                        "reason": "duplicate_question",
                        "field": field
                    }
        
        # Rule 3: Concept quality filter
        if self._is_garbage_concept(concept):
            return {
                "valid": False,
                "concept": concept,
                "action": "reject",
                "reason": "garbage_concept",
                "field": field
            }
        
        # Rule 4: Question quality filter
        if self._is_bad_question(question, field):
            return {
                "valid": False,
                "concept": concept,
                "action": "reject",
                "reason": "bad_question",
                "field": field
            }
        
        # Rule 5: Human readability check
        if not self._is_human_readable(question):
            return {
                "valid": False,
                "concept": concept,
                "action": "reject",
                "reason": "not_human_readable",
                "field": field
            }
        
        # All checks passed
        return {
            "valid": True,
            "concept": concept,
            "action": "add",
            "reason": "valid",
            "field": field,
            "question": question
        }
    
    def log_rejection(self, item, reason):
        """Log rejected concept to file."""
        existing = []
        if os.path.exists(REJECTED_LOG_PATH):
            try:
                with open(REJECTED_LOG_PATH, 'r') as f:
                    existing = json.load(f)
            except:
                existing = []
        
        entry = {
            "field": item.get("field", ""),
            "concept": item.get("concept", ""),
            "question": item.get("question", ""),
            "reason": reason,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
        existing.append(entry)
        
        with open(REJECTED_LOG_PATH, 'w') as f:
            json.dump(existing, f, indent=2)
    
    def get_summary(self):
        """Get validation summary from registry."""
        return {
            "total_concepts": len(self.existing_concepts),
            "total_mappings": len(self.field_to_concept)
        }


def validate_batch(items):
    """
    Validate a batch of concept items.
    
    Args:
        items: List of {"field": "...", "concept": "...", "question": "..."}
    
    Returns:
        Dictionary with counts and detailed results
    """
    validator = ConceptValidator()
    
    results = {
        "add": [],
        "reuse": [],
        "reject": []
    }
    
    for item in items:
        result = validator.validate(item)
        
        if result["action"] == "add":
            results["add"].append(result)
        elif result["action"] == "reuse":
            results["reuse"].append(result)
        elif result["action"] == "reject":
            results["reject"].append(result)
            # Log rejection
            validator.log_rejection(item, result["reason"])
    
    return results


if __name__ == "__main__":
    # Test validation
    test_items = [
        {"field": "has_aadhaar_card", "concept": "aadhaar", "question": "Do you have an Aadhaar card?"},
        {"field": "is_fisherman_new", "concept": "fisherman_status", "question": "What is your fisherman status?"},  # bad
        {"field": "owns_land", "concept": "land_ownership", "question": "Do you own agricultural land?"},
        {"field": "some_technical_field", "concept": "metadata_indicator", "question": "What is your metadata?"},  # garbage
    ]
    
    results = validate_batch(test_items)
    
    print("Validation Results:")
    print(f"  ADD: {len(results['add'])}")
    for r in results['add']:
        print(f"    + {r['concept']}: {r.get('question', '')[:50]}")
    
    print(f"\n  REUSE: {len(results['reuse'])}")
    
    print(f"\n  REJECT: {len(results['reject'])}")
    for r in results['reject']:
        print(f"    - {r['field']}: {r['reason']}")