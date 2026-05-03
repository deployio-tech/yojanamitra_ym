"""
╔══════════════════════════════════════════════════════════════════════════════╗
║     SEMANTIC ELIGIBILITY EXTRACTOR — Layer 2 of Hybrid Matching System     ║
║                                                                              ║
║  PURPOSE:                                                                   ║
║  Extract implicit eligibility conditions from scheme textual descriptions   ║
║  and convert them to enforceable semantic rules.                           ║
║                                                                              ║
║  EXAMPLES OF SEMANTIC CONDITIONS EXTRACTED:                                 ║
║  ✓ "students studying in Class VIII" → education_level: "Class VIII"      ║
║  ✓ "Only for farmers owning agricultural land" → must check land owner    ║
║  ✓ "widows aged 40-60" → widow + age range                                 ║
║  ✓ "unemployed youth" → occupation: unemployed, age: young                ║
║  ✓ "BPL families" → economic_status: BPL                                   ║
║  ✓ "SC/ST candidates" → caste category requirement                         ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Set, Tuple, Any

logger = logging.getLogger("yojanamitra.semantic_extractor")


class EducationLevel(str, Enum):
    """Standardized education levels."""
    CLASS_I = "Class I"
    CLASS_V = "Class V"
    CLASS_VIII = "Class VIII"
    CLASS_X = "Class X (10th)"
    CLASS_XII = "Class XII (12th)"
    GRADUATE = "UG (12+ pass)"
    POSTGRADUATE = "PG (Degree holder)"
    DIPLOMA = "Diploma"
    TECHNICAL = "Technical/ITI"
    NO_MINIMUM = "No minimum"


class OccupationType(str, Enum):
    """Standardized occupation types."""
    FARMER = "Farmer"
    STUDENT = "Student"
    UNEMPLOYED = "Unemployed"
    HOMEMAKER = "Homemaker"
    LABORER = "Laborer"
    ENTREPRENEUR = "Entrepreneur"
    SELF_EMPLOYED = "Self-employed"
    EMPLOYED = "Employed"
    PROFESSIONAL = "Professional"
    ARTISAN = "Artisan"
    INFORMAL = "Informal worker"


class EconomicStatus(str, Enum):
    """Economic classification."""
    BPL = "BPL (Below Poverty Line)"
    APL = "APL (Above Poverty Line)"
    EWS = "EWS (Economically Weaker Section)"
    LIG = "LIG (Low Income Group)"
    MIG = "MIG (Middle Income Group)"
    HIG = "HIG (High Income Group)"


class BeneficiaryType(str, Enum):
    """Type of beneficiary."""
    WIDOW = "Widow"
    SENIOR_CITIZEN = "Senior Citizen (60+)"
    DISABLED = "Disabled"
    ORPHAN = "Orphan"
    TRANSGENDER = "Transgender"
    MINORITY = "Minority"
    TRIBAL = "Tribal/ST"
    SC = "SC (Scheduled Caste)"
    OBC = "OBC"
    STUDENT = "Student"
    YOUTH = "Youth"
    WOMAN = "Woman"


@dataclass
class SemanticCondition:
    """Single extracted semantic condition."""
    
    # Condition type
    condition_type: str  # "education", "occupation", "age_range", "economic_status", etc.
    condition_value: str  # The specific value or requirement
    
    # Original text where found
    source_text: str  # The sentence/phrase from scheme description
    source_field: str  # "description", "eligibility", "benefits", etc.
    
    # Confidence in extraction (0.0-1.0)
    confidence: float = 1.0
    
    # Is this mandatory or optional
    is_mandatory: bool = True
    
    # Negation (e.g., "NOT for farmers")
    is_negated: bool = False
    
    def __str__(self) -> str:
        neg = "NOT " if self.is_negated else ""
        mandatory = "(Required)" if self.is_mandatory else "(Optional)"
        return f"{neg}{self.condition_type}={self.condition_value} {mandatory} [confidence: {self.confidence:.0%}]"


@dataclass
class SchemeSemanticProfile:
    """Complete semantic profile of a scheme."""
    
    scheme_id: str
    scheme_name: str
    
    # Extracted conditions
    conditions: List[SemanticCondition] = field(default_factory=list)
    
    # Categorized summaries
    required_education: Optional[EducationLevel] = None
    required_occupations: List[OccupationType] = field(default_factory=list)
    required_economic_status: Optional[EconomicStatus] = None
    required_beneficiary_types: List[BeneficiaryType] = field(default_factory=list)
    
    # Age constraints (semantic, not just min/max)
    age_constraints: str = ""  # e.g., "18-40 (youth)", "60+ (senior)", "21-65"
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    
    # Land/property requirements
    requires_land_ownership: bool = False
    requires_bank_account: bool = False
    requires_aadhar: bool = False

    # Income limits
    income_max: Optional[int] = None
    income_max_period: str = "annual"  # "annual" or "monthly"

    # Residence requirements
    required_residence: Optional[str] = None
    
    # Data quality
    validation_confidence: float = 1.0  # Overall confidence in extracted conditions
    
    def get_violations(self, user_profile: Dict[str, Any]) -> List[str]:
        """
        Check if user violates ANY semantic condition.
        Returns list of violation reasons (empty = no violations).
        """
        violations = []
        
        for condition in self.conditions:
            if not condition.is_mandatory:
                continue  # Skip optional conditions
            
            violation = self._check_condition(condition, user_profile)
            if violation:
                violations.append(violation)
        
        return violations
    
    def _check_condition(self, condition: SemanticCondition, user: Dict[str, Any]) -> Optional[str]:
        """Check single condition. Return violation message if failed."""

        if condition.condition_type == "age_range":
            user_age = user.get("age")
            if not user_age:
                return f"Missing age (scheme requires: {condition.condition_value} years)"

            parts = condition.condition_value.split("-")
            if len(parts) == 2:
                min_age, max_age = int(parts[0]), int(parts[1])
                if not (min_age <= user_age <= max_age):
                    return f"Age must be between {min_age} and {max_age} years"

        elif condition.condition_type == "education":
            user_education = user.get("education_level")
            if not user_education:
                return f"Missing education level (scheme requires: {condition.condition_value})"
            
            # Simple check: if scheme requires Class X, user must have at least Class X
            if not self._satisfies_education(condition.condition_value, user_education):
                negation = "must NOT be" if condition.is_negated else "must be"
                return f"Education level {negation} {condition.condition_value}"
        
        elif condition.condition_type == "occupation":
            user_occupations = user.get("occupations", [])
            if not user_occupations:
                return f"Missing occupation (scheme requires: {condition.condition_value})"
            
            required_occ = condition.condition_value.lower()
            user_occ_lower = [occ.lower() for occ in user_occupations]
            
            if condition.is_negated:
                # User must NOT have this occupation
                if any(required_occ in occ for occ in user_occ_lower):
                    return f"Cannot have occupation: {condition.condition_value}"
            else:
                # User must have this occupation
                if not any(required_occ in occ for occ in user_occ_lower):
                    return f"Must have occupation: {condition.condition_value}"
        
        elif condition.condition_type == "economic_status":
            user_status = user.get("economic_status")
            if not user_status:
                return f"Missing economic status (scheme requires: {condition.condition_value})"
            
            if user_status.lower() != condition.condition_value.lower():
                return f"Economic status must be: {condition.condition_value}"
        
        elif condition.condition_type == "beneficiary_type":
            # Map beneficiary types to user attributes
            beneficiary_map = {
                "widow": ("is_widow", True),
                "senior citizen": ("age", lambda age: age >= 60),
                "disabled": ("is_disabled", True),
                "orphan": ("is_orphan", True),
                "transgender": ("gender", "Transgender"),
                "sc": ("caste_category", "SC"),
                "st": ("caste_category", "ST"),
                "obc": ("caste_category", "OBC"),
                "woman": ("gender", "Female"),
                "student": ("is_student", True),
            }
            
            beneficiary_lower = condition.condition_value.lower()
            if beneficiary_lower in beneficiary_map:
                attr, expected = beneficiary_map[beneficiary_lower]
                user_value = user.get(attr)
                
                if callable(expected):
                    matches = expected(user_value) if user_value is not None else False
                else:
                    matches = user_value == expected
                
                if not matches:
                    negation = "must NOT be" if condition.is_negated else "must be"
                    return f"Beneficiary type {negation}: {condition.condition_value}"
        
        elif condition.condition_type == "land_ownership":
            if condition.condition_value == "required":
                user_owns_land = user.get("owns_land")
                if not user_owns_land:
                    return "Must own agricultural land"
        
        elif condition.condition_type == "bank_account":
            if condition.condition_value == "required":
                user_has_account = user.get("has_bank_account")
                if user_has_account is False:
                    return "Must have active bank account"

        elif condition.condition_type == "aadhar":
            if condition.condition_value == "required":
                user_has_aadhar = user.get("has_aadhar")
                if user_has_aadhar is False:
                    return "Must have Aadhaar card"

        elif condition.condition_type == "income_limit":
            user_income = user.get("annual_income")
            if user_income is not None:
                # Parse the condition value to get max income
                max_income = self._parse_income_limit(condition.condition_value)
                if max_income and user_income > max_income:
                    return f"Annual income must not exceed {max_income:,}"

        elif condition.condition_type == "residence":
            user_residence = user.get("state", "")
            if user_residence and condition.condition_value.lower() not in user_residence.lower():
                return f"Must be resident of {condition.condition_value}"

        return None  # No violation
    
    @staticmethod
    def _satisfies_education(required: str, user_has: str) -> bool:
        """Check if user's education meets requirement."""
        education_hierarchy = [
            "Class I", "Class V", "Class VIII", "Class X", "Class XII",
            "Diploma", "UG", "PG"
        ]
        
        try:
            req_idx = next(i for i, e in enumerate(education_hierarchy) if required.lower() in e.lower())
            has_idx = next(i for i, e in enumerate(education_hierarchy) if user_has.lower() in e.lower())
            return has_idx >= req_idx
        except StopIteration:
            return True  # Unknown education levels, assume OK


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — PATTERNS FOR SEMANTIC EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

