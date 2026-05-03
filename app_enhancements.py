"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  APP ENHANCEMENTS — New Flask Routes for All 8 Tasks                        ║
║                                                                              ║
║  Integration: Add `from app_enhancements import register_enhancement_routes` ║
║  to app.py, then call `register_enhancement_routes(app, db, model, ...)`.   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from flask import request, jsonify, session
from datetime import datetime, timezone
import json
import logging
import re

from semantic_tagger import (
    BatchTagger, SemanticMatchValidator, FalsePositiveAnalyzer,
    ContinuousLearner, AITagExtractor, SchemeTagProfile
)
from confidence_invoker import (
    ConfidenceScorer, AIFallbackValidator, ProfileSchemaAdvisor,
    EligibilityPipeline, _sanitize_profile_strict
)

logger = logging.getLogger("yojanamitra.enhancements")


# ══════════════════════════════════════════════════════════════════════════════
# DB MODELS (add to app.py or run migration)
# ══════════════════════════════════════════════════════════════════════════════

def create_enhancement_models(db):
    """
    Define and return new SQLAlchemy models needed by the enhancement system.
    Call this after `db = SQLAlchemy(app)` in app.py.
    """

    class SchemeSemanticTag(db.Model):
        """
        Task 1: Stores pre-computed semantic tags for each scheme.
        Updated during batch tagging or on-demand via API.
        """
        __tablename__ = 'scheme_semantic_tag'
        id           = db.Column(db.Integer, primary_key=True)
        scheme_id    = db.Column(db.Integer, db.ForeignKey('scheme.id'), unique=True, nullable=False)
        tags_json    = db.Column(db.Text, nullable=False)       # JSON: SchemeTagProfile.to_json()
        extraction_method = db.Column(db.String(20), default='hybrid')
        version      = db.Column(db.Integer, default=1)
        extracted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
        updated_at   = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))

        scheme = db.relationship('Scheme', backref=db.backref('semantic_tag', uselist=False, lazy='joined'))

        def to_dict(self):
            return {
                'scheme_id':   self.scheme_id,
                'tags':        json.loads(self.tags_json) if self.tags_json else {},
                'method':      self.extraction_method,
                'version':     self.version,
                'extracted_at': self.extracted_at.isoformat() if self.extracted_at else None,
            }

    class FalsePositiveFeedback(db.Model):
        """
        Task 4: Stores false positive reports from users and admins.
        Used for pattern analysis and system improvement.
        """
        __tablename__ = 'false_positive_feedback'
        id              = db.Column(db.Integer, primary_key=True)
        scheme_id       = db.Column(db.Integer, db.ForeignKey('scheme.id'), nullable=False)
        user_id         = db.Column(db.Integer, db.ForeignKey('user.id'))
        reason          = db.Column(db.Text, nullable=False)
        root_cause      = db.Column(db.String(200))
        pattern_category= db.Column(db.String(100))
        generalization  = db.Column(db.Text)
        status          = db.Column(db.String(20), default='new')  # new|reviewed|fixed
        reported_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

        def to_dict(self):
            return {
                'id':              self.id,
                'scheme_id':       self.scheme_id,
                'user_id':         self.user_id,
                'reason':          self.reason,
                'root_cause':      self.root_cause,
                'pattern_category': self.pattern_category,
                'generalization':  self.generalization,
                'status':          self.status,
                'reported_at':     self.reported_at.isoformat(),
            }

    class MissingFieldLog(db.Model):
        """
        Task 5: Logs instances where missing profile fields caused match failures.
        Aggregated to identify high-impact fields to add to the profile form.
        """
        __tablename__ = 'missing_field_log'
        id           = db.Column(db.Integer, primary_key=True)
        scheme_id    = db.Column(db.Integer, db.ForeignKey('scheme.id'))
        user_id      = db.Column(db.Integer, db.ForeignKey('user.id'))
        missing_field= db.Column(db.String(100), nullable=False)
        impact_level = db.Column(db.String(20), default='medium')
        reason       = db.Column(db.Text)
        logged_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

        def to_dict(self):
            return {
                'id':           self.id,
                'scheme_id':    self.scheme_id,
                'missing_field': self.missing_field,
                'impact_level': self.impact_level,
                'reason':       self.reason,
                'logged_at':    self.logged_at.isoformat(),
            }

    class LearningCycleLog(db.Model):
        """
        Task 6: Logs each continuous learning cycle result.
        """
        __tablename__ = 'learning_cycle_log'
        id           = db.Column(db.Integer, primary_key=True)
        run_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
        fp_count     = db.Column(db.Integer, default=0)
        patterns_found = db.Column(db.Integer, default=0)
        recommendations_json = db.Column(db.Text)
        triggered_by = db.Column(db.String(50), default='manual')  # manual|scheduler

        def to_dict(self):
            return {
                'id':          self.id,
                'run_at':      self.run_at.isoformat(),
                'fp_count':    self.fp_count,
                'patterns_found': self.patterns_found,
                'recommendations': json.loads(self.recommendations_json) if self.recommendations_json else [],
                'triggered_by': self.triggered_by,
            }

    return {
        'SchemeSemanticTag':   SchemeSemanticTag,
        'FalsePositiveFeedback': FalsePositiveFeedback,
        'MissingFieldLog':     MissingFieldLog,
        'LearningCycleLog':    LearningCycleLog,
    }


