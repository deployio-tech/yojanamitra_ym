"""
pipeline/extractor.py
Gemini-powered condition extraction from raw scheme text.
Returns structured conditions[] with field, operator, value, confidence.
Production-grade with multi-pass extraction, self-check, and safety filters.
"""

import json
import logging
import re
import time
log = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Extract eligibility conditions from scheme text as JSON array.

Example output format: [{"field": "age", "operator": "gte", "value": 18, "condition_type": "hard", "confidence": 0.9}]

Fields: age, gender, category, annual_income, education_level, is_student, state
Operators: gte, lte, eq, in, boolean

Skip: "all", "any", "open to all"
Convert: "lakh" to number (5 lakh = 500000)

Input: {scheme_text}

Output: JSON only."""

# Extended field normalization map
FIELD_NORMALIZATION = {
    "is_teacher": "occupation",
    "teacher": "occupation",
    "professor": "occupation",
    "faculty": "occupation",
    "employed": "employment_status",
    "employee": "employment_status",
    "profession": "occupation",
    "annual family income": "annual_income",
    "family income": "annual_income",
    "household income": "annual_income",
    "yearly income": "annual_income",
    "income": "annual_income",
    "age limit": "age",
    "maximum age": "age",
    "minimum age": "age",
    "caste": "category",
    "caste category": "category",
    "social category": "category",
    "belongs to sc": "category",
    "belongs to st": "category",
    "belongs to sc/st": "category",
    "scheduled caste": "category",
    "scheduled tribe": "category",
    "other backward class": "category",
    "economically weaker section": "category",
    "sex": "gender",
    "woman": "gender",
    "women only": "gender",
    "male only": "gender",
    "student": "is_student",
    "enrolled student": "is_student",
    "farmer": "is_farmer",
    "agriculturist": "is_farmer",
    "kisan": "is_farmer",
    "fisherman": "is_fisherman",
    "fisher": "is_fisherman",
    "domicile": "has_domicile",
    "aadhaar": "has_aadhaar",
    "bank account": "has_bank_account",
    "bpl card": "is_bpl",
    "bpl": "is_bpl",
    "disability": "is_disabled",
    "pwd": "is_disabled",
    "differently abled": "is_disabled",
    "transgender": "is_transgender",
    "widow": "is_widow",
    "construction worker": "is_construction_worker",
    "marginal farmer": "is_marginal_farmer",
    "self employed": "is_self_employed",
    "minority": "is_minority",
    "urban": "is_urban",
    "rural": "is_rural",
    "qualification": "education_level",
    "educational qualification": "education_level",
    "minimum qualification": "education_level",
}

QUALITY_FIELDS = [
    "age", "annual_income", "category", "state", "gender",
    "is_student", "is_farmer", "education_level", "occupation",
    "is_bpl", "is_disabled", "is_widow", "is_fisherman",
]
# Canonical field name normalisation map
FIELD_MAP = {
    "annual family income":        "annual_income",
    "family income":               "annual_income",
    "household income":            "annual_income",
    "yearly income":               "annual_income",
    "age limit":                   "age",
    "maximum age":                 "age",
    "minimum age":                 "age",
    "caste":                       "category",
    "caste category":              "category",
    "social category":             "category",
    "belongs to sc":               "category",
    "belongs to st":               "category",
    "belongs to sc/st":            "category",
    "scheduled caste":             "category",
    "scheduled tribe":             "category",
    "other backward class":        "category",
    "economically weaker section": "category",
    "sex":                         "gender",
    "woman":                       "gender",
    "women only":                  "gender",
    "male only":                   "gender",
    "student":                     "is_student",
    "enrolled student":            "is_student",
    "farmer":                      "is_farmer",
    "agriculturist":               "is_farmer",
    "kisan":                       "is_farmer",
    "fisherman":                   "is_fisherman",
    "fisher":                      "is_fisherman",
    "domicile":                    "has_domicile",
    "aadhaar":                     "has_aadhaar",
    "bank account":                "has_bank_account",
    "bpl card":                    "is_bpl",
    "bpl":                         "is_bpl",
    "disability":                  "is_disabled",
    "pwd":                         "is_disabled",
    "differently abled":           "is_disabled",
    "transgender":                 "is_transgender",
    "widow":                       "is_widow",
    "construction worker":         "is_construction_worker",
    "marginal farmer":             "is_marginal_farmer",
    "self employed":               "is_self_employed",
    "minority":                    "is_minority",
    "urban":                       "is_urban",
    "rural":                       "is_rural",
    "qualification":               "education_level",
    "educational qualification":   "education_level",
    "minimum qualification":       "education_level",
}
def normalise_field(raw_field: str) -> str:
    key = raw_field.lower().strip()
    return FIELD_MAP.get(key, key.replace(" ", "_"))
def compute_quality_score(conditions: list, raw_text: str) -> float:
    """
    Compute 0.0–1.0 quality score for extracted conditions.
    """
    if not conditions:
        return 0.0
    # 1. Condition count score (more = better, cap at 10)
    count_score = min(len(conditions) / 10, 1.0)
    # 2. Average AI confidence
    avg_conf = sum(c.get("confidence", 0.5) for c in conditions) / len(conditions)
    # 3. Has at least one hard condition
    has_hard = any(c.get("condition_type") == "hard" for c in conditions)
    hard_bonus = 0.20 if has_hard else 0.0
    # 4. Field coverage (how many canonical quality fields covered)
    covered = set(normalise_field(c.get("field", "")) for c in conditions)
    coverage = len(covered & set(QUALITY_FIELDS)) / len(QUALITY_FIELDS)
    score = (count_score * 0.25 + avg_conf * 0.40 + coverage * 0.35) + hard_bonus
    return round(min(score, 1.0), 3)
def detect_expiry(raw_text: str):
    """
    Try to extract an expiry/deadline date from raw scheme text.
    Returns datetime.date or None.
    """
    from datetime import date
    import re
    # Common patterns: "31 March 2025", "31/03/2025", "2025-03-31"
    patterns = [
        r"\b(\d{1,2})[\/\-\s](\d{1,2})[\/\-\s](20\d{2})\b",
        r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August"
        r"|September|October|November|December)[,\s]+(20\d{2})\b",
    ]
    month_map = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
    }
    # Look for deadline keywords first
    deadline_ctx = re.findall(
        r"(?:deadline|last date|closing date|valid till|expires?|ends?\s+on)[^.]{0,60}",
        raw_text, re.IGNORECASE
    )
    search_text = " ".join(deadline_ctx) if deadline_ctx else raw_text[:500]
    for pat in patterns:
        m = re.search(pat, search_text, re.IGNORECASE)
        if m:
            try:
                groups = m.groups()
                if len(groups) == 3:
                    if groups[1].isdigit():
                        day, mon, yr = int(groups[0]), int(groups[1]), int(groups[2])
                    else:
                        day = int(groups[0])
                        mon = month_map.get(groups[1].lower(), 0)
                        yr  = int(groups[2])
                    if 1 <= mon <= 12 and 1 <= day <= 31 and yr >= 2020:
                        return date(yr, mon, day)
            except Exception:
                pass
    return None
def detect_duplicates(scheme, all_schemes, threshold: float = 0.88) -> list:
    """
    Simple TF-IDF / keyword overlap duplicate detection.
    Returns list of (scheme_id, similarity_score) for potential duplicates.
    Falls back gracefully if sklearn not available.
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
    except ImportError:
        return []
    if not all_schemes or len(all_schemes) < 2:
        return []
    texts = [s.name + " " + (s.ministry or "") + " " + (s.raw_text or "")[:300]
             for s in all_schemes]
    scheme_text = scheme.name + " " + (scheme.ministry or "") + " " + (scheme.raw_text or "")[:300]
    try:
        all_texts = [scheme_text] + texts
        vect = TfidfVectorizer(max_features=500, stop_words="english")
        matrix = vect.fit_transform(all_texts)
        sims = cosine_similarity(matrix[0:1], matrix[1:])[0]
        results = []
        for i, sim in enumerate(sims):
            if sim >= threshold and all_schemes[i].id != scheme.id:
                results.append((all_schemes[i].id, round(float(sim), 3)))
        return sorted(results, key=lambda x: -x[1])
    except Exception as e:
        log.warning(f"Duplicate detection error: {e}")
        return []
