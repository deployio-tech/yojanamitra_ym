"""
engine/questions.py
Dynamic question trigger system.
- Only asks questions that change outcomes
- Batches questions that resolve multiple schemes
- Stores answers permanently into user profile

FIXED: Now uses canonical_field_registry for proper type/widget/question_text
"""
import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set

log = logging.getLogger(__name__)

from app.engine.eligibility import NON_ANSWERABLE_FIELDS
from app.engine.profile_normalizer import ProfileNormalizer
from app.engine.canonical_field_registry import (
    get_field_schema, get_all_fields, get_required_fields,
    get_widget_for_field, get_data_type_for_field, get_question_text_for_field,
    get_bounds_for_field, get_canonical_name
)

QUESTION_TEMPLATES = {
    "is_student":             "Are you currently enrolled as a student?",
    "is_farmer":              "Are you a farmer or engaged in agricultural activities?",
    "is_fisherman":           "Are you a fisherman or engaged in fishery/aquaculture?",
    "is_bpl":                 "Are you registered under the BPL (Below Poverty Line) category?",
    "is_disabled":            "Do you have a disability certificate (UDID or equivalent)?",
    "is_transgender":         "Do you identify as a transgender person?",
    "is_widow":               "Are you a widow?",
    "is_construction_worker": "Are you a registered construction worker?",
    "has_aadhaar":            "Do you have an Aadhaar card?",
    "has_bank_account":       "Do you have a bank account linked to Aadhaar?",
    "is_pregnant":            "Are you currently pregnant or a new mother?",
    "is_minority":            "Do you belong to a notified minority community?",
    "is_ews":                 "Do you belong to the Economically Weaker Section (EWS)?",
    "is_self_employed":       "Are you self-employed or running your own business?",
    "is_marginal_farmer":     "Do you own less than 2 hectares of agricultural land?",
    "has_domicile":           "Do you have a domicile certificate for your state?",
    "is_urban":               "Are you currently residing in an urban area?",
    "is_rural":               "Are you currently residing in a rural area?",
    "has_land_record":        "Do you have a land ownership / patta document?",
    "is_sc":                  "Do you belong to the Scheduled Caste (SC) category?",
    "is_st":                  "Do you belong to the Scheduled Tribe (ST) category?",
    "is_obc":                 "Do you belong to the Other Backward Class (OBC) category?",
}

from app.engine.eligibility import (
    CANONICAL_GROUPS, 
    FIELD_TO_CANONICAL, 
    get_canonical_field
)

import os as _os
_registry_path = _os.path.join(_os.path.dirname(__file__), '..', '..', 'concept_registry.json')
_field_to_concept = {}
try:
    with open(_registry_path, 'r') as f:
        _registry = json.load(f)
        _field_to_concept = _registry.get('field_to_concept', {})
except Exception:
    pass

def get_concept_for_field(field_name: str) -> str:
    return _field_to_concept.get(field_name, '')


def is_user_answerable(field_name: str) -> bool:
    if field_name.endswith("_disqualifies"):
        return False
    return True


@dataclass
class Question:
    question_id: str
    field: str
    concept: str
    text: str
    field_type: str = "boolean"
    options: list = field(default_factory=list)
    schemes_affected: list = field(default_factory=list)
    impact_score: float = 0.0
    widget: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "question_id": self.question_id,
            "field": self.field,
            "concept": self.concept,
            "text": self.text,
            "field_type": self.field_type,
            "options": self.options,
            "schemes_affected": self.schemes_affected,
            "impact_score": round(self.impact_score, 3),
            "widget": self.widget,
        }