class SemanticPatterns:
    """Regex and keyword patterns for extracting semantic conditions."""
    
    # Education patterns (with word boundaries)
    EDUCATION_PATTERNS = [
        (r"\bclass\s+(?:viii|8|10|12|x|xii)\b", "education", "class_level"),
        (r"\b(?:under\s+)?(?:post\s*)?graduate\b|\b(?:u\.?g\.?|p\.?g\.?)(?:\s|,|$)", "education", "graduate"),
        (r"\b(?:primary|secondary|higher\s+secondary|12\s+(?:pass|th)|10th|12th|ug|pg|diploma|iti)\b", "education", "education_level"),
        (r"\bclass\s+(?:i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii)\b", "education", "specific_class"),
    ]
    
    # Occupation patterns (with word boundaries)
    OCCUPATION_PATTERNS = [
        (r"\b(?:only\s+)?(?:for\s+)?farmers?\b", "occupation", "farmer"),
        (r"\bagricultural\s+workers?\b", "occupation", "farmer"),
        (r"\b(?:only\s+)?(?:for\s+)?students?\b", "occupation", "student"),
        (r"\b(?:unemployed|jobless|without\s+employment)\b", "occupation", "unemployed"),
        (r"\b(?:self\s*)?employed\b|\bentrepreneurs?\b|(?:small|micro)\s+business", "occupation", "entrepreneur"),
        (r"\bhomemakers?\b|\bhousewives?\b", "occupation", "homemaker"),
        (r"\blaborers?\b|\bconstruction\s+workers?\b", "occupation", "laborer"),
        (r"\b(?:professional|technical|skilled)\s+workers?\b", "occupation", "professional"),
        (r"\bartisans?\b|\bcraftsmen?\b", "occupation", "artisan"),
    ]
    
    # Economic status patterns (with word boundaries)
    ECONOMIC_PATTERNS = [
        (r"\bbelow\s+poverty\s+line\b|\bbpl\b", "economic_status", "BPL"),
        (r"\babove\s+poverty\s+line\b|\bapl\b", "economic_status", "APL"),
        (r"\beconomically\s+weaker\s+sections?\b|\bews\b", "economic_status", "EWS"),
        (r"\blow\s+income\s+groups?\b|\blig\b", "economic_status", "LIG"),
        (r"\bmiddle\s+income\s+groups?\b|\bmig\b", "economic_status", "MIG"),
        (r"\bhigh\s+income\s+groups?\b|\bhig\b", "economic_status", "HIG"),
    ]
    
    # Beneficiary type patterns (with word boundaries)
    BENEFICIARY_PATTERNS = [
        (r"\bwidows?\b", "beneficiary_type", "widow"),
        (r"\b(?:senior\s+)?citizens?\b|\baged?\s+(?:60|above)\b", "beneficiary_type", "senior_citizen"),
        (r"\bdisabled?\b|\bpersons?\s+with\s+disabilities?\b|\bpwds?\b", "beneficiary_type", "disabled"),
        (r"\borphans?\b", "beneficiary_type", "orphan"),
        (r"\btransgenders?\b", "beneficiary_type", "transgender"),
        (r"\bminorities?\b|\bminority\s+communities?\b", "beneficiary_type", "minority"),
        (r"\b(?:schedule[d]?|sc)\s+castes?\b", "beneficiary_type", "SC"),
        (r"\b(?:schedule[d]?|st)\s+tribes?\b", "beneficiary_type", "ST"),
        (r"\b(?:tribal|adivasi)\b", "beneficiary_type", "tribal"),
        (r"\bobc\b|\bother\s+backward\s+classes?\b", "beneficiary_type", "OBC"),
        (r"\b(?:only\s+)?(?:for\s+)?wo?men\b|\bfemale\b", "beneficiary_type", "woman"),
        (r"\b(?:only\s+)?(?:for\s+)?youths?\b|(?:18[-–])?\b35\s+years?\b|\byoung\s+(?:adults?|people)\b", "beneficiary_type", "youth"),
        (r"\b(?:only\s+)?(?:for\s+)?students?\b", "beneficiary_type", "student"),
    ]
    
    # Property/asset patterns (with word boundaries)
    PROPERTY_PATTERNS = [
        (r"\bagricultural\s+land\b|\bland\s+holdings?\b|\bland\s+ownership\b|\bowns?\s+land\b", "land_ownership", "required"),
        (r"\bbank\s+accounts?\b|\bactive\s+bank\s+accounts?\b", "bank_account", "required"),
        (r"\baadh?aar\b", "aadhar", "required"),
    ]

    # Income range patterns
    INCOME_PATTERNS = [
        (r"income\s+(?:of\s+)?(?:rs\.?|rupees?)\s*([\d,]+)(?:\s*[-–]\s*(?:rs\.?|rupees?)\s*([\d,]+))?", "income_range"),
        (r"(?:annual|monthly)\s+income\s+(?:of\s+)?(?:rs\.?|rupees?)\s*([\d,]+)", "income_range"),
    ]

    # Residence/region patterns
    RESIDENCE_PATTERNS = [
        (r"\bresident[s]?\s+of\s+([A-Za-z\s]+?)(?:\.|,|$)", "residence"),
        (r"\bdomicile\s+of\s+([A-Za-z\s]+?)(?:\.|,|$)", "residence"),
        (r"\bnative\s+of\s+([A-Za-z\s]+?)(?:\.|,|$)", "residence"),
    ]
    
    # Negation patterns
    NEGATION_PATTERNS = [
        r"not\s+eligible",
        r"(?:only\s+)?(?:for|except)\s+(?:non|non[\-\s])",
        r"cannot\s+(?:be|have)",
        r"(?:excluding|except)",
    ]


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — SEMANTIC EXTRACTOR
# ══════════════════════════════════════════════════════════════════════════════