class GeminiExtractor:
    """Production-grade Gemini-powered condition extraction."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-flash-latest"):
        self.api_key = api_key
        self.model_name = model_name
        self._model = None
    
    def _get_model(self):
        if self._model is None:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(self.model_name)
        return self._model
    
    def _clean_json(self, text: str) -> list:
        """Clean and parse JSON from Gemini response."""
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("```json").strip("```")
        return json.loads(text)
    
    # -----------------------------
    # PASS 1: MAX EXTRACTION
    # -----------------------------
    def _extract_pass(self, text: str) -> list:
        """Pass 1: Strict extraction of all conditions."""
        prompt = """
You are a STRICT scheme condition extraction engine.

MISSION: Extract ALL eligibility conditions with ZERO tolerance for missing fields.

═══════════════════════════════════════════════════════════════════════════════
COMPLETE FIELD WHITELIST (41 FIELDS):
age, gender, category, occupation, religion, marital_status, num_daughters, residence_type,
state, residence, is_rural, is_urban, state_residency,
annual_income, income, family_income, is_bpl, has_income_cert,
education_level, is_student, is_school_dropout, is_first_gen_student,
occupation, is_farmer, is_industrial_worker, is_construction_worker, is_self_employed, is_pensioner, loan_default_history,
has_aadhaar, has_bank_account, has_ration_card, has_pucca_house, is_citizen,
is_disabled, disability_percentage, is_widow, is_orphan, is_landless, is_tribal, is_minority,
land_ownership_size, has_vending_certificate