class QuestionEngine:

    def __init__(self, context_reasoner=None, max_questions: int = None):
        self.ctx = context_reasoner
        self.max_q = max_questions
        self._normalizer = ProfileNormalizer.get_instance()

    def _is_answered_in_profile(self, field_name: str, user_profile: dict) -> bool:
        canonical = self._normalizer.form_to_canonical.get(field_name, field_name)
        return user_profile.get(canonical) is not None

    def _already_answered(self, field_name: str, user_profile: dict) -> bool:
        return user_profile.get(field_name) is not None

    def _estimate_impact(self, field_name: str, scheme, user_profile: dict) -> float:
        from app.engine.eligibility import evaluate_single, UNKNOWN_C
        for cond in scheme.conditions:
            if cond.field == field_name:
                if cond.condition_type == "hard":
                    return 0.90
                elif cond.condition_type == "soft":
                    return 0.40 + 0.30 * (cond.confidence or 0.5)
        return 0.30

    def select_questions(
        self,
        possible_schemes: list,
        user_profile: dict,
        session_answered: set = None,
        include_derived: bool = False,
    ) -> List[Question]:
        """
        Generate questions for ALL missing fields across possibly-eligible schemes.
        
        Uses canonical_field_registry for typed question generation:
        - Proper data_type from registry
        - Widget spec (number_input, toggle, dropdown, etc.)
        - Question text from registry
        
        Args:
            possible_schemes: List of (scheme, EligibilityOutput) tuples
            user_profile: Dict of known profile fields
            session_answered: Fields already answered this session
            include_derived: Whether to include derivable fields in missing_fields
            
        Returns:
            List of Question objects with typed widget specs
        """
        session_answered = session_answered or set()
        
        # Collect ALL missing fields from ALL possibly-eligible schemes
        all_missing: Dict[str, dict] = {}  # canonical_field -> {fields, schemes}
        
        for scheme, elig_out in possible_schemes:
            for field in elig_out.missing_fields:
                # Map to canonical field name
                canonical = get_canonical_name(field)
                
                if canonical not in all_missing:
                    all_missing[canonical] = {
                        'field': field,  # Original field name
                        'canonical': canonical,
                        'schemes': set(),
                    }
                all_missing[canonical]['schemes'].add(scheme.id)
        
        # Build questions from registry
        questions = []
        
        for canonical, data in all_missing.items():
            # Skip if already in profile
            if user_profile.get(canonical) is not None:
                continue
            
            # Skip if already answered this session
            if canonical in session_answered:
                continue
            
            # Skip NON_ANSWERABLE fields (system fields)
            if canonical in NON_ANSWERABLE_FIELDS:
                continue
            
            # Get schema from registry
            schema = get_field_schema(canonical)
            if not schema:
                # Fallback for unknown fields - log warning
                log.warning(f"REGISTRY_GAP: field '{canonical}' has no schema")
                continue
            
            # Build widget spec
            widget_spec = {
                "type": schema.get("widget", "text_input"),
                "min": schema.get("min"),
                "max": schema.get("max"),
                "unit": schema.get("unit"),
                "options": schema.get("allowed_values"),
                "placeholder": None,
            }
            
            # Use question text from schema
            question_text = schema.get("question_text", f"Please provide {canonical}")
            
            questions.append(Question(
                question_id=f"q_{canonical}",
                field=data['field'],
                concept=canonical,
                text=question_text,
                field_type=schema.get("data_type", "string"),
                options=schema.get("allowed_values") or [],
                schemes_affected=list(data['schemes']),
                impact_score=len(data['schemes']),
                widget=widget_spec,
            ))
        
        # Sort by number of affected schemes (highest first)
        questions.sort(key=lambda q: len(q.schemes_affected), reverse=True)
        
        # NO CAP - return ALL questions
        # Frontend handles pagination
        return questions

    def process_answer(self, user_id: str, field_name: str, raw_value, context_scheme_id: str = None):
        from app import db, UserProfileAttribute, QuestionAnswer, User
        import json as _json

        canonical = get_canonical_field(field_name)
        concept = get_concept_for_field(field_name)
        
        if not concept:
            from app.engine.unmapped_logger import log_unmapped_fields
            log_unmapped_fields([field_name], context_scheme_id)
            return None
        
        if concept == "other":
            return None
        
        from app.engine.normalize import normalize_answer
        typed_value = normalize_answer(raw_value, concept)
        
        if typed_value is None:
            log.warning(f"[PROCESS_ANSWER] Normalization failed for {field_name} -> concept={concept}, value={raw_value}")
            return None

        encoded = _json.dumps(typed_value)

        qa = QuestionAnswer(
            user_id=user_id,
            question_id=f"q_{field_name}",
            field=field_name,
            value=encoded,
            context=context_scheme_id,
        )
        db.session.add(qa)

        existing = UserProfileAttribute.query.filter_by(
            user_id=user_id, field=field_name
        ).first()
        if existing:
            existing.value = encoded
            existing.source = "question_answer"
        else:
            attr = UserProfileAttribute(
                user_id=user_id,
                field=field_name,
                value=encoded,
                source="question_answer",
                confidence=1.0,
            )
            db.session.add(attr)
        
        from app.engine.eligibility import FIELD_MAP_compat
        mapped_field = FIELD_MAP_compat(field_name) or field_name
        if mapped_field != field_name:
            mapped_existing = UserProfileAttribute.query.filter_by(
                user_id=user_id, field=mapped_field
            ).first()
            if mapped_existing:
                mapped_existing.value = encoded
                mapped_existing.source = "question_answer"
            else:
                mapped_attr = UserProfileAttribute(
                    user_id=user_id,
                    field=mapped_field,
                    value=encoded,
                    source="question_answer",
                    confidence=1.0,
                )
                db.session.add(mapped_attr)
        
        if canonical != field_name and canonical != mapped_field:
            canonical_existing = UserProfileAttribute.query.filter_by(
                user_id=user_id, field=canonical
            ).first()
            if canonical_existing:
                canonical_existing.value = encoded
                canonical_existing.source = "question_answer"
            else:
                canonical_attr = UserProfileAttribute(
                    user_id=user_id,
                    field=canonical,
                    value=encoded,
                    source="question_answer",
                    confidence=1.0,
                )
                db.session.add(canonical_attr)
        
        if concept and concept != canonical and concept != mapped_field and concept != field_name:
            concept_existing = UserProfileAttribute.query.filter_by(
                user_id=user_id, field=concept
            ).first()
            if concept_existing:
                concept_existing.value = encoded
                concept_existing.source = "question_answer"
            else:
                concept_attr = UserProfileAttribute(
                    user_id=user_id,
                    field=concept,
                    value=encoded,
                    source="question_answer",
                    confidence=1.0,
                )
                db.session.add(concept_attr)

        user = User.query.get(user_id)
        if user:
            user.bump_profile_version()

        db.session.commit()
        return typed_value