class SemanticEligibilityExtractor:
    """Extract semantic conditions from unstructured scheme text."""
    
    def __init__(self):
        self.patterns = SemanticPatterns()
    
    def extract(self, scheme_json: Dict[str, Any]) -> SchemeSemanticProfile:
        """
        Extract semantic profile from scheme JSON.
        Analyzes: description, eligibility, notes, scheme name
        """
        profile = SchemeSemanticProfile(
            scheme_id=str(scheme_json.get("id", "unknown")),
            scheme_name=scheme_json.get("name", "Unknown")
        )
        
        # Collect relevant text fields
        text_fields = {
            "name": scheme_json.get("name", ""),
            "description": scheme_json.get("description", ""),
            "eligibility": scheme_json.get("eligibility", ""),
            "eligibility_criteria": scheme_json.get("eligibility_criteria", ""),
            "notes": scheme_json.get("notes", ""),
            "benefits": scheme_json.get("benefits", ""),
            "exclusions": scheme_json.get("exclusions", ""),
        }
        
        # Extract conditions from each field
        for field_name, text in text_fields.items():
            if not text:
                continue
            
            # Extract education conditions
            self._extract_education(text, field_name, profile)
            
            # Extract occupation conditions
            self._extract_occupation(text, field_name, profile)
            
            # Extract economic status
            self._extract_economic_status(text, field_name, profile)
            
            # Extract beneficiary types
            self._extract_beneficiary_types(text, field_name, profile)
            
            # Extract property/asset conditions
            self._extract_property_conditions(text, field_name, profile)

            # Extract age constraints (semantic, not structured)
            self._extract_age_constraints(text, field_name, profile)

            # Extract income constraints
            self._extract_income_constraints(text, field_name, profile)

            # Extract residence/region requirements
            self._extract_residence_constraints(text, field_name, profile)
        
        # Aggregate validation confidence
        if profile.conditions:
            # Deduplicate conditions by type + value combination
            seen = {}
            for cond in profile.conditions:
                key = (cond.condition_type, cond.condition_value.lower())
                if key not in seen:
                    seen[key] = cond
                else:
                    # Keep higher confidence
                    if cond.confidence > seen[key].confidence:
                        seen[key] = cond
            profile.conditions = list(seen.values())

            # Average confidence across all extracted conditions
            profile.validation_confidence = sum(c.confidence for c in profile.conditions) / len(profile.conditions)
        
        logger.info(f"Extracted {len(profile.conditions)} semantic conditions for scheme {profile.scheme_id}")
        
        return profile
    
    def _extract_education(self, text: str, field_name: str, profile: SchemeSemanticProfile):
        """Extract education level requirements."""
        text_lower = text.lower()
        
        for pattern, cond_type, cond_value in self.patterns.EDUCATION_PATTERNS:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                source_text = self._extract_context(text, match.start(), match.end())
                is_neg = self._is_negated(text, match.start())
                
                condition = SemanticCondition(
                    condition_type="education",
                    condition_value=cond_value,
                    source_text=source_text,
                    source_field=field_name,
                    confidence=0.85,
                    is_negated=is_neg,
                )
                profile.conditions.append(condition)
                
                # Set required education if not already set
                if not profile.required_education and not is_neg:
                    profile.required_education = self._map_education_value(cond_value)
    
    def _extract_occupation(self, text: str, field_name: str, profile: SchemeSemanticProfile):
        """Extract occupation requirements."""
        text_lower = text.lower()
        
        for pattern, cond_type, cond_value in self.patterns.OCCUPATION_PATTERNS:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                source_text = self._extract_context(text, match.start(), match.end())
                is_neg = self._is_negated(text, match.start())
                
                condition = SemanticCondition(
                    condition_type="occupation",
                    condition_value=cond_value,
                    source_text=source_text,
                    source_field=field_name,
                    confidence=0.90,
                    is_negated=is_neg,
                )
                profile.conditions.append(condition)
                
                # Add to required occupations
                if not is_neg:
                    occ_enum = self._map_occupation_value(cond_value)
                    if occ_enum and occ_enum not in profile.required_occupations:
                        profile.required_occupations.append(occ_enum)
    
    def _extract_economic_status(self, text: str, field_name: str, profile: SchemeSemanticProfile):
        """Extract economic status requirements."""
        text_lower = text.lower()
        
        for pattern, cond_type, cond_value in self.patterns.ECONOMIC_PATTERNS:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                source_text = self._extract_context(text, match.start(), match.end())
                is_neg = self._is_negated(text, match.start())
                
                condition = SemanticCondition(
                    condition_type="economic_status",
                    condition_value=cond_value,
                    source_text=source_text,
                    source_field=field_name,
                    confidence=0.88,
                    is_negated=is_neg,
                )
                profile.conditions.append(condition)
                
                # Set required economic status
                if not profile.required_economic_status and not is_neg:
                    profile.required_economic_status = self._map_economic_value(cond_value)
    
    def _extract_beneficiary_types(self, text: str, field_name: str, profile: SchemeSemanticProfile):
        """Extract beneficiary type requirements (widow, disabled, etc.)."""
        text_lower = text.lower()
        
        for pattern, cond_type, cond_value in self.patterns.BENEFICIARY_PATTERNS:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                source_text = self._extract_context(text, match.start(), match.end())
                is_neg = self._is_negated(text, match.start())
                
                condition = SemanticCondition(
                    condition_type="beneficiary_type",
                    condition_value=cond_value,
                    source_text=source_text,
                    source_field=field_name,
                    confidence=0.87,
                    is_negated=is_neg,
                )
                profile.conditions.append(condition)
                
                # Add to required beneficiary types
                if not is_neg:
                    beneficiary_enum = self._map_beneficiary_value(cond_value)
                    if beneficiary_enum and beneficiary_enum not in profile.required_beneficiary_types:
                        profile.required_beneficiary_types.append(beneficiary_enum)
    
    def _extract_property_conditions(self, text: str, field_name: str, profile: SchemeSemanticProfile):
        """Extract property/asset ownership requirements."""
        text_lower = text.lower()
        
        for pattern, cond_type, cond_value in self.patterns.PROPERTY_PATTERNS:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                source_text = self._extract_context(text, match.start(), match.end())
                
                if cond_type == "land_ownership":
                    profile.requires_land_ownership = True
                elif cond_type == "bank_account":
                    profile.requires_bank_account = True
                elif cond_type == "aadhar":
                    profile.requires_aadhar = True
                
                condition = SemanticCondition(
                    condition_type=cond_type,
                    condition_value=cond_value,
                    source_text=source_text,
                    source_field=field_name,
                    confidence=0.92,
                    is_mandatory=True,
                )
                profile.conditions.append(condition)
    
    def _extract_age_constraints(self, text: str, field_name: str, profile: SchemeSemanticProfile):
        """Extract semantic age constraints (e.g., '18-40 years young professionals')."""
        # Look for age range patterns
        age_patterns = [
            r"(\d+)\s*[-–]\s*(\d+)\s+years?",
            r"(?:aged?|age)\s+(\d+)\s*[-–]\s*(\d+)",
            r"between\s+(\d+)\s+and\s+(\d+)\s+years?",
        ]

        for pattern in age_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                age1, age2 = int(match.group(1)), int(match.group(2))
                min_age, max_age = min(age1, age2), max(age1, age2)

                source_text = self._extract_context(text, match.start(), match.end())

                if not profile.age_constraints:
                    profile.age_constraints = f"{min_age}-{max_age} years"
                    profile.age_min = min_age
                    profile.age_max = max_age

                    condition = SemanticCondition(
                        condition_type="age_range",
                        condition_value=f"{min_age}-{max_age}",
                        source_text=source_text,
                        source_field=field_name,
                        confidence=0.90,
                        is_mandatory=True,
                    )
                    profile.conditions.append(condition)

    def _extract_income_constraints(self, text: str, field_name: str, profile: SchemeSemanticProfile):
        """Extract income limit requirements (e.g., 'income below 2 lakhs')."""
        income_patterns = [
            r"income\s+(?:of\s+)?(?:rs\.?|rupees?)\s*([\d,]+)(?:\s*[-–]\s*(?:rs\.?|rupees?)\s*([\d,]+))?",
            r"(?:annual|monthly)\s+income\s+(?:of\s+)?(?:rs\.?|rupees?)\s*([\d,]+)",
        ]

        for pattern in income_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extract numeric income value
                income_str = match.group(1).replace(",", "")
                try:
                    income_val = int(income_str)

                    # Determine period (annual/monthly)
                    period = "annual"
                    if "monthly" in text[match.start():match.start()+50].lower():
                        period = "monthly"

                    # Convert monthly to annual for consistency
                    if period == "monthly":
                        income_val = income_val * 12

                    # Check if max income already set, keep lower
                    if profile.income_max is None or income_val < profile.income_max:
                        profile.income_max = income_val
                        profile.income_max_period = period

                        source_text = self._extract_context(text, match.start(), match.end())

                        condition = SemanticCondition(
                            condition_type="income_limit",
                            condition_value=f"{match.group(1)} {period}",
                            source_text=source_text,
                            source_field=field_name,
                            confidence=0.85,
                            is_mandatory=True,
                        )
                        profile.conditions.append(condition)
                except ValueError:
                    pass

    def _extract_residence_constraints(self, text: str, field_name: str, profile: SchemeSemanticProfile):
        """Extract residence/region requirements (e.g., 'resident of Gujarat')."""
        residence_patterns = [
            r"\bresident[s]?\s+of\s+([A-Za-z\s]+?)(?:\.|,|;|$)",
            r"\bdomicile\s+of\s+([A-Za-z\s]+?)(?:\.|,|;|$)",
            r"\bnative\s+of\s+([A-Za-z\s]+?)(?:\.|,|;|$)",
        ]

        for pattern in residence_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                region = match.group(1).strip()
                # Clean up trailing words
                region = re.sub(r"\s+(?:state|district|province)$", "", region, flags=re.IGNORECASE)

                if region and not profile.required_residence:
                    profile.required_residence = region

                    source_text = self._extract_context(text, match.start(), match.end())

                    condition = SemanticCondition(
                        condition_type="residence",
                        condition_value=region,
                        source_text=source_text,
                        source_field=field_name,
                        confidence=0.88,
                        is_mandatory=True,
                    )
                    profile.conditions.append(condition)
    
    @staticmethod
    def _extract_context(text: str, start: int, end: int, context_chars: int = 50) -> str:
        """Extract sentence context around a match."""
        # Find sentence boundaries
        sent_start = max(0, text.rfind(".", max(0, start - context_chars)))
        sent_end = min(len(text), text.find(".", end + context_chars))
        
        if sent_end == -1:
            sent_end = len(text)
        
        context = text[sent_start:sent_end].strip()
        # Clean up
        context = context.replace("\n", " ").replace("  ", " ")
        return context[:150]  # Limit to 150 chars
    
    @staticmethod
    def _is_negated(text: str, position: int, context_chars: int = 30) -> bool:
        """Check if a match position is in negated context (both backward and forward)."""
        # Check backward context
        context_start = max(0, position - context_chars)
        backward_context = text[context_start:position].lower()

        # Check forward context
        context_end = min(len(text), position + context_chars)
        forward_context = text[position:context_end].lower()

        negation_words = ["not", "non", "except", "excluding", "cannot", "no ", "none"]

        # Check for negation in backward context (e.g., "not for students")
        if any(word in backward_context for word in negation_words):
            return True

        # Check for negation in forward context (e.g., "students not eligible")
        # Look for negation words immediately after the match position
        for word in negation_words:
            if word in forward_context[:15]:  # Check first 15 chars after match
                return True

        return False
    
    @staticmethod
    def _map_education_value(value: str) -> Optional[EducationLevel]:
        """Map extracted education value to enum."""
        mappings = {
            "class_level": EducationLevel.CLASS_VIII,
            "graduate": EducationLevel.GRADUATE,
            "education_level": EducationLevel.CLASS_X,
            "specific_class": EducationLevel.CLASS_VIII,
        }
        return mappings.get(value)
    
    @staticmethod
    def _map_occupation_value(value: str) -> Optional[OccupationType]:
        """Map extracted occupation to enum."""
        return OccupationType[value.upper()] if value.upper() in OccupationType.__members__ else None
    
    @staticmethod
    def _map_economic_value(value: str) -> Optional[EconomicStatus]:
        """Map extracted economic status to enum."""
        return EconomicStatus[value.upper()] if value.upper() in EconomicStatus.__members__ else None
    
    @staticmethod
    def _map_beneficiary_value(value: str) -> Optional[BeneficiaryType]:
        """Map extracted beneficiary type to enum."""
        value_clean = value.upper().replace(" ", "_").replace("-", "_")

        # Special mappings
        if value_clean == "SENIOR_CITIZEN":
            return BeneficiaryType.SENIOR_CITIZEN
        elif value_clean == "STUDENT":
            return BeneficiaryType.STUDENT
        elif value_clean in BeneficiaryType.__members__:
            return BeneficiaryType[value_clean]

        return None

    @staticmethod
    def _parse_income_limit(condition_value: str) -> Optional[int]:
        """Parse income limit from condition value string."""
        # Extract number from e.g., "1,00,000 annual"
        import re
        numbers = re.findall(r"[\d,]+", condition_value)
        if numbers:
            num_str = numbers[0].replace(",", "")
            try:
                return int(num_str)
            except ValueError:
                return None
        return None