VALID OPERATORS: gte, lte, gt, lt, eq, neq, one_of, not_one_of, exists, not_exists

CRITICAL RULES:
1. ONLY use whitelist fields - if not in list, skip or map to closest
2. Extract IMPLICIT: "women only"→gender=female, "farmers"→is_farmer=true
3. Negative conditions MUST: "not if income > X"→lte
4. Age limits extract BOTH min AND max as separate conditions
5. Compound split into atomic conditions
6. HARD: blocking (age,income,category,occupation,residence), SOFT: scoring (education)

OUTPUT: JSON array only
[
  {"field": "age", "operator": "gte", "value": 18, "condition_type": "hard", "source_fragment": "..."}
]

TEXT:
""" + text
        try:
            res = self._get_model().generate_content(prompt)
            return self._clean_json(res.text)
        except Exception as e:
            log.error(f"Pass 1 extraction failed: {e}")
            return []
    
    # -----------------------------
    # PASS 2: SELF-CHECK (MISSED CONDITIONS)
    # -----------------------------
    def _self_check_pass(self, text: str, existing_conditions: list) -> list:
        """Pass 2: Self-check for missed conditions."""
        prompt = f"""
STRICT SELF-CHECK: Find ALL missing conditions.

Look for:
1. Age requirements (min/max)
2. Income limits (upper/lower)
3. Gender requirements
4. Category/caste requirements (SC/ST/OBC/General)
5. Occupation (farmer/worker/student/professional)
6. Location (state/rural/urban)
7. Education level
8. Vulnerable groups (BPL/disabled/widow/orphan/landless)
9. Documents (aadhaar/bank/ration/income cert)
10. Negative conditions ("not eligible if...")

Existing:
{json.dumps(existing_conditions, indent=2)}

TEXT:
{text}

