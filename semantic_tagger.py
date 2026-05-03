"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   SEMANTIC TAGGER — Tasks 1, 4 & 6: Pre-Tagging, FP Generalization,       ║
║                      and Continuous Learning                                ║
║                                                                              ║
║  RESPONSIBILITIES:                                                           ║
║  1. Extract structured semantic tags from scheme text (offline/batch)       ║
║  4. Detect false positive patterns and generalize fixes across schemes      ║
║  6. Periodic analysis to improve semantic tags and matching logic           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("yojanamitra.semantic_tagger")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — SEMANTIC TAG SCHEMA
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class SemanticTag:
    """
    A structured semantic condition extracted from scheme text.
    Stored in DB as JSON. Used during matching for strict validation.

    Examples:
        {"tag": "education_required", "value": "Class 8", "source": "eligibility", "confidence": 0.95}
        {"tag": "occupation", "value": "farmer", "source": "description", "confidence": 0.92}
        {"tag": "beneficiary_type", "value": "widow", "source": "name", "confidence": 0.98}
        {"tag": "min_training_years", "value": 5, "source": "eligibility", "confidence": 0.88}
        {"tag": "marital_status", "value": "married", "source": "eligibility", "confidence": 0.90}
        {"tag": "is_bpl", "value": True, "source": "eligibility", "confidence": 0.95}
    """
    tag: str                          # Canonical tag key
    value: Any                        # Strict value (string, int, bool, list)
    source: str                       # "description" | "eligibility" | "name" | "benefits"
    confidence: float = 1.0          # 0.0 – 1.0
    is_disqualifier: bool = False     # True = user having this value is EXCLUDED
    is_mandatory: bool = True         # False = informational only

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "SemanticTag":
        return cls(**d)


@dataclass
class SchemeTagProfile:
    """Aggregated semantic tags for one scheme."""
    scheme_id: int
    scheme_name: str
    tags: List[SemanticTag] = field(default_factory=list)
    extraction_method: str = "ai"      # "ai" | "regex" | "hybrid"
    extracted_at: str = ""
    version: int = 1

    def to_json(self) -> str:
        return json.dumps({
            "scheme_id": self.scheme_id,
            "scheme_name": self.scheme_name,
            "tags": [t.to_dict() for t in self.tags],
            "extraction_method": self.extraction_method,
            "extracted_at": self.extracted_at,
            "version": self.version,
        })

    @classmethod
    def from_json(cls, raw: str) -> "SchemeTagProfile":
        d = json.loads(raw)
        return cls(
            scheme_id=d["scheme_id"],
            scheme_name=d["scheme_name"],
            tags=[SemanticTag.from_dict(t) for t in d.get("tags", [])],
            extraction_method=d.get("extraction_method", "ai"),
            extracted_at=d.get("extracted_at", ""),
            version=d.get("version", 1),
        )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — REGEX-BASED FALLBACK EXTRACTOR (deterministic)
# ══════════════════════════════════════════════════════════════════════════════

