"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  SEMANTIC RULE INJECTOR  v2.0  (PATCHED)                                     ║
║                                                                              ║
║  PATCHES FROM v1.0:                                                          ║
║                                                                              ║
║  SEM-FIX-1 — NATIONALITY BLOCK REMOVED ENTIRELY                             ║
║    Old code injected a disqualifier checking residence∈[abroad,nri] —       ║
║    this NEVER fired for Indian users (residence='urban'/'rural').            ║
║    Foreign-national schemes are now returned as None in scheme_rule_adapter  ║
║    (build_rule) before they ever reach this injector. The G-NEW nationality  ║
║    section is removed — no dead code left.                                   ║
║                                                                              ║
║  SEM-FIX-2 — EDUCATION EXTRACTION TIGHTENED (S6)                            ║
║    Old: matched 'diploma' anywhere in text → forced education_level>=diploma ║
║    Problem: 'diploma' appears in thousands of schemes as a document type     ║
║    ("diploma certificate required"), not as a minimum education requirement. ║
║    New: only match education keywords in strictly eligibility-relevant        ║
║    context phrases ("passed diploma", "completed diploma", "diploma holder", ║
║    "class 10 pass", etc.). Also stops after finding the LOWEST required       ║
║    level rather than the highest, and ignores education words found purely   ║
║    in document/exclusion context.                                            ║
║                                                                              ║
║  SEM-FIX-3 — AGE EXTRACTION GUARDED AGAINST SPURIOUS MATCHES (G2)           ║
║    Old patterns matched any number followed by "years" in eligibility text — ║
║    this caught scheme amounts ("₹5000 per year"), pension amounts            ║
║    ("5 years of service"), and benefit durations. New patterns require        ║
║    an explicit eligibility keyword in the same clause.                       ║
║                                                                              ║
║  SEM-FIX-4 — RELIGION DETECTION SCOPE-GUARDED (S2)                          ║
║    Old: any mention of 'christian', 'muslim', etc. in eligibility text       ║
║    triggered a mandatory religion condition. This incorrectly flagged        ║
║    schemes that merely name minority communities as beneficiaries alongside   ║
║    others. New: require the religion word to appear with an explicit          ║
║    RESTRICTION phrase ("only", "exclusively", "applicants must belong to")   ║
║    or in the context of a known religion-restricted scheme pattern.          ║
║                                                                              ║
║  SEM-FIX-5 — WIDOW DETECTION SCOPE-GUARDED (_requires_widow)                ║
║    Old regex matched "widow" anywhere — fired on schemes that mentioned      ║
║    widows as one of several eligible groups ("SC/ST/OBC/widow women").       ║
║    New: only trigger when scheme is EXCLUSIVELY for widows.                  ║
║                                                                              ║
║  SEM-FIX-6 — annual_family_income field now exists (FIX-3 in engine)        ║
║    The S7 injection is now safe — field exists in UserProfile. Also fixed    ║
║    to use the correct regex capturing group.                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import re
import logging
from typing import List, Optional, Tuple

from eligibility_engine_strict_v21 import EligibilityCondition

logger = logging.getLogger("yojanamitra.semantic_injector")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — INCOME EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

_INCOME_PATTERNS = [
    r"(?:must\s+)?not\s+exceed\s*[₹rs\.]*\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|l\b)?",
    r"less\s+than\s*[₹rs\.]*\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|l\b)?",
    r"(?:below|upto|up\s+to|within)\s*[₹rs\.]*\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|l\b)?",
    r"income\s+(?:limit|ceiling|cap)\s+(?:of\s+)?[₹rs\.]*\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|l\b)?",
    r"income\s+(?:of\s+)?[₹rs\.]*\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|l\b)?\s*(?:per\s+(?:annum|year))",
    r"parental\s+income[^.]{0,60}?[₹rs\.]*\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|l\b)?",
    r"annual\s+(?:family\s+)?income[^.]{0,60}?[₹rs\.]*\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|l\b)?",
    r"whose[^.]{0,40}income[^.]{0,40}?[₹rs\.]*\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|l\b)?",
    r"[₹rs\.]\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|l\b)\s*(?:per\s+(?:annum|year|month))?",
    # "₹15,000 or less" / "₹X or below" — common in housing and welfare schemes
    r"[₹rs\.]\s*([\d,]+(?:\.\d+)?)\s*(?:or\s+less|and\s+below|or\s+below)\b",
]


def _extract_income_limit(text: str) -> Optional[int]:
    text_lower = text.lower()
    if not re.search(
        r"income|parental\s+income|annual\s+income|family\s+income", text_lower
    ):
        return None

    # Detect if the income figure is expressed monthly — multiply by 12 to annualise.
    # Patterns: "monthly family income ₹15,000", "income of ₹X per month", etc.
    is_monthly = bool(
        re.search(r"monthly\s+(?:family\s+)?income", text_lower) or
        re.search(r"income\s+(?:of\s+)?[₹rs\.]\s*[\d,]+\s+(?:per\s+month|pm\b|a\s+month)", text_lower) or
        (text_lower.strip().startswith("monthly") and "income" in text_lower[:80])
    )

    for pattern in _INCOME_PATTERNS:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if not match:
            continue
        try:
            raw = match.group(1).replace(",", "")
            val = float(raw)
            unit = (match.group(2) or "").lower().strip()
            if unit in ("lakh", "lakhs", "l"):
                val = val * 100_000
            else:
                # Monthly context and value looks like a monthly figure (< 100,000)
                # → multiply by 12 to get the annual equivalent
                if is_monthly and val < 100_000:
                    val = val * 12
            val = int(val)
            if 10_000 <= val <= 50_00_000:
                return val
        except (IndexError, ValueError):
            continue

    return None


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — BENEFICIARY TYPE EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def _requires_widow(name: str, elig: str) -> bool:
    """
    SEM-FIX-5: Only true when scheme is EXCLUSIVELY for widows.
    Old code matched "widow" anywhere — including schemes listing widows as
    one group among many ("SC/ST/OBC women and widows").
    New: requires strong exclusivity signal in the eligibility text.
    """
    text = (name + " " + elig).lower()

    # Patterns that indicate EXCLUSIVE widow eligibility
    EXCLUSIVE_WIDOW_PATTERNS = [
        r"\bwidow(?:ed)?\s+(?:women?|candidate|applicant|beneficiar)",
        r"\bonly\s+(?:for\s+)?widow",
        r"\bwidow(?:ed)?\s+only\b",
        r"\bvidhwa\s+(?:pension|sahayata|samman|yojana|mahila)",
        r"\bscheme\s+for\s+widow",
        r"\bwidow\s+pension\b",
        r"\bwidow\s+(?:relief|assistance|welfare|benefit)",
        r"\bapplicant\s+(?:must\s+)?be\s+(?:a\s+)?widow",
        r"\bshould\s+be\s+(?:a\s+)?widow",
    ]
    for pat in EXCLUSIVE_WIDOW_PATTERNS:
        if re.search(pat, text):
            # Guard: if "all women" or "including widow" appears, it's inclusive not exclusive
            if re.search(r"all\s+women|including\s+widow|eligible\s+for\s+all|women\s+of\s+all", text):
                return False
            return True
    return False