OUTPUT: JSON array of NEW conditions only. If none, return [].
"""
        try:
            res = self._get_model().generate_content(prompt)
            return self._clean_json(res.text)
        except Exception as e:
            log.error(f"Pass 2 self-check failed: {e}")
            return []
    
    # -----------------------------
    # FIELD NORMALIZATION
    # -----------------------------
    def _normalize_fields(self, conditions: list) -> list:
        """Normalize field names to canonical forms."""
        for c in conditions:
            field = c.get("field", "").lower().strip()
            c["field"] = FIELD_NORMALIZATION.get(field, field.replace(" ", "_"))
        return conditions
    
    # -----------------------------
    # OPERATOR NORMALIZATION
    # -----------------------------
    def _normalize_operators(self, conditions: list) -> list:
        """Normalize operators to supported format."""
        op_map = {
            '==': 'eq',
            '=': 'eq',
            '>=': 'gte',
            '>': 'gt',
            '<=': 'lte',
            '<': 'lt',
            '!=': 'neq',
            'one_of': 'in',
            'not_one_of': 'not_in',
        }
        for c in conditions:
            op = c.get("operator", "eq")
            c["operator"] = op_map.get(op, op)
        return conditions
    
    # -----------------------------
    # DEDUPLICATION
    # -----------------------------
    def _deduplicate(self, conditions: list) -> list:
        """Remove duplicate conditions."""
        seen = set()
        final = []
        for c in conditions:
            key = (c.get("field"), c.get("operator"), str(c.get("value")))
            if key not in seen:
                seen.add(key)
                final.append(c)
        return final
    
    # -----------------------------
    # TITLE AUGMENTATION
    # -----------------------------
    def _augment_from_title(self, scheme: dict, conditions: list) -> list:
        """Add conditions inferred from scheme title."""
        name = (scheme.get("name") or "").lower()
        
        def add(field, value):
            conditions.append({
                "field": field,
                "operator": "eq",
                "value": value,
                "condition_type": "hard",
                "answerable": True,
                "confidence": 0.9,
                "source_fragment": "title_inference"
            })
        
        # Multi-trigger patterns
        if "women" in name and "entrepreneur" in name:
            add("gender", "female")
            add("occupation", "entrepreneur")
        elif "women" in name:
            add("gender", "female")
        
        if "student" in name and "scholarship" in name:
            add("is_student", True)
        elif "student" in name:
            add("is_student", True)
        
        if "farmer" in name:
            add("is_farmer", True)
        
        if any(x in name for x in ["worker", "labour", "labor"]):
            add("is_industrial_worker", True)
        
        if any(x in name for x in ["faculty", "teacher", "professor"]):
            add("occupation", "faculty")
        
        if "sc" in name or "st" in name or "obc" in name:
            if "sc" in name:
                add("category", "SC")
            elif "st" in name:
                add("category", "ST")
            elif "obc" in name:
                add("category", "OBC")
        
        if "bpl" in name:
            add("is_bpl", True)
        
        if "rural" in name:
            add("is_rural", True)
        elif "urban" in name:
            add("is_urban", True)
        
        return conditions
    
    # -----------------------------
    # SAFETY FILTER
    # -----------------------------
    def is_low_confidence(self, conditions: list) -> bool:
        """Check if conditions are too few/weak (safety filter)."""
        hard = [c for c in conditions if c.get("condition_type") == "hard"]
        
        # Too few hard conditions
        if len(hard) < 2:
            return True
        
        # Missing diversity of fields
        fields = set(c.get("field") for c in hard)
        if len(fields) < 2:
            return True
        
        return False
    
    # -----------------------------
    # MAIN EXTRACT
    # -----------------------------
    def extract(self, raw_text: str, scheme: dict = None, retry: bool = True) -> tuple:
        """
        Production-grade extraction.
        Returns (conditions_list, extraction_version, error_str|None, low_confidence_flag)
        """
        if not self.api_key:
            return [], self.model_name, "No API key", True
        
        try:
            # PASS 1: Max extraction
            base = self._extract_pass(raw_text)
            
            # PASS 2: Self-check
            missing = self._self_check_pass(raw_text, base)
            
            # MERGE
            combined = base + missing
            
            # NORMALIZE FIELDS
            combined = self._normalize_fields(combined)
            
            # NORMALIZE OPERATORS
            combined = self._normalize_operators(combined)
            
            # DEDUP
            combined = self._deduplicate(combined)
            
            # TITLE AUGMENTATION
            if scheme:
                combined = self._augment_from_title(scheme, combined)
            
            # SAFETY CHECK
            low_conf = self.is_low_confidence(combined)
            
            return combined, "v3_high_recall", None, low_conf
            
        except Exception as e:
            log.error(f"Extraction failed: {e}")
            return [], "v3_high_recall", str(e), True