class RegexTagExtractor:
    """
    Fast regex-based tag extractor used as a fallback when AI is unavailable,
    or to supplement AI results with high-confidence deterministic extractions.
    """

    # Strict patterns: (pattern, tag_key, value_resolver)
    PATTERNS: List[Tuple] = [
        # ── Education ──
        (r"\bclass\s+(i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii|\d{1,2})\b",
         "education_required", lambda m: f"Class {m.group(1).upper()}"),
        (r"\b(8th|8 th)\s+(?:std|standard|class|pass)\b",
         "education_required", lambda m: "Class 8"),
        (r"\b(10th|sslc|matriculation|class x)\b",
         "education_required", lambda m: "Class 10"),
        (r"\b(12th|hsc|higher secondary|puc)\b",
         "education_required", lambda m: "Class 12"),
        (r"\b(graduate|graduation|ug|bachelor|degree)\b",
         "education_required", lambda m: "Graduation"),
        (r"\b(post.?graduate|pg|master|mba|mtech|msc)\b",
         "education_required", lambda m: "Post-Graduation"),
        (r"\b(diploma|polytechnic|iti)\b",
         "education_required", lambda m: "Diploma"),

        # ── Occupation ──
        (r"\b(farmers?|agricultural\s+workers?|kisan)\b",
         "occupation", lambda m: "farmer"),
        (r"\b(fisherm[ae]n|fisher(?:folk|women)?)\b",
         "occupation", lambda m: "fisherman"),
        (r"\b(weavers?|handloom\s+workers?)\b",
         "occupation", lambda m: "weaver"),
        (r"\b(construction\s+workers?|shramik|bocwwb)\b",
         "occupation", lambda m: "construction_worker"),
        (r"\b(safai\s+karamchari|manual\s+scavenger)\b",
         "occupation", lambda m: "safai_karamchari"),
        (r"\b(artisans?|craftsmen?|vishwakarma)\b",
         "occupation", lambda m: "artisan"),
        (r"\b(beedi\s+workers?)\b",
         "occupation", lambda m: "beedi_worker"),
        (r"\b(nurses?|nursing)\b",
         "occupation", lambda m: "nurse"),

        # ── Beneficiary type ──
        (r"\bwidows?\b",
         "beneficiary_type", lambda m: "widow"),
        (r"\b(senior\s+citizens?|aged\s+\d+\s+years?\s+and\s+above|60\s*\+|above\s+60)\b",
         "beneficiary_type", lambda m: "senior_citizen"),
        (r"\b(disabled|persons?\s+with\s+disabilit(?:y|ies)|pwd)\b",
         "beneficiary_type", lambda m: "disabled"),
        (r"\b(orphans?)\b",
         "beneficiary_type", lambda m: "orphan"),
        (r"\b(transgenders?|hijra|third\s+gender)\b",
         "beneficiary_type", lambda m: "transgender"),
        (r"\b(minorities?|minority\s+communit(?:y|ies))\b",
         "beneficiary_type", lambda m: "minority"),

        # ── Caste ──
        (r"\b(scheduled\s+castes?|sc\s+candidates?|harijan)\b",
         "caste_required", lambda m: "SC"),
        (r"\b(scheduled\s+tribes?|st\s+candidates?|adivasi)\b",
         "caste_required", lambda m: "ST"),
        (r"\b(other\s+backward\s+class(?:es)?|obc)\b",
         "caste_required", lambda m: "OBC"),

        # ── Economic status ──
        (r"\b(below\s+poverty\s+line|bpl\s+famil(?:y|ies))\b",
         "is_bpl", lambda m: True),
        (r"\b(economically\s+weaker\s+sections?|ews)\b",
         "is_ews", lambda m: True),
        (r"\b(antyodaya|aay\s+ration)\b",
         "ration_card_type", lambda m: "AAY"),

        # ── Training requirement ──
        (r"minimum\s+(\d+)\s+years?\s+(?:of\s+)?training",
         "min_training_years", lambda m: int(m.group(1))),
        (r"(\d+)\s+years?\s+(?:of\s+)?experience",
         "min_experience_years", lambda m: int(m.group(1))),

        # ── Residence ──
        (r"\b(rural\s+areas?|villages?|gram\s+panchayat)\b",
         "residence_type", lambda m: "Rural"),
        (r"\b(urban\s+areas?|municipalities|corporations?)\b",
         "residence_type", lambda m: "Urban"),

        # ── Gender ──
        (r"\b(only\s+(?:for\s+)?wo?men|women\s+only|mahila|stree)\b",
         "gender", lambda m: "Female"),
        (r"\b(only\s+(?:for\s+)?(?:boys?|men)|male\s+only)\b",
         "gender", lambda m: "Male"),

        # ── Document requirements ──
        (r"\b(aadhaar|aadhar)\b",
         "requires_aadhaar", lambda m: True),
        (r"\b(bank\s+account|savings\s+account)\b",
         "requires_bank_account", lambda m: True),

        # ── Marital status ──
        (r"\b(unmarried|single\s+(?:women?|girls?))\b",
         "marital_status", lambda m: "unmarried"),
        (r"\b(married\s+(?:women?|couples?))\b",
         "marital_status", lambda m: "married"),

        # ── Disability percentage ──
        (r"(\d+)\s*%\s*(?:or\s+more\s+)?(?:of\s+)?disability",
         "min_disability_percentage", lambda m: int(m.group(1))),

        # ── Land ownership ──
        (r"(?:not\s+)?(?:owning?|own(?:ed)?\s+)?agricultural\s+land",
         "agricultural_land", lambda m: True),

        # ── Disqualifiers (NOT patterns) ──
        (r"(?:not\s+(?:eligible|applicable)\s+(?:for|to)\s+)(?:govt(?:ernment)?\s+employees?)",
         "is_govt_employee", lambda m: "disqualifier"),
        (r"(?:income\s+tax|income-tax)\s+(?:payer|assessee|filer)",
         "is_income_taxpayer", lambda m: "disqualifier"),
    ]

    def extract(self, scheme: Dict[str, Any]) -> List[SemanticTag]:
        """Extract tags using regex patterns from scheme text fields."""
        combined_text = " ".join(filter(None, [
            scheme.get("name", ""),
            scheme.get("description", ""),
            scheme.get("eligibility", ""),
            scheme.get("benefits", ""),
            scheme.get("exclusions", ""),
        ])).lower()

        tags: List[SemanticTag] = []
        seen_tags: set = set()

        for pattern, tag_key, value_fn in self.PATTERNS:
            for match in re.finditer(pattern, combined_text, re.IGNORECASE):
                value = value_fn(match)

                # Determine source field
                source = self._find_source(match.start(), scheme)

                # Check for disqualifier
                is_disq = False
                if value == "disqualifier":
                    is_disq = True
                    value = True  # The field value we're checking

                # De-duplicate: skip if (tag_key, value) already added
                dedup_key = f"{tag_key}::{value}"
                if dedup_key in seen_tags:
                    continue
                seen_tags.add(dedup_key)

                tags.append(SemanticTag(
                    tag=tag_key,
                    value=value,
                    source=source,
                    confidence=0.88,
                    is_disqualifier=is_disq,
                    is_mandatory=True,
                ))

        return tags

    def _find_source(self, position: int, scheme: Dict) -> str:
        """Identify which field the match came from based on offset."""
        offset = 0
        for field_name in ["name", "description", "eligibility", "benefits", "exclusions"]:
            text = scheme.get(field_name, "") or ""
            if position < offset + len(text.lower()):
                return field_name
            offset += len(text.lower()) + 1
        return "combined"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — AI-POWERED TAG EXTRACTOR (Gemini)