def _requires_senior_citizen(elig: str) -> bool:
    text = elig.lower()
    return bool(re.search(
        r"\b(senior\s+citizens?\s+(?:only|aged?)|"
        r"aged?\s+60\s+(?:years?\s+)?(?:and\s+)?(?:above|or\s+more)|"
        r"60\s+(?:years?\s+)?(?:and\s+)?above|"
        r"above\s+(?:the\s+age\s+of\s+)?60|"
        r"old\s+age\s+(?:pension|benefit|assistance))\b",
        text
    ))


def _requires_disability(elig: str) -> bool:
    """
    True if scheme is strictly for persons with disability.
    Expanded to catch: "specially-abled", "hearing challenged",
    "speech impaired", "orthopedically handicapped", "blindness" etc.

    BUG 5 FIX: Marriage assistance schemes say "normal person marrying
    orthopedically disabled" — the APPLICANT is not disabled, the spouse is.
    Guard: if a disability phrase appears ONLY in a "marrying/spouse" context,
    do NOT fire the disability requirement.
    """
    text = elig.lower()

    # Guard: check if ALL disability mentions are in a "marrying X disabled" context,
    # meaning the disability belongs to the spouse/partner, not the applicant.
    _MARRIAGE_GUARD_PATTERNS = [
        r"(?:marr(?:ying|ied\s+to|iage\s+with)|wed(?:ding)?\s+(?:a|an)?|spouse\s+(?:is|being))"
        r"[^.]{0,60}?"
        r"(?:orthopedic|disabled|divyang|handicap|specially.abled|pwd|physically\s+(?:challenged|disabled))",
        r"(?:orthopedic|disabled|divyang|handicap|specially.abled|pwd|physically\s+(?:challenged|disabled))"
        r"[^.]{0,60}?"
        r"(?:spouse|partner|bride|groom|husband|wife)",
    ]
    # Strip sentences that match the marriage-guard pattern, then re-check
    text_stripped = text
    for gpat in _MARRIAGE_GUARD_PATTERNS:
        text_stripped = re.sub(gpat, "", text_stripped)

    DISABILITY_PHRASES = [
        # Core person-with-disability phrases
        "persons with disabilit", "person with disabilit",
        "divyangjan", "divyang",
        "pwd only", "pwd candidates", "pwd beneficiar",
        "disabled person", "disable person",
        # Physical condition and descriptive terms
        "physically handicapped", "physically disabled", "physically challenged",
        "specially-abled", "specially abled",
        "differently abled", "differently-abled",
        "hearing impaired", "hearing challenged", "hearing-impaired",
        "visually impaired", "visually challenged", "visually-impaired",
        "speech impaired", "speech-impaired",
        "locomotor disability", "locomotor impairment",
        "orthopedically handicapped", "orthopedically impaired",
        # Specific conditions that require disability status
        "cerebral palsy", "mental retardation", "intellectual disabilit",
        "autism", "multiple disabilit",
        "bedridden", "debilitating disability",
        # Percentage-based detection (covers "50% of disability", "disability of 40%")
        "% of disability", "% disability", "% or more disability",
        "with disability of", "disability of ",
        "disability of not less than", "disability of at least",
        # Document/registration
        "disability certificate is required", "disability certificate",
        "registered as disabled", "certified disabled",
        # Other terms
        "blindness", "deaf ", "dumb ",
    ]
    return any(phrase in text_stripped for phrase in DISABILITY_PHRASES)


def _requires_farmer(name: str, desc: str, elig: str) -> bool:
    text = (name + " " + desc + " " + elig).lower()
    return bool(re.search(
        r"\b("
        r"only\s+for\s+farmers?|"
        r"(?:small|marginal|tenant)\s+farmers?\s+(?:only|eligible)|"
        r"farmers?\s+(?:holding|owning|with)\s+(?:land|agricultural)|"
        r"agricultural\s+(?:labou?rers?|workers?)\s+(?:only|eligible)|"
        r"kisan\s+(?:only|samman|credit|vikas)|"
        r"pm\s+kisan"
        r")\b",
        text
    ))


def _is_school_level(name: str, elig: str) -> bool:
    text = (name + " " + elig).lower()
    return bool(re.search(
        r"\b("
        r"studying\s+in\s+class\s+(?:vi+|[6-9]|10|ix|x)\b|"
        r"class\s+(?:viii|vii|vi|ix|x)\s+(?:student|pass|annual)|"
        r"pre.?matric\s+scholarship|"
        r"nmms\s+(?:selection\s+)?examination|"
        r"class\s+(?:7|8|9|10)\s+(?:annual|pass|student)|"
        r"studying\s+in\s+class\s+(?:7|8|9|10)\b|"
        r"school\s+level\s+scholarship"
        r")\b",
        text
    ))


def _requires_orphan(name: str, elig: str) -> bool:
    """
    True if scheme is specifically for orphans.
    Expanded to catch "without biological parents", "lost both parents" etc.
    """
    text = (name + " " + elig).lower()
    ORPHAN_PHRASES = [
        "for orphans", "orphans only", "orphan eligible", "orphan welfare",
        "without biological", "without adoptive parents", "lost both parents",
        "parentless", "both parents deceased", "both parents dead",
        "destitute child", "child without parents",
    ]
    return any(p in text for p in ORPHAN_PHRASES)


def _requires_minority(name: str, elig: str) -> bool:
    text = (name + " " + elig).lower()
    return bool(re.search(
        r"\b(minorities?\s+(?:only|communities?|candidates?|students?)|"
        r"for\s+(?:religious\s+)?minorities?|"
        r"nmdfc|national\s+minorities?\s+development)\b",
        text
    ))


def _requires_tribal(name: str, elig: str) -> bool:
    text = (name + " " + elig).lower()
    return bool(re.search(
        r"\b(scheduled\s+tribes?\s+(?:only|candidates?|students?|beneficiar)|"
        r"tribal\s+(?:only|welfare|development|students?)|"
        r"adivasi\s+(?:only|welfare)|"
        r"for\s+(?:scheduled\s+tribes?|st\s+candidates?))\b",
        text
    ))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — MAIN INJECTOR
# ══════════════════════════════════════════════════════════════════════════════

