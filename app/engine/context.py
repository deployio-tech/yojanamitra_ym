"""
engine/context.py
Contextual Reasoner — computes a 0.0–1.0 plausibility signal
without creating hard failures. Adjusts which questions are asked first.
"""
import logging

log = logging.getLogger(__name__)

# Domain → occupation keywords likely to map there
DOMAIN_OCCUPATION_MAP = {
    "agriculture":   ["farmer", "agriculturist", "kisan", "cultivator", "fisherman"],
    "fisheries":     ["fisherman", "fisher", "fish farmer"],
    "education":     ["student", "teacher", "lecturer", "professor"],
    "health":        ["doctor", "nurse", "asha", "health worker"],
    "labour":        ["labourer", "worker", "construction", "migrant"],
    "women":         [],   # handled by gender
    "disability":    [],   # handled by boolean flags
    "minority":      [],
    "sc_st":         [],
    "obc":           [],
    "entrepreneur":  ["entrepreneur", "business", "self-employed", "msme"],
}

# Target group → profile field mappings
TARGET_PROFILE_MAP = {
    "women":        ("gender",   "female"),
    "girl":         ("gender",   "female"),
    "girls":        ("gender",   "female"),
    "daughter":     ("gender",   "female"),
    "boy":          ("gender",   "male"),
    "boys":         ("gender",   "male"),
    "son":          ("gender",   "male"),
    "sc":           ("category", "sc"),
    "st":           ("category", "st"),
    "obc":          ("category", "obc"),
    "ews":          ("category", "ews"),
    "student":      ("is_student", True),
    "farmer":       ("occupation", "farmer"),
    "fisherman":    ("occupation", "fisherman"),
    "disabled":     ("is_disabled", True),
    "transgender":  ("is_transgender", True),
    "bpl":          ("is_bpl", True),
}


def _occ_match(occupation: str, domain_keys: list) -> float:
    if not occupation:
        return 0.0
    occ_lower = occupation.lower()
    for kw in domain_keys:
        if kw in occ_lower:
            return 0.85
    return 0.0