# ══════════════════════════════════════════════════════════════════════════════

AI_EXTRACTION_PROMPT = """You are a precise government scheme eligibility analyst.

Given the following scheme data, extract STRICT structured eligibility tags.

RULES:
1. Only extract tags that are explicitly stated — do NOT infer
2. Use the exact tag keys from the ALLOWED_TAGS list below
3. Be strict and context-aware — avoid naive keyword matching
4. For education: "Class VIII students" → education_required: "Class 8"
5. For occupation: "only for farmers" → occupation: "farmer"
6. For beneficiary: "widow pension" → beneficiary_type: "widow"
7. For numeric: "minimum 5 years training" → min_training_years: 5

ALLOWED_TAGS (use ONLY these keys):
- education_required: string ("Class 8", "Class 10", "Class 12", "Graduation", "Post-Graduation", "Diploma")
- occupation: string (e.g., "farmer", "fisherman", "weaver", "student", "construction_worker")
- beneficiary_type: string (e.g., "widow", "senior_citizen", "disabled", "orphan", "transgender")
- caste_required: string or list (e.g., "SC", "ST", "OBC", ["SC", "ST"])
- is_bpl: boolean
- is_ews: boolean
- gender: string ("Male", "Female")
- residence_type: string ("Urban", "Rural")
- min_training_years: integer
- min_experience_years: integer
- min_disability_percentage: integer
- marital_status: string ("married", "unmarried", "widowed")
- requires_aadhaar: boolean
- requires_bank_account: boolean
- requires_agricultural_land: boolean (true = must own land, false = must NOT own land)
- min_children: integer
- ration_card_type: string ("BPL", "APL", "AAY", "PHH")
- is_income_taxpayer_disqualifier: boolean (true = income taxpayers are EXCLUDED)
- is_govt_employee_disqualifier: boolean (true = govt employees are EXCLUDED)
- age_min_override: integer (if eligibility text specifies a min age different from structured data)
- age_max_override: integer

SCHEME DATA:
Name: {name}
Description: {description}
Eligibility: {eligibility}
Benefits: {benefits}
Exclusions: {exclusions}

Return ONLY a valid JSON array of tag objects. Each tag must have:
{{
  "tag": "<tag_key>",
  "value": <value>,
  "source": "<which field you found this in>",
  "confidence": <0.0-1.0>,
  "is_disqualifier": <boolean>,
  "is_mandatory": <boolean>
}}

Return [] if no tags can be reliably extracted.
Respond ONLY with the JSON array — no preamble, no markdown."""