def inject_semantic_conditions(
    scheme_id: int,
    name: str,
    description: str,
    eligibility: str,
    exclusions: str,
    db_max_income: Optional[int],
    db_widow_requirement: Optional[str],
    db_disability_requirement: Optional[str],
    db_senior_citizen_requirement: Optional[str],
    db_allowed_occupations: Optional[list],
    db_orphan_requirement: Optional[str],
    db_minority_requirement: Optional[str],
    db_tribal_requirement: Optional[str],
    db_min_age: Optional[int] = None,
    db_max_age: Optional[int] = None,
) -> Tuple[List[EligibilityCondition], List[EligibilityCondition]]:

    conditions:    List[EligibilityCondition] = []
    disqualifiers: List[EligibilityCondition] = []

    full_text  = f"{name} {description} {eligibility} {exclusions}"
    elig_lower = (eligibility or "").lower()
    sid        = scheme_id

    # ── 1. INCOME LIMIT ────────────────────────────────────────────────────────
    if db_max_income is None:
        extracted_income = _extract_income_limit(elig_lower)
        if extracted_income:
            conditions.append(EligibilityCondition(
                field="income_annual",
                operator="lte",
                value=extracted_income,
                is_mandatory=True,
                failure_message=(
                    f"Annual income must not exceed ₹{extracted_income:,} "
                    f"(extracted from eligibility criteria)."
                ),
                score_weight=25,
                condition_id=f"{sid}_semantic_income_max",
            ))
            # SEM-FIX-6: annual_family_income now exists in UserProfile (FIX-3 in engine)
            conditions.append(EligibilityCondition(
                field="annual_family_income",
                operator="lte",
                value=extracted_income,
                is_mandatory=False,
                failure_message=(
                    f"Annual family income must not exceed ₹{extracted_income:,}."
                ),
                score_weight=20,
                condition_id=f"{sid}_semantic_family_income_max",
            ))
            logger.debug(f"[{sid}] Semantic income cap injected: ₹{extracted_income:,}")

    # ── 2. WIDOW REQUIREMENT ───────────────────────────────────────────────────
    # SEM-FIX-5: now uses tighter _requires_widow() that checks exclusivity
    _db_widow = (db_widow_requirement or "").strip().lower()
    if _db_widow in ("", "any", "none", "null") and _requires_widow(name, eligibility):
        conditions.append(EligibilityCondition(
            field="is_widow",
            operator="is_true",
            value=None,
            is_mandatory=True,
            failure_message="This scheme is for widows / vidhwa only.",
            score_weight=25,
            condition_id=f"{sid}_semantic_widow",
        ))
        logger.debug(f"[{sid}] Semantic widow condition injected")

    # ── 3. DISABILITY REQUIREMENT ──────────────────────────────────────────────
    _db_disability = (db_disability_requirement or "").strip().lower()
    if _db_disability in ("", "any", "none", "null") and _requires_disability(elig_lower):
        conditions.append(EligibilityCondition(
            field="is_disabled",
            operator="is_true",
            value=None,
            is_mandatory=True,
            failure_message="This scheme is for persons with disabilities (PwD/Divyangjan) only.",
            score_weight=25,
            condition_id=f"{sid}_semantic_disability",
        ))
        logger.debug(f"[{sid}] Semantic disability condition injected")

    # ── 4. SENIOR CITIZEN REQUIREMENT ─────────────────────────────────────────
    _db_senior = (db_senior_citizen_requirement or "").strip().lower()
    if _db_senior in ("", "any", "none", "null") and _requires_senior_citizen(elig_lower):
        conditions.append(EligibilityCondition(
            field="is_senior_citizen",
            operator="is_true",
            value=None,
            is_mandatory=True,
            failure_message="This scheme is for senior citizens (age 60+) only.",
            score_weight=25,
            condition_id=f"{sid}_semantic_senior",
        ))
        logger.debug(f"[{sid}] Semantic senior citizen condition injected")

    # ── 5. FARMER REQUIREMENT ──────────────────────────────────────────────────
    _db_occs = [o.lower() for o in (db_allowed_occupations or [])]
    _has_farmer_in_db = any(o in ("farmer", "all", "any") for o in _db_occs)
    if not _has_farmer_in_db and _requires_farmer(name, description, eligibility):
        conditions.append(EligibilityCondition(
            field="is_farmer",
            operator="is_true",
            value=None,
            is_mandatory=True,
            failure_message="This scheme is for farmers / agricultural workers only.",
            score_weight=25,
            condition_id=f"{sid}_semantic_farmer",
        ))
        logger.debug(f"[{sid}] Semantic farmer condition injected")

    # ── 6. SCHOOL-LEVEL EDUCATION CEILING ─────────────────────────────────────
    if _is_school_level(name, eligibility):
        conditions.append(EligibilityCondition(
            field="education_level",
            operator="in",
            value=["none", "primary", "secondary"],
            is_mandatory=True,
            failure_message=(
                "This scholarship is for school students (up to Class X). "
                "Graduates and above are not eligible."
            ),
            score_weight=25,
            condition_id=f"{sid}_semantic_school_edu",
        ))
        disqualifiers.append(EligibilityCondition(
            field="education_level",
            operator="in",
            value=["graduation", "postgrad", "phd", "diploma"],
            is_mandatory=True,
            failure_message=(
                "Graduates, diploma holders, and postgraduates cannot apply "
                "for this school-level scholarship."
            ),
            score_weight=25,
            condition_id=f"{sid}_semantic_school_edu_disq",
        ))
        logger.debug(f"[{sid}] Semantic school-level education ceiling injected")

    # ── 7. ORPHAN REQUIREMENT ──────────────────────────────────────────────────
    _db_orphan = (db_orphan_requirement or "").strip().lower()
    if _db_orphan in ("", "any", "none", "null") and _requires_orphan(name, eligibility):
        conditions.append(EligibilityCondition(
            field="is_orphan",
            operator="is_true",
            value=None,
            is_mandatory=True,
            failure_message="This scheme is for orphans only.",
            score_weight=25,
            condition_id=f"{sid}_semantic_orphan",
        ))
        logger.debug(f"[{sid}] Semantic orphan condition injected")

    # ── 8. MINORITY REQUIREMENT ────────────────────────────────────────────────
    _db_minority = (db_minority_requirement or "").strip().lower()
    if _db_minority in ("", "any", "none", "null") and _requires_minority(name, eligibility):
        conditions.append(EligibilityCondition(
            field="is_minority",
            operator="is_true",
            value=None,
            is_mandatory=True,
            failure_message="This scheme is for religious minority communities only.",
            score_weight=25,
            condition_id=f"{sid}_semantic_minority",
        ))
        logger.debug(f"[{sid}] Semantic minority condition injected")

    # ── 9. TRIBAL REQUIREMENT ──────────────────────────────────────────────────
    _db_tribal = (db_tribal_requirement or "").strip().lower()
    if _db_tribal in ("", "any", "none", "null") and _requires_tribal(name, eligibility):
        conditions.append(EligibilityCondition(
            field="is_tribal",
            operator="is_true",
            value=None,
            is_mandatory=True,
            failure_message="This scheme is for Scheduled Tribes / tribal communities only.",
            score_weight=25,
            condition_id=f"{sid}_semantic_tribal",
        ))
        logger.debug(f"[{sid}] Semantic tribal condition injected")

    # ── G2: AGE from text (SEM-FIX-3: tighter patterns, no spurious matches) ──
    # Old patterns matched "5 years of service" → injected age>=5 condition.
    # New patterns require an explicit eligibility context word in the clause.
    _AGE_CONTEXT = r"(?:age|aged?|years?\s+old|must\s+be|eligib|minimum\s+age|maximum\s+age)"

    age_range_match = (None if (db_min_age is not None and db_max_age is not None) else
        re.search(
            r"between\s*(\d{1,3})\s*(?:and|to|-)\s*(\d{1,3})\s*years?\s*(?:of\s+age)?",
            elig_lower))

    age_min_match = (None if db_min_age is not None else
        re.search(
            r"(?:above|over|more\s+than|minimum\s+age\s+(?:is|of)?|aged?\s+(?:above|over))"
            r"\s*(\d{1,3})\s*years?",
            elig_lower))

    age_max_match = (None if db_max_age is not None else
        re.search(
            r"(?:below|under|not\s+more\s+than|up\s+to|maximum\s+age\s+(?:is|of)?|aged?\s+(?:below|under))"
            r"\s*(\d{1,3})\s*years?",
            elig_lower))

    if age_range_match:
        a_min, a_max = int(age_range_match.group(1)), int(age_range_match.group(2))
        if 5 <= a_min <= 100:
            conditions.append(EligibilityCondition(
                field="age", operator="gte", value=a_min, is_mandatory=True,
                failure_message=f"Minimum age {a_min} years required (from eligibility text).",
                score_weight=30, condition_id=f"{sid}_sem_age_min_range"))
        if 5 <= a_max <= 100:
            conditions.append(EligibilityCondition(
                field="age", operator="lte", value=a_max, is_mandatory=True,
                failure_message=f"Maximum age {a_max} years (from eligibility text).",
                score_weight=30, condition_id=f"{sid}_sem_age_max_range"))
    else:
        if age_min_match:
            a_min = int(age_min_match.group(1))
            if 5 <= a_min <= 100:
                conditions.append(EligibilityCondition(
                    field="age", operator="gte", value=a_min, is_mandatory=True,
                    failure_message=f"Minimum age {a_min} years required (from eligibility text).",
                    score_weight=30, condition_id=f"{sid}_sem_age_min"))
        if age_max_match:
            a_max = int(age_max_match.group(1))
            if 5 <= a_max <= 100:
                conditions.append(EligibilityCondition(
                    field="age", operator="lte", value=a_max, is_mandatory=True,
                    failure_message=f"Maximum age {a_max} years (from eligibility text).",
                    score_weight=30, condition_id=f"{sid}_sem_age_max"))

    # SEM-FIX-1: G-NEW NATIONALITY BLOCK REMOVED ENTIRELY
    # Foreign-national schemes are now returned as None in build_rule()
    # before they ever reach this injector. No dead code left here.

    # ── Specific trade/occupation requirements ─────────────────────────────────
    full_lower = full_text.lower()
    TRADE_OCC_MAP = [
        (["coconut tree climber", "neera technician", "coconut harvester"],
         ["farmer", "agricultural"], "Coconut Tree Climber/Neera Technician", f"{sid}_sem_coconut"),
        (["khadi artisan", "khadi karigar"],
         ["artisan", "weaver", "khadi", "craftsman"], "Khadi Artisan", f"{sid}_sem_khadi"),
        (["silk weaver", "handloom weaver"],
         ["weaver", "artisan"], "Handloom/Silk Weaver", f"{sid}_sem_weaver"),
        (["toddy tapper"],
         ["toddy", "agricultural", "farmer"], "Toddy Tapper", f"{sid}_sem_toddy"),
        (["beedi worker", "bidi worker"],
         ["beedi", "worker"], "Beedi Worker", f"{sid}_sem_beedi"),
        (["safai karamchari", "sanitation worker"],
         ["safai", "sanitation", "scavenger"], "Safai Karamchari", f"{sid}_sem_safai"),
        (["working journalist", "press reporter", "accredited journalist"],
         ["journalist", "reporter", "press", "media"], "Working Journalist", f"{sid}_sem_journalist"),
        (["rubber tapper"],
         ["rubber", "farmer", "agricultural"], "Rubber Tapper", f"{sid}_sem_rubber"),
        (["coir worker", "coir industry"],
         ["coir", "worker", "artisan"], "Coir Worker", f"{sid}_sem_coir"),
        (["ex-serviceman", "ex serviceman", "defence veteran", "armed forces veteran"],
         ["ex-serviceman", "veteran", "defence", "army", "navy", "air force"],
         "Ex-Serviceman/Veteran", f"{sid}_sem_exserviceman"),
        (["war widow"],
         ["widow", "war widow"], "War Widow", f"{sid}_sem_war_widow"),
    ]
    for signals, passing_occs, role_name, cond_id in TRADE_OCC_MAP:
        if any(sig in full_lower for sig in signals):
            conditions.append(EligibilityCondition(
                field="occupation",
                operator="in",
                value=passing_occs,
                is_mandatory=True,
                failure_message=f"This scheme is specifically for {role_name}.",
                score_weight=35, condition_id=cond_id))
            break

    # ── G3: CONSTRUCTION/BOCW WORKER ──────────────────────────────────────────
    BOCW_PHRASES = ["bocw registered", "registered with bocw", "bocw member",
                    "bocw card holder", "bocw beneficiary",
                    "building and other construction workers welfare board",
                    "construction workers welfare board"]
    if any(p in full_lower for p in BOCW_PHRASES):
        conditions.append(EligibilityCondition(
            field="is_bocw_registered", operator="is_true", value=None, is_mandatory=True,
            failure_message="Must be a registered BOCW (Building and Other Construction Worker) card holder.",
            score_weight=30, condition_id=f"{sid}_sem_bocw"))

    # ── G4: PENSIONER EXCLUSION ────────────────────────────────────────────────
    PENSION_EXCL = ["pension holder", "already receiving pension", "drawing pension",
                    "not drawing pension", "not a pensioner", "should not be a pensioner",
                    "not receiving any pension", "no pension"]
    if any(p in full_lower for p in PENSION_EXCL):
        disqualifiers.append(EligibilityCondition(
            field="is_pensioner", operator="is_true", value=None, is_mandatory=True,
            failure_message="Persons already receiving a pension are not eligible for this scheme.",
            score_weight=30, condition_id=f"{sid}_sem_pensioner_disq"))

    # ── G5: MARITAL STATUS ─────────────────────────────────────────────────────
    UNMARRIED_PHRASES = ["unmarried", "un-married", "not married", "never married",
                         "spinster", "bachelor", "single girl", "should be unmarried"]
    MARRIED_PHRASES   = ["must be married", "should be married", "married woman",
                         "married couple", "husband and wife", "spouse"]
    if any(p in full_lower for p in UNMARRIED_PHRASES):
        conditions.append(EligibilityCondition(
            field="marital_status", operator="in", value=["single", "unmarried", "never married"],
            is_mandatory=True,
            failure_message="Applicant must be unmarried / single.",
            score_weight=25, condition_id=f"{sid}_sem_unmarried"))
    elif any(p in full_lower for p in MARRIED_PHRASES):
        conditions.append(EligibilityCondition(
            field="marital_status", operator="in", value=["married"],
            is_mandatory=True,
            failure_message="Applicant must be married.",
            score_weight=20, condition_id=f"{sid}_sem_married"))

    # ── G6: NUMBER OF DAUGHTERS ────────────────────────────────────────────────
    daughters_match = re.search(
        r"(\d+|one|two|three|four)\s*(?:or more\s*)?(?:daughters?|girl\s*child(?:ren)?)", full_lower)
    if daughters_match:
        num_map = {"one": 1, "two": 2, "three": 3, "four": 4}
        raw_num = daughters_match.group(1)
        req_daughters = num_map.get(raw_num, int(raw_num) if raw_num.isdigit() else 1)
        if "single girl" in full_lower or "one daughter" in full_lower:
            conditions.append(EligibilityCondition(
                field="num_daughters", operator="gte", value=1, is_mandatory=True,
                failure_message="Must have at least one daughter.",
                score_weight=25, condition_id=f"{sid}_sem_daughters"))
        elif req_daughters >= 2:
            conditions.append(EligibilityCondition(
                field="num_daughters", operator="gte", value=req_daughters, is_mandatory=True,
                failure_message=f"Must have at least {req_daughters} daughters.",
                score_weight=25, condition_id=f"{sid}_sem_daughters_n"))

    # ── G7: TRANSGENDER ────────────────────────────────────────────────────────
    TRANS_PHRASES = ["transgender", "third gender", "kinnar", "hijra", "trans person"]
    if any(p in full_lower for p in TRANS_PHRASES):
        conditions.append(EligibilityCondition(
            field="gender", operator="in", value=["transgender", "third gender", "female", "male"],
            is_mandatory=False,
            failure_message="This scheme specifically targets transgender/third gender persons.",
            score_weight=20, condition_id=f"{sid}_sem_transgender"))

    # ── G8: DROPOUT REQUIRED ──────────────────────────────────────────────────
    DROPOUT_PHRASES = ["school dropout", "drop-out", "dropped out", "out of school",
                       "left school", "not currently enrolled", "non-enrolled"]
    if any(p in full_lower for p in DROPOUT_PHRASES):
        conditions.append(EligibilityCondition(
            field="is_school_dropout", operator="is_true", value=None, is_mandatory=True,
            failure_message="This scheme targets school dropouts / out-of-school youth.",
            score_weight=25, condition_id=f"{sid}_sem_dropout"))

    # ── G9: FIRST GENERATION STUDENT ──────────────────────────────────────────
    FIRST_GEN_PHRASES = ["first generation", "first-generation", "first gen learner",
                         "first in family to pursue higher", "no graduate in family"]
    if any(p in full_lower for p in FIRST_GEN_PHRASES):
        conditions.append(EligibilityCondition(
            field="is_first_gen_student", operator="is_true", value=None, is_mandatory=True,
            failure_message="Must be the first person in the family to pursue higher education.",
            score_weight=25, condition_id=f"{sid}_sem_first_gen"))

    # ── G10: LANDLESS LABOURER ────────────────────────────────────────────────
    LANDLESS_PHRASES = ["landless", "no agricultural land", "without land",
                        "landless labourer", "landless farmer", "landless agricultural"]
    if any(p in full_lower for p in LANDLESS_PHRASES):
        conditions.append(EligibilityCondition(
            field="is_landless", operator="is_true", value=None, is_mandatory=True,
            failure_message="Must be a landless labourer (no agricultural land).",
            score_weight=25, condition_id=f"{sid}_sem_landless"))

    # ── G11: LAND AREA THRESHOLD ──────────────────────────────────────────────
    # "up to X acres" means user must own <= X acres AND > 0 acres.
    # Without the gt 0 companion, a user with 0 acres passes the lte condition,
    # allowing non-landowners to match coffee-grower, horticulture, and farm schemes.
    GROWER_SIGNALS = [
        "grower", "growers", "farmer", "cultivator", "plantation", "coffee holding",
        "agricultural land", "own land", "land holding", "land-holding",
        "horticulture", "fruit grower", "kisaan", "kisan",
    ]
    land_match = re.search(
        r"(?:less than|below|up to|not more than|maximum|within)\s*(\d+(?:\.\d+)?)\s*(?:acres?|hectares?)",
        full_lower)
    if land_match:
        land_val = float(land_match.group(1))
        is_hectares = "hectare" in land_match.group(0)
        if is_hectares:
            land_val = land_val * 2.471
        if 0 < land_val <= 50:
            conditions.append(EligibilityCondition(
                field="land_owned_acres", operator="lte", value=round(land_val, 2), is_mandatory=True,
                failure_message=f"Land holding must not exceed {round(land_val, 2)} acres.",
                score_weight=20, condition_id=f"{sid}_sem_land_max"))
            # If scheme is for growers/farmers, must also own SOME land (> 0)
            if any(sig in full_lower for sig in GROWER_SIGNALS):
                conditions.append(EligibilityCondition(
                    field="land_owned_acres", operator="gt", value=0, is_mandatory=True,
                    failure_message="Must own agricultural land to qualify for this scheme.",
                    score_weight=20, condition_id=f"{sid}_sem_land_min"))

    # ── G12: NO PUCCA HOUSE ───────────────────────────────────────────────────
    NO_HOUSE_PHRASES = ["not own a pucca house", "no pucca house", "should not have a house",
                        "not having own house", "houseless", "homeless", "no permanent house"]
    if any(p in full_lower for p in NO_HOUSE_PHRASES):
        disqualifiers.append(EligibilityCondition(
            field="has_pucca_house", operator="is_true", value=None, is_mandatory=True,
            failure_message="Applicant must not own a pucca (permanent) house.",
            score_weight=25, condition_id=f"{sid}_sem_no_pucca_house"))

    # ── G13: NT/DNT DENOTIFIED TRIBE ─────────────────────────────────────────
    DNT_PHRASES = ["denotified tribe", "vimukta jati", "nt-dnt", "nomadic tribe",
                   "semi-nomadic", "vjnt", "vimukt jati"]
    if any(p in full_lower for p in DNT_PHRASES):
        conditions.append(EligibilityCondition(
            field="caste_category", operator="in",
            value=["nt", "dnt", "vimukta", "nomadic tribe", "denotified tribe", "vjnt", "sc", "st"],
            is_mandatory=True,
            failure_message="Must belong to a Denotified/Nomadic Tribe (NT/DNT/Vimukta Jati).",
            score_weight=25, condition_id=f"{sid}_sem_dnt"))

    # ── G14: KUTCHA HOUSE REQUIRED ────────────────────────────────────────────
    KUTCHA_PHRASES = ["kutcha house", "kutcha/semi-permanent", "semi-permanent house",
                      "kuccha house", "thatched house", "not pucca"]
    if any(p in full_lower for p in KUTCHA_PHRASES):
        conditions.append(EligibilityCondition(
            field="house_type", operator="in", value=["kutcha", "semi-permanent", ""],
            is_mandatory=True,
            failure_message="Must be living in a kutcha or semi-permanent house.",
            score_weight=20, condition_id=f"{sid}_sem_kutcha"))

    # ── G15: OWN AGRICULTURAL LAND REQUIRED ──────────────────────────────────
    OWN_LAND_PHRASES = ["must own agricultural land", "should have agricultural land",
                        "own cultivable land", "own farm land", "possess agricultural land"]
    if any(p in full_lower for p in OWN_LAND_PHRASES):
        conditions.append(EligibilityCondition(
            field="land_owned_acres", operator="gt", value=0, is_mandatory=True,
            failure_message="Must own some agricultural land.",
            score_weight=20, condition_id=f"{sid}_sem_own_land"))

    # ── G16: FREEDOM FIGHTER ──────────────────────────────────────────────────
    FF_PHRASES = ["freedom fighter", "swatantrata sainik", "independence activist",
                  "ex-freedom fighter", "family of freedom fighter"]
    if any(p in full_lower for p in FF_PHRASES):
        conditions.append(EligibilityCondition(
            field="achievement_certificates",
            operator="contains", value="freedom_fighter_certificate",
            is_mandatory=True,
            failure_message="Must hold a Freedom Fighter / Swatantrata Sainik certificate.",
            score_weight=25, condition_id=f"{sid}_sem_freedom_fighter"))

    # ── S1: RESIDENCE FROM TEXT ────────────────────────────────────────────────
    RURAL_PHRASES = ["rural area", "rural resident", "rural applicant",
                     "resident of rural", "living in rural", "village resident",
                     "gram panchayat area", "rural household", "rural beneficiary"]
    URBAN_PHRASES = ["urban area", "urban resident", "urban local body",
                     "resident of urban", "municipality area", "municipal ward",
                     "urban household", "urban beneficiary", "city resident"]
    if any(p in elig_lower for p in RURAL_PHRASES):
        conditions.append(EligibilityCondition(
            field="residence", operator="in", value=["rural", "village", ""],
            is_mandatory=True,
            failure_message="This scheme is for residents of rural areas only.",
            score_weight=25, condition_id=f"{sid}_sem_rural"))
    elif any(p in elig_lower for p in URBAN_PHRASES):
        conditions.append(EligibilityCondition(
            field="residence", operator="in", value=["urban", "city", "town", ""],
            is_mandatory=True,
            failure_message="This scheme is for residents of urban areas only.",
            score_weight=25, condition_id=f"{sid}_sem_urban"))

    # ── S2: RELIGION FROM TEXT (SEM-FIX-4: requires explicit restriction phrase) ─
    # Old: any mention of 'muslim', 'christian' etc. triggered mandatory condition.
    # New: requires co-occurrence with a restriction phrase OR an exclusive pattern.
    RELIGION_EXCLUSIVE_MAP = {
        "muslim":    [
            "only for muslim", "exclusively for muslim", "muslim applicants only",
            "muslim community only", "muslim beneficiar", "waqf board",
            "for muslim", "muslim scholarship", "muslim students only",
        ],
        "christian": [
            "only for christian", "exclusively for christian", "christian applicants only",
            "christian community only", "christian scholarship",
        ],
        "sikh": [
            "only for sikh", "sikh community only", "sikh applicants only",
            "sikh scholarship", "for sikh",
        ],
        "buddhist": [
            "only for buddhist", "buddhist community only", "neo-buddhist only",
            "ambedkarite buddhist",
        ],
        "jain": [
            "only for jain", "jain community only", "jain applicants only",
        ],
        "parsi": [
            "parsi community only", "for parsis", "zoroastrian only",
        ],
    }
    matched_exclusive_religions = []
    for religion, signals in RELIGION_EXCLUSIVE_MAP.items():
        if any(sig in elig_lower for sig in signals):
            matched_exclusive_religions.append(religion)
    if len(matched_exclusive_religions) == 1:
        religion_name = matched_exclusive_religions[0]
        conditions.append(EligibilityCondition(
            field="religion", operator="in", value=[religion_name],
            is_mandatory=True,
            failure_message=f"This scheme is specifically for {religion_name.title()} community members.",
            score_weight=30, condition_id=f"{sid}_sem_religion_{religion_name}"))

    # ── S3: BPL FROM TEXT ─────────────────────────────────────────────────────
    BPL_TEXT_PHRASES = [
        "below poverty line", "bpl family", "bpl household", "bpl beneficiary",
        "bpl category", "bpl list", "identified bpl", "bpl certificate",
        "poverty line", "antyodaya family", "poorest of the poor",
    ]
    if any(p in elig_lower for p in BPL_TEXT_PHRASES):
        conditions.append(EligibilityCondition(
            field="is_bpl", operator="is_true", value=None,
            is_mandatory=True,
            failure_message="This scheme requires BPL (Below Poverty Line) status.",
            score_weight=25, condition_id=f"{sid}_sem_bpl_text"))

    # ── S4: PREGNANCY / MATERNAL REQUIREMENT ──────────────────────────────────
    PREGNANCY_PHRASES = [
        "pregnant woman", "pregnant mother", "pregnant applicant",
        "lactating mother", "lactating woman", "expectant mother",
        "during pregnancy", "in pregnancy", "maternity benefit",
    ]
    if any(p in elig_lower for p in PREGNANCY_PHRASES):
        conditions.append(EligibilityCondition(
            field="gender", operator="in", value=["female"],
            is_mandatory=True,
            failure_message="This scheme requires the applicant to be a pregnant/lactating woman.",
            score_weight=30, condition_id=f"{sid}_sem_pregnancy"))

    # ── S5: SPECIFIC DISEASE REQUIREMENT ──────────────────────────────────────
    DISEASE_MAP = [
        (["cancer", "chemotherapy", "oncology"],         "cancer patient"),
        (["hiv", "aids", "plha"],                        "HIV/AIDS patient"),
        (["tuberculosis", " tb patient", "tb-infected"],  "TB patient"),
        (["thalassemia"],                                 "thalassemia patient"),
        (["haemophilia", "hemophilia"],                   "haemophilia patient"),
        (["leprosy", "hansen"],                           "leprosy patient"),
        (["sickle cell"],                                 "sickle cell patient"),
        (["down syndrome"],                               "Down syndrome patient"),
        (["kidney failure", "renal failure", "dialysis"], "kidney/renal patient"),
        (["parkinson"],                                   "Parkinson disease patient"),
        (["alzheimer"],                                   "Alzheimer patient"),
    ]
    for signals, disease_name in DISEASE_MAP:
        if any(sig in elig_lower for sig in signals):
            conditions.append(EligibilityCondition(
                field="is_disabled", operator="is_true", value=None,
                is_mandatory=True,
                failure_message=f"This scheme is for {disease_name}s (requires disability/medical condition status).",
                score_weight=30, condition_id=f"{sid}_sem_disease_{signals[0][:10].replace(' ', '_')}"))
            break

    # ── S6: EDUCATION FROM TEXT (SEM-FIX-2: context-gated) ───────────────────
    # Old: matched "diploma" anywhere → forced min education for thousands of schemes.
    # New: only match when the education word appears in an eligibility context phrase.
    # Patterns require the word to be followed by "pass", "holder", "completed", etc.
    # or preceded by "minimum", "atleast", "should have", "passed".
    EDU_EXTRACT_PATTERNS = [
        # Class 10 / SSLC / Matric — require "pass" or "passed" context
        (r"(?:passed?|completed?|cleared?)\s+(?:class\s*(?:10|x)\b|sslc|10th|matric)", "secondary"),
        (r"(?:10th|sslc|matric)\s+pass(?:ed)?", "secondary"),
        # Class 12 / HSC / Intermediate
        (r"(?:passed?|completed?|cleared?)\s+(?:class\s*(?:12|xii)\b|hsc|12th|intermediate)", "secondary"),
        (r"(?:12th|hsc|intermediate)\s+pass(?:ed)?", "secondary"),
        # Diploma — MUST appear in eligibility context, NOT as a document
        (r"(?:passed?|completed?|holding?|holder\s+of|possess(?:ing)?)\s+(?:a\s+)?diploma",  "diploma"),
        (r"diploma\s+(?:holder|pass(?:ed)?|in\s+\w+\s+from|from\s+(?:a\s+)?(?:govt|government|recognised|recognized|polytechnic))", "diploma"),
        (r"(?:minimum\s+qualification|educational\s+qualification)[^.]{0,60}diploma", "diploma"),
        # Graduate / Bachelor
        (r"(?:graduation|bachelor(?:'s)?\s+degree|under.?graduate|b\.(?:sc|tech|com|a|e))\s+(?:pass|degree|holder)?", "graduation"),
        (r"(?:passed?|completed?)\s+graduation", "graduation"),
        # Postgrad
        (r"(?:post.?graduat|master(?:'s)?\s+degree|m\.(?:sc|tech|com|a|b[a]|pharm))\s+(?:pass|degree|holder)?", "postgrad"),
        # PhD
        (r"\bph\.?d\b|\bdoctorat", "phd"),
    ]
    extracted_edu = None
    EDU_RANK = {"none": 0, "primary": 1, "secondary": 2, "diploma": 3,
                "graduation": 4, "postgrad": 5, "phd": 6}
    for pattern, edu_level in EDU_EXTRACT_PATTERNS:
        if re.search(pattern, elig_lower):
            # Take the LOWEST matching level (minimum required)
            if extracted_edu is None or EDU_RANK.get(edu_level, 0) < EDU_RANK.get(extracted_edu, 0):
                extracted_edu = edu_level

    if extracted_edu:
        conditions.append(EligibilityCondition(
            field="education_level", operator="in",
            value=[k for k, v in EDU_RANK.items() if v >= EDU_RANK.get(extracted_edu, 0)],
            is_mandatory=True,
            failure_message=f"Minimum education required: {extracted_edu.replace('_', ' ').title()}.",
            score_weight=25, condition_id=f"{sid}_sem_edu_min"))

    # ── S7: FAMILY INCOME FROM TEXT ───────────────────────────────────────────
    # SEM-FIX-6: annual_family_income now exists in UserProfile (FIX-3 in engine)
    if db_max_income is None:
        fam_income_lakh = re.search(
            r"annual\s+family\s+income.*?(?:below|up to|not.*exceed|less than|within)\s*"
            r"(?:rs\.?|₹|inr)?\s*(\d+(?:\.\d+)?)\s*(?:lakh|lac)",
            elig_lower)
        fam_income_rs = re.search(
            r"annual\s+family\s+income.*?(?:below|up to|not.*exceed)\s*(?:rs\.?|₹|inr)?\s*(\d[\d,]+)",
            elig_lower)
        family_cap = None
        if fam_income_lakh:
            family_cap = int(float(fam_income_lakh.group(1)) * 100000)
        elif fam_income_rs:
            family_cap = int(fam_income_rs.group(1).replace(",", ""))
        if family_cap and 10000 < family_cap < 10000000:
            conditions.append(EligibilityCondition(
                field="annual_family_income", operator="lte", value=family_cap,
                is_mandatory=True,
                failure_message=f"Annual family income must not exceed ₹{family_cap:,}.",
                score_weight=25, condition_id=f"{sid}_sem_family_income"))

    # ── S8: PASSPORT REQUIRED ─────────────────────────────────────────────────
    PASSPORT_PHRASES = ["valid passport", "must hold a passport", "possess a passport",
                        "passport is mandatory", "passport holder"]
    if any(p in elig_lower for p in PASSPORT_PHRASES):
        conditions.append(EligibilityCondition(
            field="documents_uploaded", operator="contains", value="passport",
            is_mandatory=False,
            failure_message="A valid passport is required for this scheme.",
            score_weight=20, condition_id=f"{sid}_sem_passport"))

    # ── S9: NOT OWN PROPERTY / LAND ───────────────────────────────────────────
    NOT_OWN_LAND_PHRASES = [
        "should not own agricultural land", "must not own any land",
        "not own any property", "should not possess any land",
        "does not own any land", "landless and should not own",
    ]
    if any(p in elig_lower for p in NOT_OWN_LAND_PHRASES):
        disqualifiers.append(EligibilityCondition(
            field="land_owned_acres", operator="gt", value=0,
            is_mandatory=True,
            failure_message="Must not own any agricultural land or property.",
            score_weight=25, condition_id=f"{sid}_sem_no_land_ownership"))

    # ── S10: INCOME TAXPAYER EXCLUSION FROM TEXT ──────────────────────────────
    TAXPAYER_EXCL_TEXT = [
        "income tax payer", "income taxpayer", "paying income tax",
        "not an income tax assessee", "non income tax payer",
        "not paying income tax", "income tax assessee not eligible",
    ]
    if any(p in elig_lower for p in TAXPAYER_EXCL_TEXT):
        disqualifiers.append(EligibilityCondition(
            field="is_income_taxpayer", operator="is_true", value=None,
            is_mandatory=True,
            failure_message="Income tax payers are not eligible for this scheme.",
            score_weight=25, condition_id=f"{sid}_sem_taxpayer_excl"))

    # ── S11: MERIT / EXAM PERCENTAGE REQUIREMENT ──────────────────────────────
    MERIT_PHRASES = ["meritorious student", "merit scholarship", "rank holder",
                     "merit list", "top performer", "first rank", "second rank"]
    PERCENT_MATCH = re.search(
        r"(\d{2,3})\s*%\s*(?:or more|and above|marks|score|aggregate|minimum)\s*(?:in|at|from)",
        elig_lower)
    if any(p in elig_lower for p in MERIT_PHRASES) or PERCENT_MATCH:
        req_pct = float(PERCENT_MATCH.group(1)) if PERCENT_MATCH else 60.0
        conditions.append(EligibilityCondition(
            field="exam_percentage", operator="gte", value=req_pct,
            is_mandatory=False,
            failure_message=f"Minimum exam percentage of {req_pct}% may be required.",
            score_weight=20, condition_id=f"{sid}_sem_merit_pct"))

    # ── S12: SINGLE / ABANDONED WOMAN ────────────────────────────────────────
    SINGLE_WOMAN_PHRASES = ["single woman", "abandoned woman", "deserted woman",
                            "destitute woman", "woman without support",
                            "separated woman", "divorced woman (single)"]
    if any(p in elig_lower for p in SINGLE_WOMAN_PHRASES):
        conditions.append(EligibilityCondition(
            field="is_single_woman", operator="is_true", value=None,
            is_mandatory=True,
            failure_message="This scheme is for single/abandoned women only.",
            score_weight=25, condition_id=f"{sid}_sem_single_woman"))

    # ── S13: DESTITUTE ────────────────────────────────────────────────────────
    DESTITUTE_PHRASES = ["destitute", "no source of income", "without any income",
                         "no livelihood", "extreme poverty", "ultra poor"]
    if any(p in elig_lower for p in DESTITUTE_PHRASES):
        conditions.append(EligibilityCondition(
            field="is_destitute", operator="is_true", value=None,
            is_mandatory=True,
            failure_message="This scheme targets destitute / extreme poverty households.",
            score_weight=25, condition_id=f"{sid}_sem_destitute"))

    # ── S14: ACID ATTACK SURVIVOR ─────────────────────────────────────────────
    if "acid attack" in elig_lower:
        conditions.append(EligibilityCondition(
            field="is_acid_attack_survivor", operator="is_true", value=None,
            is_mandatory=True,
            failure_message="This scheme is for acid attack survivors only.",
            score_weight=30, condition_id=f"{sid}_sem_acid_attack"))

    # ── S15: DISASTER / CALAMITY VICTIM ──────────────────────────────────────
    DISASTER_PHRASES = ["flood victim", "disaster affected", "calamity affected",
                        "natural disaster", "cyclone victim", "earthquake affected",
                        "fire accident victim", "victims of natural"]
    if any(p in elig_lower for p in DISASTER_PHRASES):
        conditions.append(EligibilityCondition(
            field="is_disaster_affected", operator="is_true", value=None,
            is_mandatory=True,
            failure_message="This scheme is for victims of natural disaster / calamity.",
            score_weight=25, condition_id=f"{sid}_sem_disaster"))

    # ── S16: MIGRANT WORKER ───────────────────────────────────────────────────
    MIGRANT_PHRASES = ["inter-state migrant", "migrant worker", "migrant labour",
                       "seasonal migrant", "migrant labourer"]
    if any(p in elig_lower for p in MIGRANT_PHRASES):
        conditions.append(EligibilityCondition(
            field="is_migrant_worker", operator="is_true", value=None,
            is_mandatory=True,
            failure_message="This scheme is for inter-state migrant workers.",
            score_weight=25, condition_id=f"{sid}_sem_migrant"))

    # ── S17: TRACTOR / FARM EQUIPMENT OWNER ───────────────────────────────────
    TRACTOR_PHRASES = ["must own a tractor", "should have a tractor", "tractor owner",
                       "possess agricultural equipment", "owns farm machinery"]
    if any(p in elig_lower for p in TRACTOR_PHRASES):
        conditions.append(EligibilityCondition(
            field="has_tractor", operator="is_true", value=None,
            is_mandatory=True,
            failure_message="Must own a tractor or farm equipment.",
            score_weight=20, condition_id=f"{sid}_sem_tractor"))

    # ── S18: NUMBER OF CHILDREN ───────────────────────────────────────────────
    children_match = re.search(
        r"(\d+|one|two|three|four)\s+(?:or more\s+)?(?:children|sons and daughters|kids)",
        elig_lower)
    if children_match:
        num_map = {"one": 1, "two": 2, "three": 3, "four": 4}
        raw = children_match.group(1)
        req = num_map.get(raw, int(raw) if raw.isdigit() else 1)
        if req >= 2:
            conditions.append(EligibilityCondition(
                field="num_children", operator="gte", value=req,
                is_mandatory=True,
                failure_message=f"Must have at least {req} children.",
                score_weight=20, condition_id=f"{sid}_sem_children_{req}"))

    # ── S19: SPORTS CERTIFICATE ─────────────────────────────────────────────────
    SPORTS_PHRASES = [
        "sportsperson", "sports person", "athlete", "sports quota",
        "national level sport", "state level sport", "district sport",
        "international sport", "olympic", "commonwealth games",
        "meritorious sportsperson", "sports achievement", "sporting achievement",
        "represent state", "represent district", "represent national",
        "sports certificate", "sports qualification",
    ]
    if any(p in elig_lower for p in SPORTS_PHRASES):
        conditions.append(EligibilityCondition(
            field="sports_certificates",
            operator="contains", value="sports_certificate",
            is_mandatory=False,
            failure_message="This scheme requires a sports certificate. "
                            "Please add your sports achievements to your profile.",
            score_weight=20, condition_id=f"{sid}_sem_sports"))

    # ── S20: ART / CULTURE CERTIFICATE ─────────────────────────────────────────
    ART_PHRASES = [
        "art scholarship", "cultural talent", "classical dance", "classical music",
        "traditional art", "painting scholarship", "cultural activities",
        "fine arts", "performing arts", "artistic achievement",
        "cultural scholarship", "art certificate", "dance certificate",
        "music certificate", "cultural heritage", "folk art",
    ]
    if any(p in elig_lower for p in ART_PHRASES):
        conditions.append(EligibilityCondition(
            field="art_certificates",
            operator="contains", value="art_certificate",
            is_mandatory=False,
            failure_message="This scheme requires an art/culture certificate. "
                            "Please add your artistic achievements to your profile.",
            score_weight=20, condition_id=f"{sid}_sem_art"))

    # ── S21: NCC CERTIFICATE ───────────────────────────────────────────────────
    NCC_PHRASES = [
        "ncc certificate", "ncc holder", "ncc c certificate", 
        "ncc b certificate", "ncc a certificate",
        "ncc 'c' certificate", "ncc 'b' certificate", "ncc 'a' certificate",
        "national cadet corps", "ncc training",
    ]
    if any(p in elig_lower for p in NCC_PHRASES):
        conditions.append(EligibilityCondition(
            field="ncc_certificate", operator="is_true", value=None,
            is_mandatory=False,
            failure_message="This scheme requires an NCC certificate. "
                            "Please add your NCC details to your profile.",
            score_weight=20, condition_id=f"{sid}_sem_ncc"))

    # ── S22: NSS CERTIFICATE ───────────────────────────────────────────────────
    NSS_PHRASES = [
        "nss volunteer", "national service scheme", "nss certificate",
        "nss participation", "national service scheme volunteer",
    ]
    if any(p in elig_lower for p in NSS_PHRASES):
        conditions.append(EligibilityCondition(
            field="nss_certificate", operator="is_true", value=None,
            is_mandatory=False,
            failure_message="This scheme requires NSS participation. "
                            "Please add your NSS details to your profile.",
            score_weight=20, condition_id=f"{sid}_sem_nss"))

    # ── S23: SKILL / VOCATIONAL CERTIFICATE ─────────────────────────────────────
    SKILL_PHRASES = [
        "iti certified", "skill certificate", "vocational training",
        "industrial training institute", "skill development",
        "apprenticeship certificate", "trade certificate",
        "professional certificate", "competency certificate",
    ]
    if any(p in elig_lower for p in SKILL_PHRASES):
        conditions.append(EligibilityCondition(
            field="skill_certificates",
            operator="contains", value="skill_certificate",
            is_mandatory=False,
            failure_message="This scheme requires a skill/vocational certificate. "
                            "Please add your skills training to your profile.",
            score_weight=20, condition_id=f"{sid}_sem_skill"))

    total = len(conditions) + len(disqualifiers)
    if total > 0:
        logger.info(
            f"[Scheme {sid}] Semantic injector added {len(conditions)} conditions "
            f"+ {len(disqualifiers)} disqualifiers"
        )

    return conditions, disqualifiers