class ContextualReasoner:
    """
    Returns a context_score in [0.0, 1.0] for a (scheme, user_profile) pair.
    This is a soft signal — it never overrides hard conditions.
    """

    def score(self, scheme, user_profile: dict) -> float:
        signals = []

        # 1. State match (scheme uses 'allowed_states' field - JSON list)
        user_state = (user_profile.get("state") or "").strip().lower()
        scheme_states = getattr(scheme, 'allowed_states', None)
        if scheme_states:
            import json
            if isinstance(scheme_states, str):
                try:
                    scheme_states = json.loads(scheme_states)
                except:
                    scheme_states = []
            scheme_states = [s.lower() for s in scheme_states]
            if scheme_states and 'all' not in scheme_states:
                if user_state and user_state in scheme_states:
                    signals.append(0.90)
                else:
                    signals.append(0.10)
            else:
                signals.append(0.50)
        elif user_state:
            signals.append(0.50)
        else:
            signals.append(0.50)

        # 2. Domain × occupation plausibility
        try:
            import json
            domains = json.loads(scheme.domain or "[]") if isinstance(scheme.domain, str) else (scheme.domain or [])
        except Exception:
            domains = []

        occ = user_profile.get("occupation", "")
        domain_signal = 0.50
        for d in domains:
            kws = DOMAIN_OCCUPATION_MAP.get(d.lower(), [])
            m = _occ_match(occ, kws)
            if m > 0:
                domain_signal = m
                break
        signals.append(domain_signal)

        # 3. Target group alignment
        try:
            import json
            tgroups = json.loads(scheme.target_groups or "[]") if isinstance(scheme.target_groups, str) else (scheme.target_groups or [])
        except Exception:
            tgroups = []

        tg_signal = 0.50
        if tgroups:
            matched = 0
            mismatched = 0
            for tg in tgroups:
                mapping = TARGET_PROFILE_MAP.get(tg.lower())
                if not mapping:
                    continue
                pfield, pval = mapping
                user_val = user_profile.get(pfield)
                if user_val is None:
                    continue   # unknown → neutral
                if isinstance(pval, str):
                    if str(user_val).lower() == pval.lower():
                        matched += 1
                    else:
                        mismatched += 1
                elif isinstance(pval, bool):
                    if bool(user_val) == pval:
                        matched += 1
                    else:
                        mismatched += 1
            if matched + mismatched > 0:
                tg_signal = matched / (matched + mismatched)
        signals.append(tg_signal)

        # 4. Age plausibility (if no hard age condition, use soft signal)
        user_age = user_profile.get("age")
        if user_age is not None:
            try:
                age_val = int(user_age)
                if 18 <= age_val <= 60:
                    signals.append(0.70)
                elif age_val < 18:
                    signals.append(0.55)  # could be student schemes
                else:
                    signals.append(0.55)  # could be senior schemes
            except (ValueError, TypeError):
                logging.warning(f"[CONTEXT] Invalid age value '{user_age}' - skipping age plausibility")
                pass  # skip if invalid

        # 5. Income plausibility for welfare schemes
        income = user_profile.get("annual_income")
        if income is not None and tgroups:
            welfare_tgs = {"sc", "st", "obc", "bpl", "ews"}
            if any(t.lower() in welfare_tgs for t in tgroups):
                try:
                    income_val = int(income)
                    if income_val <= 300000:
                        signals.append(0.80)
                    elif income_val <= 800000:
                        signals.append(0.50)
                    else:
                        signals.append(0.20)
                except (ValueError, TypeError):
                    logging.warning(f"[CONTEXT] Invalid income value '{income}' - skipping income plausibility")
                    pass  # skip if invalid

        # 6. Benefit type from scheme name (no benefit_type field in DB)
        name_lower = (scheme.name or "").lower()
        is_student = user_profile.get("is_student", False)
        user_age = user_profile.get("age")
        benefit_signal = 0.50
        if any(k in name_lower for k in ("scholarship", "fellowship", "grant")):
            benefit_signal = 0.85 if is_student else 0.50
        elif any(k in name_lower for k in ("loan", "credit")):
            benefit_signal = 0.80 if occ in ("self-employed", "business", "farmer") else 0.50
        elif "pension" in name_lower:
            benefit_signal = 0.85 if (user_age and int(user_age) >= 60) else 0.50
        elif any(k in name_lower for k in ("training", "skill")):
            benefit_signal = 0.80 if occ in ("student", "unemployed", "labourer") else 0.50
        if benefit_signal != 0.50:
            signals.append(benefit_signal)

        # 7. Quality score signal
        qs = getattr(scheme, 'quality_score', 0.0) or 0.0
        if qs >= 0.7:
            signals.append(0.70)
        elif qs >= 0.4:
            signals.append(0.55)
        elif qs > 0:
            signals.append(0.40)

        # 8. Target group specificity boost
        if tgroups:
            tg_boost = 0.0
            cat = (user_profile.get("category") or "").lower()
            if any(t.lower() == cat for t in tgroups):
                tg_boost += 0.05
            if occ and any(t.lower() in occ for t in tgroups):
                tg_boost += 0.05
            if tg_boost > 0:
                signals.append(0.50 + tg_boost)

        # Weighted average of all signals
        if not signals:
            return 0.50
        return round(sum(signals) / len(signals), 4)

    def field_plausibility(self, field_name: str, user_profile: dict) -> float:
        """
        Returns 0.0–1.0 estimate of whether the user likely has a certain
        field value as True/positive. Used to deprioritise questions.
        """
        occ = (user_profile.get("occupation") or "").lower()
        age = user_profile.get("age")

        plausibility_rules = {
            "is_student":        0.80 if (age and int(age) <= 25) else 0.20,
            "is_farmer":         0.70 if "farm" in occ or "kisan" in occ else 0.15,
            "is_fisherman":      0.70 if "fish" in occ else 0.05,
            "is_bpl":            0.60 if (user_profile.get("annual_income") or 999999) < 100000 else 0.15,
            "is_disabled":       0.10,
            "is_transgender":    0.05,
            "is_widow":          0.60 if user_profile.get("gender") == "female" else 0.02,
            "is_pregnant":       0.10 if user_profile.get("gender") == "female" else 0.02,
            "has_aadhaar":       0.90,
            "has_bank_account":  0.85,
            "is_construction_worker": 0.40 if "construct" in occ or "labour" in occ else 0.10,
            "is_self_employed":  0.50,
            "is_marginal_farmer": 0.20,
            "is_minority":       0.50,
            "is_ews":            0.50,
            "is_urban":          0.50,
            "is_rural":          0.50,
            "has_domicile":      0.70,
            "has_land_record":    0.40,
        }
        return plausibility_rules.get(field_name, 0.50)
