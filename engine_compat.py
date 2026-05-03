"""
engine_compat.py
Bridges the new structured Condition-based engine with the existing
app.py (which uses flat Scheme columns and old ProfileNormalizer patterns).
Provides EligibilityOrchestrator configured to work with the existing DB.
"""
import json
import logging
from datetime import datetime, timezone

from app.engine.eligibility import (
    EligibilityEngine, EligibilityOutput,
    PASS_R, FAIL_R, UNKNOWN_C,
    ELIGIBLE, POSSIBLE, INELIGIBLE,
    evaluate_single, normalize_gender,
)
from app.engine.context import ContextualReasoner
from app.engine.questions import QuestionEngine
from app.engine.scorer import ResultRanker

log = logging.getLogger(__name__)

ORCHESTRATOR_INSTANCE = None


def get_orchestrator(app_config=None):
    """Singleton orchestrator — configured once per app lifecycle."""
    global ORCHESTRATOR_INSTANCE
    if ORCHESTRATOR_INSTANCE is None:
        cfg = app_config or {}
        ORCHESTRATOR_INSTANCE = NewEligibilityOrchestrator(cfg)
    return ORCHESTRATOR_INSTANCE


def _condition_result(condition_id, field, status, reason):
    from dataclasses import dataclass
    @dataclass
    class CR:
        condition_id: str
        field: str
        status: str
        reason: str
    return CR(str(condition_id), field, status, reason)


class NewEligibilityOrchestrator:
    """
    Wraps the new engine to work with existing Scheme/User objects.
    Handles schemes that have:
    1. Condition rows in the DB (new path)
    2. Only flat columns (old path — converted on-the-fly via Scheme.conditions property)
    """

    def __init__(self, config=None):
        self.cfg = config or {}
        self.engine  = EligibilityEngine(self.cfg)
        self.ctx     = ContextualReasoner()
        self.qengine = QuestionEngine(self.ctx, max_questions=self.cfg.get("MAX_QUESTIONS_PER_SESSION", 3))
        self.ranker  = ResultRanker()
        self._quality_score_cache = {}

    def _get_quality_score(self, scheme) -> float:
        """Get or compute quality score for a scheme."""
        if hasattr(scheme, 'quality_score') and scheme.quality_score:
            return scheme.quality_score
        if scheme.id in self._quality_score_cache:
            return self._quality_score_cache[scheme.id]
        return 0.50

    def prefilter(self, user, schemes_query):
        """Fast DB-level filter: active schemes, state match."""
        today = datetime.now(timezone.utc).date()
        candidates = []
        for scheme in schemes_query:
            if hasattr(scheme, 'is_active') and not scheme.is_active:
                continue
            if hasattr(scheme, 'expires_at') and scheme.expires_at:
                if scheme.expires_at < today:
                    continue
            if hasattr(scheme, 'allowed_states') and scheme.allowed_states and hasattr(user, 'state') and user.state:
                import json
                allowed = scheme.allowed_states
                if isinstance(allowed, str):
                    try:
                        allowed = json.loads(allowed)
                    except:
                        allowed = []
                allowed = [s.lower() for s in allowed]
                if allowed and 'all' not in allowed:
                    if user.state.lower() not in allowed:
                        continue
            candidates.append(scheme)
        return candidates

    def _tier(self, scheme, profile: dict) -> int:
        """1=full+questions, 2=full no questions, 3=hard only."""
        ctx_score = self.ctx.score(scheme, profile)
        if ctx_score >= 0.65:
            return 1
        if ctx_score >= 0.35:
            return 2
        return 3

    def evaluate_single_scheme(self, scheme, user, use_cache=True):
        """
        Evaluate one scheme for one user.
        Exclusively uses the multi-pass engine for 100% stability.
        """
        if not hasattr(user, 'get_profile_dict'):
            profile = {}
        else:
            profile = user.get_profile_dict()

        conds = list(scheme.conditions) if hasattr(scheme, 'conditions') else []

        if not conds:
            return EligibilityOutput(
                result=POSSIBLE, confidence=0.10,
                blocking_reason="No conditions extracted for this scheme",
                missing_fields=[], acquirable=[],
            )

        ctx_score = self.ctx.score(scheme, profile)
        return self.engine.evaluate(scheme, profile, ctx_score)

    def _hard_fail_fast(self, hard_conds, profile):
        """Fast hard fail check without building full result."""
        from collections import defaultdict
        NUMERIC_FIELDS = {"age", "annual_income", "family_income", "monthly_income",
                          "income", "disability_percentage"}

        by_field = defaultdict(list)
        for cond in hard_conds:
            by_field[getattr(cond, 'field', '')].append(cond)

        for field_name, fconds in by_field.items():
            pv = profile.get(field_name)
            if pv is None:
                continue

            if field_name in NUMERIC_FIELDS:
                gte_vals, lte_vals = [], []
                for c in fconds:
                    try:
                        val = json.loads(c.value) if isinstance(c.value, str) else c.value
                        val = float(val)
                        op = getattr(c, 'operator', 'eq')
                        if op == 'gte':
                            gte_vals.append(val)
                        elif op == 'lte':
                            lte_vals.append(val)
                    except (ValueError, TypeError):
                        pass
                max_lower = max(gte_vals) if gte_vals else float("-inf")
                min_upper = min(lte_vals) if lte_vals else float("inf")
                try:
                    pv_f = float(pv)
                    if not (max_lower <= pv_f <= min_upper):
                        return True
                except (ValueError, TypeError):
                    return True
            else:
                any_pass = any(
                    evaluate_single(c, profile).status == PASS_R for c in fconds
                )
                if not any_pass:
                    return True
        return False

    def evaluate_all(self, user, schemes, use_cache=True, question_cap=3):
        """
        Evaluate all schemes for a user.
        Returns (ranked_list, questions_list).
        """
        if not hasattr(user, 'get_profile_dict'):
            profile = {}
        else:
            profile = user.get_profile_dict()

        candidates = self.prefilter(user, schemes)
        scheme_results = []
        possible_pairs = []

        for scheme in candidates:
            eo = self.evaluate_single_scheme(scheme, user, use_cache)
            scheme_results.append((scheme, eo))
            if eo.result == POSSIBLE:
                possible_pairs.append((scheme, eo))

        ranked = self.ranker.rank(scheme_results)
        questions = self.qengine.select_questions(possible_pairs, profile)
        if question_cap is not None:
            questions = questions[:question_cap]

        return ranked, questions

    def quick_score(self, user, scheme) -> float:
        """Fast 0.0–1.0 match score without full evaluation."""
        eo = self.evaluate_single_scheme(scheme, user, use_cache=False)
        return eo.confidence


