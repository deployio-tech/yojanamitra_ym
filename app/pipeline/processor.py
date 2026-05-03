"""
pipeline/processor.py
Full 8-step scheme processing pipeline.
Step 1: Raw ingestion normalisation
Step 2: AI condition extraction
Step 3: Field normalisation
Step 4: Quality scoring
Step 5: Expiry detection
Step 6: Duplicate detection
Step 7: Validation pass
Step 8: Publish or queue for admin
"""
import json
import logging
import re
from datetime import date, timezone, datetime

log = logging.getLogger(__name__)


class PipelineProcessor:

    def __init__(self, extractor, config=None):
        self.extractor = extractor           # GeminiExtractor instance
        self.cfg = config or {}
        self.quality_threshold  = self.cfg.get("QUALITY_SCORE_THRESHOLD", 0.45)
        self.dup_threshold      = self.cfg.get("DUPLICATE_SIMILARITY_THRESHOLD", 0.88)
        self.conf_threshold     = self.cfg.get("EXTRACTION_CONFIDENCE_THRESHOLD", 0.60)

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1: Raw ingestion normalisation
    # ─────────────────────────────────────────────────────────────────────────

    def step1_normalise(self, raw_text: str) -> str:
        if not raw_text:
            return ""
        text = re.sub(r"\s+", " ", raw_text)
        text = re.sub(r"<[^>]+>", " ", text)   # strip HTML tags
        return text.strip()

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2 + 3: Extract + normalise
    # ─────────────────────────────────────────────────────────────────────────

    def step2_extract(self, normalised_text: str):
        return self.extractor.extract(normalised_text)

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4: Quality scoring
    # ─────────────────────────────────────────────────────────────────────────

    def step4_quality(self, conditions: list, raw_text: str) -> float:
        from app.pipeline.extractor import compute_quality_score
        return compute_quality_score(conditions, raw_text)

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5: Expiry detection
    # ─────────────────────────────────────────────────────────────────────────

    def step5_expiry(self, raw_text: str):
        from app.pipeline.extractor import detect_expiry
        return detect_expiry(raw_text)

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 6: Duplicate detection
    # ─────────────────────────────────────────────────────────────────────────

    def step6_duplicates(self, scheme, all_schemes: list) -> list:
        from app.pipeline.extractor import detect_duplicates
        return detect_duplicates(scheme, all_schemes, self.dup_threshold)

    # ─────────────────────────────────────────────────────────────────────────
    # FILTER: Clean conditions before validation
    # ─────────────────────────────────────────────────────────────────────────

    def filter_conditions(self, conditions: list) -> list:
        """
        Filter and clean conditions before validation/saving.
        
        Priority order:
        1. Normalize value
        2. Skip "all/any" (highest priority)
        3. Field-specific confidence threshold
        4. Deduplicate
        """
        filtered = []
        seen = set()
        CRITICAL_FIELDS = ["gender", "age", "annual_income", "category"]

        for c in conditions:
            # Step 1: Normalize value FIRST
            field = c.get("field")
            value = c.get("value")
            confidence = c.get("confidence", 0)

            if value is None:
                continue

            if isinstance(value, list):
                val_norm = [str(v).strip().lower() for v in value]
            else:
                val_norm = str(value).strip().lower()

            # Step 2: Skip "all/any" (HIGHEST PRIORITY - before confidence)
            skip_values = ["all", "any", "everyone", "no restriction"]
            if isinstance(val_norm, str):
                if val_norm in skip_values:
                    continue
            elif isinstance(val_norm, list):
                if all(v in skip_values for v in val_norm):
                    continue

            # Step 3: Basic field validation
            operator = c.get("operator")
            if not field or not operator:
                continue

            # Step 4: Field-specific confidence threshold
            min_conf = 0.5 if field in CRITICAL_FIELDS else 0.7
            if confidence < min_conf:
                continue

            # Step 4b: Guard against is_disabled hallucination
            if field == "is_disabled" and confidence < 0.8:
                print(f"[FILTER] is_disabled with low confidence ({confidence}) - skipping")
                continue

            # Step 5: Deduplication (list-safe key) - use normalized for key
            if isinstance(val_norm, list):
                key = (field, operator, tuple(val_norm))
            else:
                key = (field, operator, val_norm)

            if key in seen:
                continue
            seen.add(key)

            # Step 6: Suspicious condition logging (no drop)
            if field in ["is_disabled", "is_minority", "is_tribal"]:
                print(f"[WARN] Suspicious condition: {field} = {value}")

            # Step 7: Keep original value (don't overwrite with normalized string)
            # val_norm is for deduplication only, not for storage
            filtered.append(c)

        return filtered

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 7: Validation
    # ─────────────────────────────────────────────────────────────────────────

    def step7_validate(self, conditions: list) -> list:
        """
        Returns list of (issue_description, severity) tuples.
        """
        issues = []
        age_min = age_max = None
        income_val = None

        for c in conditions:
            f = c.get("field", "")
            op = c.get("operator", "")
            v = c.get("value")

            if f == "age":
                try:
                    if op == "gte":
                        age_min = float(v)
                    elif op == "lte":
                        age_max = float(v)
                    elif op == "range" and isinstance(v, list):
                        age_min, age_max = float(v[0]), float(v[1])
                except Exception:
                    pass

            if f == "annual_income" and op == "lte":
                try:
                    income_val = float(v)
                except Exception:
                    pass

        if age_min is not None and age_max is not None and age_min > age_max:
            issues.append((
                f"Inconsistent age range: min {age_min} > max {age_max}",
                "warning"
            ))

        # Suspicious: very high income limit with welfare target groups
        # (not a hard error, just a warning)
        if income_val and income_val > 5_000_000:
            issues.append((
                f"Unusually high income limit ({income_val}). Verify extraction.",
                "warning"
            ))

        return issues

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 8: Commit to DB
    # ─────────────────────────────────────────────────────────────────────────

    def step8_commit(self, scheme, conditions, quality_score, expiry_date,
                     duplicates, validation_issues, extraction_version,
                     extraction_error=None):
        from app import db, Condition, SchemeFlag

        now = datetime.now(timezone.utc)
        blocking_flags = []

        # Handle extraction failure
        if extraction_error or not conditions:
            scheme.extraction_status = "failed"
            scheme.is_active = False
            flag = SchemeFlag(
                scheme_id=scheme.id,
                flag_type="extraction_failed",
                reason=extraction_error or "No conditions extracted",
                severity="block",
                auto_raised=True,
            )
            db.session.add(flag)
            db.session.commit()
            log.warning(f"Scheme {scheme.id} extraction failed: {extraction_error}")
            return False

        scheme.extraction_version = extraction_version
        scheme.quality_score = quality_score
        scheme.expires_at = expiry_date

        # Remove old conditions
        Condition.query.filter_by(scheme_id=scheme.id).delete()

        # Insert new conditions
        for c in conditions:
            conf = float(c.get("confidence", 1.0))
            is_ambiguous = conf < self.conf_threshold
            ctype = c.get("condition_type", "soft")
            # Force ambiguous conditions to soft
            if is_ambiguous and ctype == "hard":
                ctype = "soft"

            cond = Condition(
                scheme_id=scheme.id,
                field=c.get("field", "unknown"),
                operator=c.get("operator", "eq"),
                value=json.dumps(c.get("value")),
                condition_type=ctype,
                confidence=conf,
                source_fragment=c.get("source_fragment", ""),
                is_ambiguous=is_ambiguous,
                notes=c.get("notes", ""),
            )
            db.session.add(cond)
            if is_ambiguous:
                flag = SchemeFlag(
                    scheme_id=scheme.id,
                    flag_type="ambiguous",
                    reason=f"Condition '{c.get('field')}' extracted with confidence {conf:.2f}",
                    severity="warning",
                    auto_raised=True,
                )
                db.session.add(flag)

        # Quality flag
        if quality_score < self.quality_threshold:
            f = SchemeFlag(
                scheme_id=scheme.id,
                flag_type="low_quality",
                reason=f"Quality score {quality_score:.2f} below threshold {self.quality_threshold}",
                severity="block",
                auto_raised=True,
            )
            db.session.add(f)
            blocking_flags.append("low_quality")

        # Expiry flag
        if expiry_date and expiry_date < date.today():
            f = SchemeFlag(
                scheme_id=scheme.id,
                flag_type="expired",
                reason=f"Scheme expired on {expiry_date}",
                severity="block",
                auto_raised=True,
            )
            db.session.add(f)
            blocking_flags.append("expired")

        # Duplicate flags
        for dup_id, sim in duplicates:
            f = SchemeFlag(
                scheme_id=scheme.id,
                flag_type="duplicate",
                reason=f"Similarity {sim:.0%} with scheme {dup_id}",
                severity="warning",
                auto_raised=True,
            )
            db.session.add(f)

        # Validation issues
        for issue_text, severity in validation_issues:
            f = SchemeFlag(
                scheme_id=scheme.id,
                flag_type="inconsistent",
                reason=issue_text,
                severity=severity,
                auto_raised=True,
            )
            db.session.add(f)

        # Final status
        if blocking_flags:
            scheme.extraction_status = "flagged"
            scheme.is_active = False
        else:
            scheme.extraction_status = "extracted"
            scheme.is_active = True

        scheme.updated_at = now
        db.session.commit()
        return scheme.is_active

    # ─────────────────────────────────────────────────────────────────────────
    # FULL PIPELINE RUN
    # ─────────────────────────────────────────────────────────────────────────

    def run(self, scheme, all_active_schemes=None):
        """
        Run the full 8-step pipeline for a single scheme.
        Returns True if published, False if flagged/failed.
        """
        from app import db

        log.info(f"Pipeline START: {scheme.name} ({scheme.id})")

        # Step 1
        normalised = self.step1_normalise(scheme.raw_text or "")
        if not normalised:
            scheme.extraction_status = "failed"
            db.session.commit()
            log.warning(f"Scheme {scheme.id} has no raw_text — aborting pipeline")
            return False

        # Step 2 + 3
        conditions, ext_version, err = self.step2_extract(normalised)

        # FILTER: Clean conditions (before validation)
        conditions = self.filter_conditions(conditions)

        # Step 4
        quality = self.step4_quality(conditions, normalised)

        # Step 5
        expiry = self.step5_expiry(normalised)

        # Step 6
        dupes = self.step6_duplicates(scheme, all_active_schemes or [])

        # Step 7
        issues = self.step7_validate(conditions)

        # Step 8
        published = self.step8_commit(
            scheme, conditions, quality, expiry,
            dupes, issues, ext_version, err
        )

        log.info(f"Pipeline END: {scheme.name} → {'published' if published else 'flagged'}")
        return published
