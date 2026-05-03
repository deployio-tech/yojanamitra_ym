"""
pipeline/__init__.py
Pipeline factory and nightly scheduler.
"""
import logging
from app.pipeline.extractor  import GeminiExtractor
from app.pipeline.processor  import PipelineProcessor

log = logging.getLogger(__name__)


def get_pipeline(app):
    # Hardcoded API key - same as in root app.py
    api_key = 'PASTE_YOUR_GEMINI_API_KEY_HERE'
    key_preview = api_key[:10] if api_key else "NONE"
    print(f"=== PIPELINE: Using API key: {key_preview}... ===")
    extractor = GeminiExtractor(
        api_key=api_key or "",
        model_name="gemini-flash-latest",
    )
    return PipelineProcessor(extractor, config=app.config)


def run_pipeline_for_scheme(scheme_id: str, app):
    """Run pipeline for a single scheme by ID. Safe to call from any context."""
    with app.app_context():
        from app import db, Scheme
        scheme = Scheme.query.get(scheme_id)
        if not scheme:
            log.error(f"Scheme {scheme_id} not found")
            return False
        pipeline = get_pipeline(app)
        all_active = Scheme.query.filter_by(is_active=True).all()
        return pipeline.run(scheme, all_active)


def run_nightly_batch(app):
    """Process all pending schemes. Called by scheduler."""
    with app.app_context():
        from app import Scheme
        pending = Scheme.query.filter(
            Scheme.extraction_status.in_(["pending", "failed"])
        ).all()
        log.info(f"Nightly batch: {len(pending)} schemes to process")
        pipeline = get_pipeline(app)
        all_active = Scheme.query.filter_by(is_active=True).all()
        for scheme in pending:
            try:
                pipeline.run(scheme, all_active)
            except Exception as e:
                log.error(f"Pipeline error for {scheme.id}: {e}")

        # Also mark expired active schemes
        from datetime import date
        from app import db
        expired = Scheme.query.filter(
            Scheme.is_active == True,
            Scheme.expires_at < date.today()
        ).all()
        for s in expired:
            s.is_active = False
            log.info(f"Auto-expired: {s.name}")
        db.session.commit()
        log.info("Nightly batch complete")


def init_scheduler(app):
    if not app.config.get("SCHEDULER_ENABLED", False):
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        hour = app.config.get("PIPELINE_BATCH_HOUR", 2)
        scheduler.add_job(
            func=run_nightly_batch,
            args=[app],
            trigger="cron",
            hour=hour,
            minute=0,
            id="nightly_pipeline",
            replace_existing=True,
        )
        scheduler.start()
        log.info(f"Scheduler started — nightly pipeline at {hour}:00")
        return scheduler
    except Exception as e:
        log.error(f"Scheduler init failed: {e}")