# ══════════════════════════════════════════════════════════════════════════════
# ROUTE REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════

def register_enhancement_routes(app, db, gemini_model, models: dict, Scheme, User):
    """
    Register all new API routes for the 8-task enhancement system.

    Parameters:
        app          — Flask app instance
        db           — SQLAlchemy db instance
        gemini_model — Initialized Gemini model (or None)
        models       — Dict from create_enhancement_models()
        Scheme       — Scheme model class
        User         — User model class
    """
    SchemeSemanticTag    = models['SchemeSemanticTag']
    FalsePositiveFeedback = models['FalsePositiveFeedback']
    MissingFieldLog      = models['MissingFieldLog']
    LearningCycleLog     = models['LearningCycleLog']

    tagger     = BatchTagger(gemini_model=gemini_model)
    validator  = SemanticMatchValidator()
    fp_analyzer = FalsePositiveAnalyzer()
    profile_advisor = ProfileSchemaAdvisor()
    ai_validator = AIFallbackValidator(gemini_model)
    pipeline   = EligibilityPipeline(gemini_model=gemini_model)

    # ── Task 1: Semantic Pre-Tagging ─────────────────────────────────────────

    @app.route('/api/admin/semantic-tags/batch', methods=['POST'])
    def batch_tag_schemes():
        """
        Task 1: Trigger AI batch semantic tagging for all (or untagged) schemes.
        Admin only. Long-running — returns job status immediately.
        """
        if session.get('user_type') != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.json or {}
        only_untagged = data.get('only_untagged', True)
        scheme_ids    = data.get('scheme_ids', [])  # Optional: specific scheme IDs

        # Determine which schemes to tag
        if scheme_ids:
            schemes = Scheme.query.filter(Scheme.id.in_(scheme_ids)).all()
        elif only_untagged:
            tagged_ids = {st.scheme_id for st in SchemeSemanticTag.query.all()}
            schemes = Scheme.query.filter(~Scheme.id.in_(tagged_ids)).all()
        else:
            schemes = Scheme.query.all()

        if not schemes:
            return jsonify({'message': 'No schemes to tag', 'tagged': 0}), 200

        # Run in background
        import threading
        def _tag_job():
            with app.app_context():
                tagged_count = 0
                for scheme in schemes:
                    try:
                        scheme_dict = scheme.to_dict()
                        scheme_dict['id'] = scheme.id
                        profile = tagger.tag_scheme(scheme_dict)
                        profile_json = profile.to_json()

                        existing = SchemeSemanticTag.query.filter_by(scheme_id=scheme.id).first()
                        if existing:
                            existing.tags_json         = profile_json
                            existing.extraction_method = profile.extraction_method
                            existing.version           += 1
                            existing.extracted_at      = datetime.now(timezone.utc)
                        else:
                            tag_record = SchemeSemanticTag(
                                scheme_id=scheme.id,
                                tags_json=profile_json,
                                extraction_method=profile.extraction_method,
                            )
                            db.session.add(tag_record)

                        db.session.commit()
                        tagged_count += 1
                    except Exception as e:
                        logger.error(f"Tagging error for scheme {scheme.id}: {e}")
                        db.session.rollback()

                logger.info(f"Batch tagging complete: {tagged_count} schemes tagged")

        threading.Thread(target=_tag_job, daemon=True).start()

        return jsonify({
            'message':  f'Batch tagging started for {len(schemes)} schemes',
            'total':    len(schemes),
            'status':   'running',
        }), 202

    @app.route('/api/admin/semantic-tags/<int:scheme_id>', methods=['GET'])
    def get_scheme_semantic_tags(scheme_id):
        """Get semantic tags for a specific scheme."""
        if session.get('user_type') != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        tag_record = SchemeSemanticTag.query.filter_by(scheme_id=scheme_id).first()
        if not tag_record:
            return jsonify({'tags': [], 'message': 'No tags computed yet'}), 200

        return jsonify(tag_record.to_dict()), 200

    @app.route('/api/admin/semantic-tags/<int:scheme_id>', methods=['POST'])
    def tag_single_scheme(scheme_id):
        """Trigger on-demand semantic tagging for a single scheme."""
        if session.get('user_type') != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        scheme = Scheme.query.get_or_404(scheme_id)
        scheme_dict = scheme.to_dict()
        scheme_dict['id'] = scheme.id

        try:
            profile = tagger.tag_scheme(scheme_dict)
            profile_json = profile.to_json()

            existing = SchemeSemanticTag.query.filter_by(scheme_id=scheme_id).first()
            if existing:
                existing.tags_json = profile_json
                existing.extraction_method = profile.extraction_method
                existing.version += 1
                existing.extracted_at = datetime.now(timezone.utc)
            else:
                tag_record = SchemeSemanticTag(
                    scheme_id=scheme_id,
                    tags_json=profile_json,
                    extraction_method=profile.extraction_method,
                )
                db.session.add(tag_record)

            db.session.commit()
            return jsonify({'message': 'Tags updated', 'tags': profile.to_json()}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/admin/semantic-tags/coverage', methods=['GET'])
    def get_tag_coverage():
        """Get tag coverage stats — how many schemes have been tagged."""
        if session.get('user_type') != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        total_schemes = Scheme.query.count()
        tagged_schemes = SchemeSemanticTag.query.count()
        low_tag_schemes = SchemeSemanticTag.query.filter(
            SchemeSemanticTag.tags_json.like('%"tags": []%')
        ).count()

        return jsonify({
            'total_schemes':   total_schemes,
            'tagged_schemes':  tagged_schemes,
            'untagged_schemes': total_schemes - tagged_schemes,
            'coverage_pct':    round((tagged_schemes / max(total_schemes, 1)) * 100, 1),
            'low_coverage_schemes': low_tag_schemes,
        }), 200

    # ── Task 3: Confidence-Based AI Invocation ───────────────────────────────

    @app.route('/api/schemes/<int:scheme_id>/confidence-check', methods=['POST'])
    def confidence_check_scheme(scheme_id):
        """
        Task 3: Run full confidence assessment + optional AI validation
        for a specific scheme against the logged-in user's profile.
        """
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not logged in'}), 401

        scheme = Scheme.query.get_or_404(scheme_id)
        user   = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Build raw user profile
        raw_profile = _build_raw_profile(user)

        # Get semantic tags
        tag_record = SchemeSemanticTag.query.filter_by(scheme_id=scheme_id).first()
        tags = []
        semantic_violations = []
        semantic_delta = 0.0

        if tag_record:
            try:
                tp = SchemeTagProfile.from_json(tag_record.tags_json)
                tags = tp.tags
                _, semantic_violations, semantic_delta = validator.validate(tags, raw_profile)
            except Exception as e:
                logger.warning(f"Semantic validation failed for scheme {scheme_id}: {e}")

        # Run confidence assessment
        scorer = ConfidenceScorer()
        confidence = scorer.assess(
            scheme_id=scheme_id,
            scheme_name=scheme.name,
            base_engine_score=70,  # Default — caller can pass actual engine score
            semantic_violations=semantic_violations,
            semantic_delta=semantic_delta,
            user_profile=raw_profile,
            eligibility_text=scheme.eligibility or "",
        )

        # Log missing fields (Task 5)
        for field_name in confidence.missing_profile_fields:
            log_entry = MissingFieldLog(
                scheme_id=scheme_id,
                user_id=user_id,
                missing_field=field_name,
                impact_level=profile_advisor._assess_impact(field_name, scheme.name),
                reason=f"Field '{field_name}' missing when evaluating '{scheme.name}'",
            )
            db.session.add(log_entry)
        db.session.commit()

        # Optional AI validation
        ai_result = None
        if confidence.requires_ai_validation and gemini_model:
            safe_profile = _sanitize_profile_strict(raw_profile)
            ai_result = ai_validator.validate(scheme.to_dict(), safe_profile, confidence)

        return jsonify({
            'scheme_id':         scheme_id,
            'scheme_name':       scheme.name,
            'confidence':        confidence.to_dict(),
            'semantic_violations': semantic_violations,
            'ai_validation':     ai_result,
            'privacy_confirmed': True,  # Task 8: confirming PII not sent to AI
        }), 200

    # ── Task 4: False Positive Reporting ────────────────────────────────────

    @app.route('/api/feedback/false-positive', methods=['POST'])
    def report_false_positive():
        """
        Task 4: User or admin reports a false positive.
        System analyzes root cause and generalizes the fix.
        """
        data    = request.json or {}
        user_id = session.get('user_id')

        scheme_id = data.get('scheme_id')
        reason    = data.get('reason', 'Scheme shown but I am not eligible')

        if not scheme_id:
            return jsonify({'error': 'scheme_id is required'}), 400

        scheme = Scheme.query.get(scheme_id)
        if not scheme:
            return jsonify({'error': 'Scheme not found'}), 404

        # Analyze root cause
        scheme_dict = scheme.to_dict()
        scheme_dict['id'] = scheme.id
        fp_report = fp_analyzer.analyze_false_positive(scheme_dict, reason)

        # Save to DB
        record = FalsePositiveFeedback(
            scheme_id=scheme_id,
            user_id=user_id,
            reason=reason,
            root_cause=fp_report.root_cause,
            pattern_category=fp_report.pattern_category,
            generalization=fp_report.generalization,
        )
        db.session.add(record)
        db.session.commit()

        # Suggest a tag fix if possible
        suggested_tag = fp_analyzer.suggest_tag_fix(fp_report.pattern_category, scheme_dict)

        return jsonify({
            'message':         'Report submitted. Thank you for improving the system.',
            'root_cause':      fp_report.root_cause,
            'pattern':         fp_report.pattern_category,
            'suggested_fix':   fp_report.generalization,
            'suggested_tag':   suggested_tag.to_dict() if suggested_tag else None,
        }), 201

    @app.route('/api/admin/false-positives/analysis', methods=['GET'])
    def get_false_positive_analysis():
        """Task 4 & 6: Admin view of FP patterns and generalization opportunities."""
        if session.get('user_type') != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        reports = FalsePositiveFeedback.query.order_by(
            FalsePositiveFeedback.reported_at.desc()
        ).all()

        report_dicts = [r.to_dict() for r in reports]
        analysis = fp_analyzer.batch_analyze(report_dicts)

        return jsonify({
            'reports': report_dicts[:50],
            'analysis': analysis,
        }), 200

    @app.route('/api/admin/false-positives/<int:report_id>/apply-fix', methods=['POST'])
    def apply_false_positive_fix(report_id):
        """
        Task 4: Apply the suggested tag fix to update semantic tags
        and generalize across similar schemes.
        """
        if session.get('user_type') != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        report = FalsePositiveFeedback.query.get_or_404(report_id)
        scheme = Scheme.query.get(report.scheme_id)
        if not scheme:
            return jsonify({'error': 'Scheme not found'}), 404

        scheme_dict = scheme.to_dict()
        scheme_dict['id'] = scheme.id

        suggested_tag = fp_analyzer.suggest_tag_fix(report.pattern_category, scheme_dict)
        if not suggested_tag:
            return jsonify({'message': 'No automatic fix available for this pattern'}), 200

        # Update or create semantic tag record for this scheme
        tag_record = SchemeSemanticTag.query.filter_by(scheme_id=report.scheme_id).first()
        if tag_record:
            existing_profile = SchemeTagProfile.from_json(tag_record.tags_json)
            # Avoid duplicates
            existing_tag_keys = {t.tag for t in existing_profile.tags}
            if suggested_tag.tag not in existing_tag_keys:
                existing_profile.tags.append(suggested_tag)
                tag_record.tags_json = existing_profile.to_json()
                tag_record.version += 1
        else:
            from semantic_tagger import SchemeTagProfile as STP
            new_profile = STP(
                scheme_id=report.scheme_id,
                scheme_name=scheme.name,
                tags=[suggested_tag],
                extraction_method='fix',
                extracted_at=datetime.now(timezone.utc).isoformat(),
            )
            tag_record = SchemeSemanticTag(
                scheme_id=report.scheme_id,
                tags_json=new_profile.to_json(),
                extraction_method='fix',
            )
            db.session.add(tag_record)

        report.status = 'fixed'
        db.session.commit()

        return jsonify({
            'message':       'Fix applied and semantic tags updated',
            'applied_tag':   suggested_tag.to_dict(),
            'scheme_id':     report.scheme_id,
        }), 200

    # ── Task 5: Profile Schema Improvement ──────────────────────────────────

    @app.route('/api/admin/profile-schema/missing-fields', methods=['GET'])
    def get_missing_field_recommendations():
        """Task 5: Get recommendations for new profile fields based on match failures."""
        if session.get('user_type') != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        logs = MissingFieldLog.query.order_by(MissingFieldLog.logged_at.desc()).all()
        log_dicts = [l.to_dict() for l in logs]

        aggregated = profile_advisor.aggregate_missing_fields(log_dicts)
        form_additions = profile_advisor.get_form_additions(aggregated)

        return jsonify({
            'total_log_entries':   len(log_dicts),
            'unique_missing_fields': len(aggregated),
            'top_recommendations': aggregated[:10],
            'form_additions':      form_additions,
        }), 200

    # ── Task 6: Continuous Learning ──────────────────────────────────────────

    @app.route('/api/admin/learning/run-cycle', methods=['POST'])
    def run_learning_cycle():
        """
        Task 6: Trigger a continuous learning cycle.
        Analyzes FPs, identifies low-coverage schemes, and produces recommendations.
        """
        if session.get('user_type') != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        learner = ContinuousLearner(ai_extractor=AITagExtractor(gemini_model))

        fp_reports = [r.to_dict() for r in FalsePositiveFeedback.query.all()]

        # Get schemes with no or empty tags
        tagged_ids = {st.scheme_id for st in SchemeSemanticTag.query.all()}
        untagged = Scheme.query.filter(~Scheme.id.in_(tagged_ids)).limit(100).all()
        untagged_dicts = [{**s.to_dict(), 'id': s.id} for s in untagged]

        result = learner.run_learning_cycle(fp_reports, untagged_dicts)

        # Log the cycle
        cycle_log = LearningCycleLog(
            fp_count=len(fp_reports),
            patterns_found=result.get('false_positive_analysis', {}).get('unique_patterns', 0),
            recommendations_json=json.dumps(result.get('recommendations', [])),
            triggered_by=request.json.get('triggered_by', 'manual') if request.json else 'manual',
        )
        db.session.add(cycle_log)
        db.session.commit()

        return jsonify(result), 200

    @app.route('/api/admin/learning/history', methods=['GET'])
    def get_learning_history():
        """Task 6: Get history of learning cycles."""
        if session.get('user_type') != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        logs = LearningCycleLog.query.order_by(LearningCycleLog.run_at.desc()).limit(20).all()
        return jsonify({'cycles': [l.to_dict() for l in logs]}), 200

    # ── Task 7: Contextual AI Assistant ─────────────────────────────────────

    CONTEXTUAL_ASSIST_PROMPT = """You are the YojanaMitra AI assistant embedded in a government scheme portal.

A user has selected text on the page and triggered the "{action}" action.

SELECTED TEXT (grounded context — base your entire response on this):
"{selected_text}"

USER PROFILE (sanitized — no PII):
{profile_json}

TASK: {task_instruction}

STRICT REQUIREMENTS:
1. Stay grounded in the selected text — do NOT fabricate information
2. Be concise (3-6 sentences max for explain/summarize, 4-8 for eligibility)
3. Use plain language — avoid bureaucratic jargon
4. For eligibility checks: extract conditions STRICTLY from selected text, then compare with profile
5. If a condition FAILS → user is NOT eligible; do not assume missing data is favorable
6. Never expose PII — refer to user as "you" not by name
7. Do not hallucinate scheme names, amounts, or dates not present in selected text

{extra_instructions}"""

    ACTION_INSTRUCTIONS = {
        'explain': (
            "TASK: Explain the selected text in simple, plain language that anyone can understand. "
            "Break down any government jargon, technical terms, or complex conditions.",
            ""
        ),
        'summarize': (
            "TASK: Summarize the key points of the selected text in 3-4 bullet points. "
            "Focus on: who is eligible, what benefit is given, and how to apply (if mentioned).",
            ""
        ),
        'eligibility': (
            "TASK: Extract ALL eligibility conditions from the selected text. "
            "Compare EACH condition strictly against the user's profile. "
            "Mark the user as eligible ONLY if ALL conditions are met. "
            "If profile data is missing for a condition, state it as 'Cannot verify'.",
            'Return as JSON: {"verdict": "ELIGIBLE"|"NOT_ELIGIBLE"|"POSSIBLY_ELIGIBLE", '
            '"confidence": 0-100, "reasoning": "...", "key_factors": ["...", "..."], '
            '"missing_info_that_could_change_verdict": ["field1"]}'
        ),
        'ask': (
            "TASK: Answer the user's question using the selected text as context. "
            "If the answer is not in the selected text, say so clearly.",
            ""
        ),
    }

    @app.route('/api/contextual-assist', methods=['POST'])
    def contextual_assist():
        """
        Task 7 & 8: Contextual AI assistant endpoint.
        Receives selected text + sanitized user profile.
        Returns AI response grounded in selected text.
        """
        data = request.json or {}

        selected_text = (data.get('selected_text') or '').strip()[:1000]
        user_action   = data.get('user_action', 'explain').lower()
        question      = (data.get('question') or '').strip()[:300]
        raw_profile   = data.get('user_profile', {})

        if not selected_text:
            return jsonify({'error': 'No text selected'}), 400

        if user_action not in ACTION_INSTRUCTIONS:
            user_action = 'explain'

        # Task 8: Re-sanitize profile even if frontend already did
        safe_profile = _sanitize_profile_strict(raw_profile)

        if not gemini_model:
            return jsonify({
                'response': _contextual_fallback(user_action, selected_text, question),
                'powered_by': 'fallback',
            }), 200

        task_instruction, extra = ACTION_INSTRUCTIONS[user_action]
        if user_action == 'ask' and question:
            task_instruction = f"TASK: Answer this question: \"{question}\" using the selected text as context."

        prompt = CONTEXTUAL_ASSIST_PROMPT.format(
            action=user_action.capitalize(),
            selected_text=selected_text,
            profile_json=json.dumps(safe_profile, indent=2) if safe_profile else '{}',
            task_instruction=task_instruction,
            extra_instructions=extra,
        )

        try:
            response = gemini_model.generate_content(prompt)
            text = response.text.strip()

            # For eligibility action, try to parse JSON verdict
            if user_action == 'eligibility':
                try:
                    json_match = re.search(r'\{.*\}', text, re.DOTALL)
                    if json_match:
                        verdict_data = json.loads(json_match.group())
                        return jsonify({
                            **verdict_data,
                            'powered_by': 'gemini',
                            'privacy_confirmed': True,
                        }), 200
                except Exception:
                    pass

            return jsonify({
                'response':     text,
                'powered_by':   'gemini',
                'privacy_confirmed': True,
            }), 200

        except Exception as e:
            error_str = str(e)
            logger.error(f"Contextual assist error: {error_str}")

            if '429' in error_str or 'quota' in error_str.lower():
                return jsonify({
                    'response': '⚠ AI is momentarily busy. Please try again in a moment.',
                    'powered_by': 'quota_limit',
                }), 200

            return jsonify({
                'response': _contextual_fallback(user_action, selected_text, question),
                'powered_by': 'fallback',
            }), 200

    # ── Task 8: Privacy validation endpoint ────────────────────────────────

    @app.route('/api/privacy/validate-profile', methods=['POST'])
    def validate_profile_privacy():
        """
        Task 8: Validate that a profile payload contains no PII before external use.
        Returns sanitized version and a list of removed fields.
        """
        raw_profile = request.json or {}
        safe_profile = _sanitize_profile_strict(raw_profile)

        removed_fields = [k for k in raw_profile if k not in safe_profile]

        return jsonify({
            'sanitized_profile': safe_profile,
            'removed_fields':    removed_fields,
            'safe_field_count':  len(safe_profile),
            'pii_removed':       len(removed_fields),
            'privacy_status':    'clean' if not removed_fields else 'sanitized',
        }), 200


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _build_raw_profile(user) -> dict:
    """Build raw profile dict from User ORM object."""
    from app import normalize_education_level, normalize_is_student  # Circular import safe here
    return {
        "user_id":           str(user.id),
        "age":               user.age,
        "gender":            (user.gender or "").lower().strip(),
        "state":             user.state or "",
        "district":          user.district or "",
        "income_annual":     user.income or 0,
        "is_bpl":            str(user.ration_card_type or "").lower() in ["bpl", "antyodaya", "aay"],
        "ration_card_type":  (user.ration_card_type or "none").lower(),
        "occupation":        [user.occupation] if user.occupation else [],
        "is_farmer":         user.is_farmer == "Yes",
        "is_self_employed":  str(user.employment_status or "").lower() in ["self-employed", "self employed"],
        "is_govt_employee":  str(user.occupation or "").lower() in ["government employee", "govt employee"],
        "is_income_taxpayer": False,
        "is_student":        normalize_is_student(user.education_status, user.employment_status,
                                                   user.highest_education_level or user.education),
        "land_owned_acres":  user.land_size_acres or 0.0,
        "father_occupation": (user.father_occupation or "").lower(),
        "mother_occupation": (user.mother_occupation or "").lower(),
        "caste_category":    (user.caste or "general").lower(),
        "religion":          (user.religion or "").lower(),
        "is_minority":       user.minority_status == "Yes",
        "is_disabled":       user.disability == "Yes",
        "disability_percentage": user.disability_percentage or 0,
        "is_widow":          user.is_widow_single_woman == "Yes",
        "is_abandoned_woman": user.is_widow_single_woman == "Yes",
        "is_senior_citizen": user.is_senior_citizen == "Yes",
        "is_orphan":         user.is_orphan == "Yes",
        "is_tribal":         user.is_tribal == "Yes",
        "marital_status":    (user.marital_status or "single").lower(),
        "residence":         (user.residence or "").lower(),
        "education_level":   _normalize_edu(user),
        "has_aadhaar":       user.aadhaar_available == "Yes",
        "has_bank_account":  user.bank_account_available == "Yes",
        "has_pan":           False,
        "domicile_status":   user.domicile_status,
        "family_type":       user.family_type,
        "total_family_members": user.total_family_members,
        "is_head_of_family": user.is_head_of_family,
        "annual_family_income": user.annual_family_income,
        "income_slab":       user.income_slab,
        "income_certificate_available": user.income_certificate_available,
        "employment_status": user.employment_status,
        "ews_status":        user.ews_status == "Yes",
        "ration_card_available": user.ration_card_available,
        "owns_land":         user.own_agricultural_land == "Yes",
    }


def _normalize_edu(user) -> str:
    """Normalize education level from user object."""
    raw = user.highest_education_level or user.education or ""
    raw_lower = raw.lower()
    if "phd" in raw_lower or "doctorate" in raw_lower:   return "phd"
    if any(x in raw_lower for x in ["postgrad", "post grad", "master", "mba", "mtech", "pg "]):
        return "postgrad"
    if any(x in raw_lower for x in ["be", "btech", "bsc", "bachelor", "degree", "graduation", "college"]):
        return "graduation"
    if "diploma" in raw_lower or "polytechnic" in raw_lower or "iti" in raw_lower:
        return "diploma"
    if any(x in raw_lower for x in ["12th", "hsc", "puc", "class 12"]):
        return "secondary"
    if any(x in raw_lower for x in ["10th", "sslc", "class 10"]):
        return "primary"
    return "none"


def _contextual_fallback(action: str, text: str, question: str) -> str:
    """Offline fallback responses when Gemini is unavailable."""
    if action == 'explain':
        return (
            "This section describes eligibility criteria for a government scheme. "
            "It outlines who qualifies based on age, income, caste, or occupation. "
            "Complete your profile for a personalized eligibility check."
        )
    if action == 'summarize':
        return (
            "Key points from the selected text:\n"
            "• Describes eligibility or benefits of a government scheme\n"
            "• May include age, income, or category-based criteria\n"
            "• Visit the official portal link to apply"
        )
    if action == 'eligibility':
        return "Unable to check eligibility offline. Please ensure your profile is complete and try again."
    if action == 'ask':
        return f"I couldn't process your question about \"{question}\" right now. Please try again shortly."
    return "AI assistant is temporarily unavailable. Please try again in a moment."