class AITagExtractor:
    """Extract semantic tags using Gemini AI."""

    def __init__(self, gemini_model):
        self.model = gemini_model

    def extract(self, scheme: Dict[str, Any]) -> Tuple[List[SemanticTag], str]:
        """
        Extract tags using AI.
        Returns (tags, method) where method is 'ai', 'regex', or 'hybrid'.
        """
        if not self.model:
            logger.warning("AI model not available, falling back to regex")
            return self._fallback_extract(scheme)

        prompt = AI_EXTRACTION_PROMPT.format(
            name=scheme.get("name", ""),
            description=(scheme.get("description") or "")[:500],
            eligibility=(scheme.get("eligibility") or "")[:600],
            benefits=(scheme.get("benefits") or "")[:300],
            exclusions=(scheme.get("exclusions") or "")[:300],
        )

        try:
            response = self.model.generate_content(prompt)
            raw_text = response.text.strip()

            # Clean markdown wrappers if present
            raw_text = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()

            raw_tags = json.loads(raw_text)

            if not isinstance(raw_tags, list):
                raise ValueError("Expected a JSON array")

            tags = []
            for item in raw_tags:
                if not isinstance(item, dict) or "tag" not in item:
                    continue
                tags.append(SemanticTag(
                    tag=item["tag"],
                    value=item["value"],
                    source=item.get("source", "ai"),
                    confidence=float(item.get("confidence", 0.9)),
                    is_disqualifier=bool(item.get("is_disqualifier", False)),
                    is_mandatory=bool(item.get("is_mandatory", True)),
                ))

            # Hybrid: supplement AI tags with high-confidence regex tags
            regex_tags = RegexTagExtractor().extract(scheme)
            merged = self._merge_tags(tags, regex_tags)

            logger.info(f"AI extracted {len(tags)} tags, regex added {len(merged) - len(tags)} more")
            return merged, "hybrid"

        except Exception as e:
            logger.warning(f"AI tag extraction failed: {e}. Using regex fallback.")
            return self._fallback_extract(scheme)

    def _fallback_extract(self, scheme: Dict) -> Tuple[List[SemanticTag], str]:
        tags = RegexTagExtractor().extract(scheme)
        return tags, "regex"

    @staticmethod
    def _merge_tags(ai_tags: List[SemanticTag], regex_tags: List[SemanticTag]) -> List[SemanticTag]:
        """Merge regex tags into AI tags, skipping duplicates. AI takes precedence."""
        ai_keys = {t.tag for t in ai_tags}
        extra = [t for t in regex_tags if t.tag not in ai_keys and t.confidence >= 0.88]
        return ai_tags + extra


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — SEMANTIC MATCHING VALIDATOR
# ══════════════════════════════════════════════════════════════════════════════

