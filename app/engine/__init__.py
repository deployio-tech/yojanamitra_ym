"""
engine/__init__.py
Orchestrator — ties together prefilter, engine, context, questions, cache.
"""
import json
import logging
from datetime import datetime, timezone

from app.engine.eligibility import EligibilityEngine, INELIGIBLE, POSSIBLE, ELIGIBLE
from app.engine.context    import ContextualReasoner
from app.engine.questions  import QuestionEngine
from app.engine.scorer     import ResultRanker

log = logging.getLogger(__name__)


class EligibilityOrchestrator:

    def __init__(self, app_config=None):
        cfg = app_config or {}
        self.engine   = EligibilityEngine(cfg)
        self.ctx      = ContextualReasoner()
        self.qengine  = QuestionEngine(self.ctx, max_questions=None)
        self.ranker   = ResultRanker()

    # ── Pre-filter ─────────────────────────────────────────────────────────────

    def prefilter(self, user, schemes_query):
        """
        Fast DB-level filter: active, extracted, not expired, state match.
        Returns a list of Scheme objects.
        """
        from datetime import date
        today = date.today()

        candidates = []
        for scheme in schemes_query:
            if not scheme.is_active:
                continue
            # Allow schemes that are extracted OR have conditions in DB
            has_conditions = hasattr(scheme, 'condition_rows') and scheme.condition_rows.count() > 0
            if scheme.extraction_status != "extracted" and not has_conditions:
                continue
            if scheme.expires_at and scheme.expires_at < today:
                continue
            # State filter: central (None) always passes; state must match
            # Scheme uses 'allowed_states' field (JSON list)
            if hasattr(scheme, 'allowed_states') and scheme.allowed_states and user.state:
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

    # ── Cache check ────────────────────────────────────────────────────────────

    def _get_cached(self, user_id, scheme_id, profile_version):
        from app import EligibilityResult
        er = EligibilityResult.query.filter_by(
            user_id=user_id, scheme_id=scheme_id
        ).first()
        if er and er.profile_version == profile_version:
            return er
        return None

    def _write_cache(self, user, scheme, elig_out):
        from app import db, EligibilityResult
        er = EligibilityResult.query.filter_by(
            user_id=user.id, scheme_id=scheme.id
        ).first()
        if not er:
            er = EligibilityResult(user_id=user.id, scheme_id=scheme.id)
            db.session.add(er)
        er.result          = elig_out.result
        er.confidence      = elig_out.confidence
        er.blocking_reason = elig_out.blocking_reason
        er.missing_fields  = json.dumps(elig_out.missing_fields)
        er.acquirable      = json.dumps(elig_out.acquirable)
        er.computed_at     = datetime.now(timezone.utc)
        er.profile_version = user.profile_version
        db.session.commit()

    # ── Tiering ────────────────────────────────────────────────────────────────

    def _tier(self, scheme, user_profile: dict) -> int:
        """1 = full+questions, 2 = full no questions, 3 = hard only."""
        ctx_score = self.ctx.score(scheme, user_profile)
        if ctx_score >= 0.65:
            return 1
        if ctx_score >= 0.35:
            return 2
        return 3

    # ── Main evaluate ──────────────────────────────────────────────────────────

    def evaluate_for_user(self, user, all_schemes, use_cache=True, question_cap=3):
        """
        Full evaluation loop for one user.
        Returns (ranked_list, questions_list)
        """
        profile = user.get_profile_dict()
        candidates = self.prefilter(user, all_schemes)

        scheme_results = []
        possible_pairs = []

        for scheme in candidates:
            # Cache hit
            if use_cache:
                cached = self._get_cached(user.id, scheme.id, user.profile_version)
                if cached:
                    from app.engine.eligibility import EligibilityOutput
                    eo = EligibilityOutput(
                        result=cached.result,
                        confidence=cached.confidence,
                        blocking_reason=cached.blocking_reason or "",
                        missing_fields=cached.missing_fields_list,
                        acquirable=cached.acquirable_list,
                    )
                    scheme_results.append((scheme, eo))
                    if eo.result == POSSIBLE:
                        possible_pairs.append((scheme, eo))
                    continue

            tier = self._tier(scheme, profile)
            ctx_score = self.ctx.score(scheme, profile)

            if tier == 3:
                from app.engine.eligibility import evaluate_single, FAIL_R, EligibilityOutput
                from collections import defaultdict
                import json
                NUMERIC_FIELDS = {"age", "annual_income", "family_income", "monthly_income",
                                  "income", "disability_percentage"}
                hard_conds = [c for c in scheme.conditions if c.condition_type == "hard" and not c.is_ambiguous]
                by_field = defaultdict(list)
                for cond in hard_conds:
                    by_field[cond.field].append(cond)
                hard_fail = False
                for field_name, field_conds in by_field.items():
                    pv = profile.get(field_name)
                    if pv is None:
                        continue
                    if field_name in NUMERIC_FIELDS:
                        gte_vals, lte_vals = [], []
                        for c in field_conds:
                            try:
                                val = json.loads(c.value) if isinstance(c.value, str) else c.value
                                val = float(val)
                                if c.operator == "gte":
                                    gte_vals.append(val)
                                elif c.operator == "lte":
                                    lte_vals.append(val)
                            except (ValueError, TypeError):
                                pass
                        max_lower = max(gte_vals) if gte_vals else float("-inf")
                        min_upper = min(lte_vals) if lte_vals else float("inf")
                        try:
                            pv_f = float(pv)
                            if not (max_lower <= pv_f <= min_upper):
                                hard_fail = True
                                break
                        except (ValueError, TypeError):
                            hard_fail = True
                            break
                    else:
                        any_pass = any(evaluate_single(c, profile).status == PASS_R for c in field_conds)
                        if not any_pass:
                            hard_fail = True
                            break
                if hard_fail:
                    eo = EligibilityOutput(result=INELIGIBLE, confidence=1.0,
                                           blocking_reason="Hard condition failed (Tier 3)")
                else:
                    eo = EligibilityOutput(result=POSSIBLE, confidence=max(0.10, ctx_score * 0.4))
            else:
                eo = self.engine.evaluate(scheme, profile, ctx_score)

            self._write_cache(user, scheme, eo)
            scheme_results.append((scheme, eo))
            if eo.result == POSSIBLE:
                possible_pairs.append((scheme, eo))

        ranked = self.ranker.rank(scheme_results)

        # Generate questions from POSSIBLE schemes only
        questions = self.qengine.select_questions(possible_pairs, profile)
        if question_cap is not None:
            questions = questions[:question_cap]

        return ranked, questions

    def invalidate_cache_for_field(self, user_id: str, field_name: str):
        """Delete cached results for schemes that have a condition on field_name."""
        from app import db, EligibilityResult, Condition
        affected_scheme_ids = db.session.query(Condition.scheme_id).filter_by(
            field=field_name
        ).distinct().all()
        ids = [r[0] for r in affected_scheme_ids]
        if ids:
            EligibilityResult.query.filter(
                EligibilityResult.user_id == user_id,
                EligibilityResult.scheme_id.in_(ids),
            ).delete(synchronize_session=False)
            db.session.commit()