def build_engine_response(orch, user, all_schemes):
    """
    Build a recommendations response dict from the orchestrator.
    Mirrors the format expected by existing /api/recommendations route.
    """
    ranked, questions = orch.evaluate_all(user, all_schemes, use_cache=True, question_cap=3)

    recommendations = []
    possibly_eligible = []
    ineligible_count = 0

    for r in ranked:
        entry = {
            "id":                r.scheme_id,
            "name":              r.scheme_name,
            "result":            r.result,
            "confidence":        r.confidence,
            "display_label":     r.display_label,
            "action_label":      r.action_label,
            "top_insight":       r.top_insight,
            "missing_fields":    r.missing_fields,
            "acquirable":        r.acquirable,
            "blocking_reason":   r.blocking_reason,
        }
        if r.result == ELIGIBLE:
            recommendations.append(entry)
        elif r.result == INELIGIBLE:
            # Do NOT surface ineligible in either list — just count them
            ineligible_count += 1
        else:
            # POSSIBLE → possibly_eligible
            possibly_eligible.append(entry)

    return {
        "recommendations":   recommendations,
        "possibly_eligible": possibly_eligible,
        "questions":         [q.to_dict() for q in questions],
        "meta": {
            "total":            len(ranked),
            "fully_eligible":  len(recommendations),
            "possibly_eligible": len(possibly_eligible),
            "ineligible":      ineligible_count,
        }
    }


def build_single_scheme_response(scheme, user, orch=None):
    """
    Build a single-scheme eligibility response.
    Mirrors the format expected by existing /api/schemes/<id>/eligibility route.
    """
    if orch is None:
        orch = get_orchestrator()
    eo = orch.evaluate_single_scheme(scheme, user, use_cache=True)

    if eo.result == ELIGIBLE:
        label, action = "Likely Eligible", "Apply Now"
    elif eo.result == INELIGIBLE:
        label, action = "Not Eligible", "See Why"
    else:
        label, action = "Possibly Eligible", "Check & Apply"

    return {
        "scheme_id":         scheme.id,
        "scheme_name":       scheme.name,
        "score":             eo.confidence,
        "display_label":     label,
        "action_label":      action,
        "result":            eo.result,
        "blocking_reason":   eo.blocking_reason,
        "missing_fields":    eo.missing_fields,
        "acquirable":        eo.acquirable,
        "top_insight":       eo.blocking_reason or (
            f"Confirm your {eo.missing_fields[0]}" if eo.missing_fields
            else "You appear to meet all known requirements."
        ),
    }