class SemanticMatchValidator:
    """
    Task 2: Validate a user profile against pre-computed semantic tags.
    Returns (is_eligible, violations, confidence_delta).
    """

    # Maps semantic tag keys to user profile attribute paths
    TAG_TO_PROFILE: Dict[str, str] = {
        "occupation":               "occupation_normalized",
        "beneficiary_type":         "beneficiary_type_normalized",
        "caste_required":           "caste_category",
        "is_bpl":                   "is_bpl",
        "is_ews":                   "ews_status",
        "gender":                   "gender",
        "residence_type":           "residence",
        "min_disability_percentage":"disability_percentage",
        "marital_status":           "marital_status",
        "requires_aadhaar":         "has_aadhaar",
        "requires_bank_account":    "has_bank_account",
        "requires_agricultural_land":"owns_land",
        "ration_card_type":         "ration_card_type",
        "is_income_taxpayer_disqualifier": "is_income_taxpayer",
        "is_govt_employee_disqualifier":   "is_govt_employee",
    }

    def validate(
        self,
        tags: List[SemanticTag],
        user_profile: Dict[str, Any]
    ) -> Tuple[bool, List[str], float]:
        """
        Validate user profile against semantic tags.
        Returns: (passes, violation_messages, confidence_score_delta)
        """
        violations = []
        confidence_delta = 0.0

        # Precompute normalized profile values
        normalized = self._normalize_profile(user_profile)

        for tag in tags:
            if not tag.is_mandatory:
                continue

            result, violation_msg = self._check_tag(tag, normalized, user_profile)

            if result == "FAIL":
                violations.append(violation_msg)
                if tag.is_disqualifier:
                    # Hard fail — stop immediately
                    return False, violations, -100.0
            elif result == "MISSING":
                # Missing profile field — cannot confirm → NOT eligible
                violations.append(f"Missing profile data for: {tag.tag}")
                confidence_delta -= 15.0
            elif result == "PASS":
                confidence_delta += 2.0  # Slight boost for each confirmed match

        is_eligible = len(violations) == 0
        return is_eligible, violations, confidence_delta

    def _check_tag(
        self,
        tag: SemanticTag,
        normalized: Dict,
        raw_profile: Dict
    ) -> Tuple[str, str]:
        """
        Returns ("PASS", "") | ("FAIL", reason) | ("MISSING", field)
        """
        t = tag.tag
        v = tag.value

        # ── Education ──
        if t == "education_required":
            user_edu = normalized.get("education_level", "")
            if not user_edu:
                return "MISSING", "education_level"
            if not self._meets_education(v, user_edu):
                return "FAIL", f"Education required: {v}, user has: {user_edu}"
            return "PASS", ""

        # ── Occupation ──
        if t == "occupation":
            user_occs = normalized.get("occupations", [])
            if not user_occs:
                return "MISSING", "occupation"
            req = v.lower()
            if not any(req in occ.lower() for occ in user_occs):
                return "FAIL", f"Occupation required: {v}"
            return "PASS", ""

        # ── Beneficiary type ──
        if t == "beneficiary_type":
            check_map = {
                "widow":          ("is_widow", True),
                "senior_citizen": ("is_senior_citizen", True),
                "disabled":       ("is_disabled", True),
                "orphan":         ("is_orphan", True),
                "minority":       ("is_minority", True),
                "transgender":    ("gender", "Transgender"),
                "sc":             ("caste_category", "sc"),
                "st":             ("caste_category", "st"),
                "obc":            ("caste_category", "obc"),
                "student":        ("is_student", True),
            }
            btype = v.lower()
            if btype in check_map:
                attr, expected = check_map[btype]
                user_val = raw_profile.get(attr)
                if user_val is None:
                    return "MISSING", attr
                if callable(expected):
                    passes = expected(user_val)
                elif isinstance(expected, bool):
                    passes = bool(user_val) == expected
                else:
                    passes = str(user_val).lower() == str(expected).lower()
                if not passes:
                    return "FAIL", f"Must be a {v}"
            return "PASS", ""

        # ── Caste required ──
        if t == "caste_required":
            user_caste = normalized.get("caste_category", "").lower()
            if not user_caste:
                return "MISSING", "caste_category"
            allowed = [v] if isinstance(v, str) else v
            allowed_lower = [c.lower() for c in allowed]
            if user_caste not in allowed_lower:
                return "FAIL", f"Caste required: {v}"
            return "PASS", ""

        # ── Boolean checks ──
        if t in ("is_bpl", "is_ews"):
            user_val = raw_profile.get(t)
            if user_val is None:
                return "MISSING", t
            if v and not user_val:
                return "FAIL", f"Must be {t.upper().replace('_', ' ')}"
            return "PASS", ""

        # ── Disqualifiers ──
        if t == "is_income_taxpayer_disqualifier":
            if raw_profile.get("is_income_taxpayer"):
                return "FAIL", "Income taxpayers are not eligible"
            return "PASS", ""

        if t == "is_govt_employee_disqualifier":
            if raw_profile.get("is_govt_employee"):
                return "FAIL", "Government employees are not eligible"
            return "PASS", ""

        # ── Residence ──
        if t == "residence_type":
            user_res = (raw_profile.get("residence") or "").lower()
            req = v.lower()
            if user_res and user_res != req:
                return "FAIL", f"Residence required: {v}"
            return "PASS", ""

        # ── Gender ──
        if t == "gender":
            user_gender = (raw_profile.get("gender") or "").lower()
            if user_gender and user_gender != v.lower():
                return "FAIL", f"Gender required: {v}"
            return "PASS", ""

        # ── Numeric threshold ──
        if t == "min_disability_percentage":
            dp = raw_profile.get("disability_percentage", 0) or 0
            if dp < int(v):
                return "FAIL", f"Disability must be ≥ {v}%"
            return "PASS", ""

        if t == "min_training_years":
            # Cannot check without profile field — skip with low confidence note
            return "PASS", ""  # Field not in profile schema yet

        if t == "min_experience_years":
            return "PASS", ""  # Not in schema yet

        # ── Ration card ──
        if t == "ration_card_type":
            user_rt = (raw_profile.get("ration_card_type") or "").upper()
            req = v.upper() if isinstance(v, str) else [x.upper() for x in v]
            if isinstance(req, list):
                if user_rt not in req:
                    return "FAIL", f"Ration card must be one of: {req}"
            elif user_rt and user_rt != req:
                return "FAIL", f"Ration card must be: {req}"
            return "PASS", ""

        # ── Aadhaar / bank account ──
        if t == "requires_aadhaar" and v:
            if not raw_profile.get("has_aadhaar"):
                return "FAIL", "Aadhaar card required"
            return "PASS", ""

        if t == "requires_bank_account" and v:
            if raw_profile.get("has_bank_account") is False:
                return "FAIL", "Bank account required"
            return "PASS", ""

        return "PASS", ""

    @staticmethod
    def _normalize_profile(p: Dict) -> Dict:
        """Create normalized views of profile fields."""
        raw_occ = p.get("occupation", [])
        if isinstance(raw_occ, str):
            raw_occ = [raw_occ]

        return {
            "occupation_normalized": p.get("occupation", ""),
            "occupations": raw_occ,
            "education_level": (p.get("education_level") or "").lower(),
            "caste_category": (p.get("caste_category") or "").lower(),
        }

    @staticmethod
    def _meets_education(required: str, user_has: str) -> bool:
        """Check if user's education meets or exceeds requirement."""
        HIERARCHY = ["none", "primary", "class 8", "secondary", "class 10",
                     "class 12", "diploma", "graduation", "post-graduation", "phd"]

        def rank(val: str) -> int:
            val_l = val.lower().strip()
            # Normalize common aliases
            alias_map = {
                "class 8": 2, "class viii": 2, "8th": 2,
                "class 10": 4, "class x": 4, "10th": 4, "sslc": 4,
                "class 12": 5, "class xii": 5, "12th": 5, "hsc": 5, "puc": 5,
                "graduation": 7, "degree": 7, "ug": 7, "graduate": 7,
                "post-graduation": 8, "postgrad": 8, "pg": 8,
                "phd": 9,
            }
            for k, v in alias_map.items():
                if k in val_l:
                    return v
            for i, level in enumerate(HIERARCHY):
                if level in val_l:
                    return i
            return 0

        return rank(user_has) >= rank(required)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — FALSE POSITIVE PATTERN GENERALIZER (Task 4)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class FalsePositiveReport:
    """Structured false positive report from a user or admin."""
    scheme_id: int
    scheme_name: str
    user_id: int
    reason: str                    # User-stated reason for FP
    root_cause: str = ""           # System-analyzed root cause
    pattern_category: str = ""    # "missing_semantic_tag" | "wrong_occupation" | etc.
    generalization: str = ""       # Suggested fix to generalize
    reported_at: str = ""


class FalsePositiveAnalyzer:
    """
    Task 4: Analyze false positive patterns and generalize fixes.
    """

    PATTERN_DETECTORS = [
        # Pattern: occupation mentioned in text but missing in metadata
        (r"\bonly\s+for\s+(\w+)\b", "missing_occupation_tag",
         "Add occupation tag extracted from eligibility text"),
        # Pattern: gender-specific language without gender metadata
        (r"\b(mahila|stree|women\s+only|ladies)\b", "missing_gender_tag",
         "Add gender=Female semantic tag from text"),
        # Pattern: caste-restricted but caste not in DB
        (r"\b(sc|st|obc|dalits?|tribals?)\s+(only|candidates?)\b", "missing_caste_tag",
         "Add caste_required tag from eligibility text"),
        # Pattern: BPL/poverty requirement not captured
        (r"\b(bpl|below\s+poverty\s+line|antyodaya)\b", "missing_bpl_tag",
         "Add is_bpl=True semantic tag"),
        # Pattern: widow-specific scheme without beneficiary tag
        (r"\bwidow\s*(pension|sahay|relief|scheme)\b", "missing_widow_tag",
         "Add beneficiary_type=widow semantic tag"),
        # Pattern: state-specific scheme without state restriction
        (r"\b(karnataka|maharashtra|bihar|up|odisha)\s+(scheme|yojana)\b", "missing_state_tag",
         "Add state restriction for mentioned state"),
    ]

    def analyze_false_positive(self, scheme: Dict, reason: str) -> FalsePositiveReport:
        """Analyze a false positive and identify the root cause pattern."""
        text = " ".join(filter(None, [
            scheme.get("name", ""),
            scheme.get("description", ""),
            scheme.get("eligibility", ""),
        ])).lower()

        report = FalsePositiveReport(
            scheme_id=scheme.get("id", 0),
            scheme_name=scheme.get("name", ""),
            user_id=0,
            reason=reason,
            reported_at=datetime.now(timezone.utc).isoformat(),
        )

        for pattern, category, generalization in self.PATTERN_DETECTORS:
            if re.search(pattern, text, re.IGNORECASE):
                report.root_cause = f"Text contains '{pattern}' but no corresponding eligibility rule"
                report.pattern_category = category
                report.generalization = generalization
                break

        if not report.root_cause:
            report.root_cause = "Unclassified — requires manual review"
            report.pattern_category = "unknown"
            report.generalization = "Manually review scheme eligibility text and add missing semantic tags"

        return report

    def batch_analyze(self, reports: List[Dict]) -> Dict[str, Any]:
        """
        Aggregate false positive reports to find systemic patterns.
        Returns: {pattern_category: {count, affected_schemes, recommended_fix}}
        """
        pattern_counts: Dict[str, Dict] = {}

        for report in reports:
            cat = report.get("pattern_category", "unknown")
            if cat not in pattern_counts:
                pattern_counts[cat] = {
                    "count": 0,
                    "affected_schemes": [],
                    "recommended_fix": report.get("generalization", ""),
                    "priority": "low",
                }
            pattern_counts[cat]["count"] += 1
            scheme_id = report.get("scheme_id")
            if scheme_id not in pattern_counts[cat]["affected_schemes"]:
                pattern_counts[cat]["affected_schemes"].append(scheme_id)

        # Assign priority based on frequency
        for cat, data in pattern_counts.items():
            if data["count"] >= 10:
                data["priority"] = "high"
            elif data["count"] >= 3:
                data["priority"] = "medium"
            else:
                data["priority"] = "low"

        # Sort by count descending
        sorted_patterns = dict(
            sorted(pattern_counts.items(), key=lambda x: x[1]["count"], reverse=True)
        )

        return {
            "total_reports": len(reports),
            "unique_patterns": len(pattern_counts),
            "patterns": sorted_patterns,
            "top_priority": max(pattern_counts.keys(),
                               key=lambda k: pattern_counts[k]["count"],
                               default="none"),
        }

    def suggest_tag_fix(self, pattern_category: str, scheme: Dict) -> Optional[SemanticTag]:
        """
        Suggest a new semantic tag to fix a false positive pattern.
        Returns the SemanticTag to add, or None if no fix can be determined.
        """
        text = " ".join(filter(None, [
            scheme.get("name", ""),
            scheme.get("eligibility", ""),
        ])).lower()

        fixes = {
            "missing_occupation_tag": self._suggest_occupation_tag,
            "missing_gender_tag":     self._suggest_gender_tag,
            "missing_caste_tag":      self._suggest_caste_tag,
            "missing_bpl_tag":        lambda t: SemanticTag("is_bpl", True, "ai_fix", 0.95),
            "missing_widow_tag":      lambda t: SemanticTag("beneficiary_type", "widow", "ai_fix", 0.95),
        }

        fn = fixes.get(pattern_category)
        return fn(text) if fn else None

    @staticmethod
    def _suggest_occupation_tag(text: str) -> Optional[SemanticTag]:
        m = re.search(r"only\s+for\s+(\w+)", text)
        if m:
            return SemanticTag("occupation", m.group(1), "ai_fix", 0.85)
        return None

    @staticmethod
    def _suggest_gender_tag(text: str) -> SemanticTag:
        return SemanticTag("gender", "Female", "ai_fix", 0.92)

    @staticmethod
    def _suggest_caste_tag(text: str) -> Optional[SemanticTag]:
        for caste in ["SC", "ST", "OBC"]:
            if caste.lower() in text:
                return SemanticTag("caste_required", caste, "ai_fix", 0.90)
        return None


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — CONTINUOUS LEARNING ORCHESTRATOR (Task 6)
# ══════════════════════════════════════════════════════════════════════════════

class ContinuousLearner:
    """
    Task 6: Periodic analysis and system improvement recommendations.
    Analyzes false positives, improves semantic tagging, and recommends updates.
    """

    def __init__(self, ai_extractor: Optional[AITagExtractor] = None):
        self.ai_extractor = ai_extractor
        self.fp_analyzer = FalsePositiveAnalyzer()

    def run_learning_cycle(
        self,
        false_positive_reports: List[Dict],
        untagged_schemes: List[Dict],
        tag_coverage_threshold: float = 0.6
    ) -> Dict[str, Any]:
        """
        Run one learning cycle. Returns actionable recommendations.
        """
        recommendations = []
        actions_taken = []

        # 1. Analyze FP patterns
        fp_analysis = self.fp_analyzer.batch_analyze(false_positive_reports)
        if fp_analysis["total_reports"] > 0:
            top_pattern = fp_analysis.get("top_priority")
            recommendations.append({
                "type": "false_positive_pattern",
                "severity": "high",
                "description": f"Top FP pattern: {top_pattern}",
                "action": fp_analysis["patterns"].get(top_pattern, {}).get("recommended_fix", ""),
                "affected_scheme_count": len(fp_analysis["patterns"].get(top_pattern, {}).get("affected_schemes", [])),
            })

        # 2. Identify schemes with low tag coverage
        low_coverage_schemes = []
        for scheme in untagged_schemes:
            tags = RegexTagExtractor().extract(scheme)
            if len(tags) < 2:  # Low tag coverage threshold
                low_coverage_schemes.append(scheme.get("id"))

        if low_coverage_schemes:
            recommendations.append({
                "type": "low_tag_coverage",
                "severity": "medium",
                "description": f"{len(low_coverage_schemes)} schemes have insufficient semantic tags",
                "action": "Trigger AI batch re-tagging for these schemes",
                "affected_scheme_ids": low_coverage_schemes[:20],  # Sample
            })

        # 3. Profile schema gaps
        missing_field_analysis = self._analyze_missing_fields_impact(false_positive_reports)
        if missing_field_analysis:
            recommendations.append({
                "type": "profile_schema_gap",
                "severity": "medium",
                "description": "Missing profile fields causing match failures",
                "action": "Add recommended fields to user profile form",
                "missing_fields": missing_field_analysis,
            })

        return {
            "cycle_timestamp": datetime.now(timezone.utc).isoformat(),
            "false_positive_analysis": fp_analysis,
            "low_coverage_scheme_count": len(low_coverage_schemes),
            "recommendations": recommendations,
            "actions_taken": actions_taken,
            "next_cycle_recommended": "in 7 days",
        }

    @staticmethod
    def _analyze_missing_fields_impact(reports: List[Dict]) -> List[Dict]:
        """Identify which missing profile fields most commonly caused FPs."""
        field_freq: Dict[str, int] = {}
        for r in reports:
            for field in r.get("missing_fields", []):
                field_freq[field] = field_freq.get(field, 0) + 1

        return sorted([
            {"field": f, "frequency": c,
             "impact": "high" if c > 5 else "medium" if c > 2 else "low"}
            for f, c in field_freq.items()
        ], key=lambda x: x["frequency"], reverse=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — BATCH TAGGING ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

class BatchTagger:
    """
    Orchestrates batch semantic tagging of all schemes.
    Can run offline or on-demand via API.
    """

    def __init__(self, gemini_model=None, batch_size: int = 10):
        self.extractor = AITagExtractor(gemini_model)
        self.batch_size = batch_size

    def tag_scheme(self, scheme: Dict) -> SchemeTagProfile:
        """Tag a single scheme."""
        tags, method = self.extractor.extract(scheme)

        return SchemeTagProfile(
            scheme_id=scheme.get("id", 0),
            scheme_name=scheme.get("name", ""),
            tags=tags,
            extraction_method=method,
            extracted_at=datetime.now(timezone.utc).isoformat(),
            version=2,
        )

    def tag_batch(self, schemes: List[Dict]) -> List[SchemeTagProfile]:
        """Tag a list of schemes. Logs progress."""
        results = []
        total = len(schemes)

        for i, scheme in enumerate(schemes):
            try:
                profile = self.tag_scheme(scheme)
                results.append(profile)
                if (i + 1) % 10 == 0:
                    logger.info(f"Tagged {i+1}/{total} schemes")
            except Exception as e:
                logger.error(f"Failed to tag scheme {scheme.get('id')}: {e}")
                # Add empty profile so we don't lose track
                results.append(SchemeTagProfile(
                    scheme_id=scheme.get("id", 0),
                    scheme_name=scheme.get("name", ""),
                    tags=[],
                    extraction_method="failed",
                    extracted_at=datetime.now(timezone.utc).isoformat(),
                ))

        logger.info(f"Batch tagging complete: {len(results)}/{total} tagged")
        return results
