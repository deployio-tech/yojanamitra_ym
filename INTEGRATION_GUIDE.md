# YojanaMitra — Enhanced Intelligence Engine
## Integration Guide: All 8 Tasks

---

## Files Delivered

| File | Tasks | Description |
|------|-------|-------------|
| `semantic_tagger.py` | 1, 2, 4, 6 | Semantic pre-tagging, matching validator, FP generalizer, continuous learner |
| `confidence_invoker.py` | 3, 5, 8 | Confidence scoring, AI invocation, profile advisor, PII sanitizer |
| `contextual_assistant.js` | 7 | Frontend text-selection popup with AI actions |
| `app_enhancements.py` | All | Flask routes, DB models, API endpoints |

---

## Step 1 — Add DB Models to app.py

After `db = SQLAlchemy(app)`, add:

```python
from app_enhancements import create_enhancement_models
enhancement_models = create_enhancement_models(db)
SchemeSemanticTag      = enhancement_models['SchemeSemanticTag']
FalsePositiveFeedback  = enhancement_models['FalsePositiveFeedback']
MissingFieldLog        = enhancement_models['MissingFieldLog']
LearningCycleLog       = enhancement_models['LearningCycleLog']
```

Then in `init_db()`, add after `db.create_all()`:
```python
# Ensure enhancement tables exist
SchemeSemanticTag.__table__.create(db.engine, checkfirst=True)
FalsePositiveFeedback.__table__.create(db.engine, checkfirst=True)
MissingFieldLog.__table__.create(db.engine, checkfirst=True)
LearningCycleLog.__table__.create(db.engine, checkfirst=True)
```

---

## Step 2 — Register Enhancement Routes

After all existing routes in app.py, add:

```python
from app_enhancements import register_enhancement_routes
register_enhancement_routes(
    app=app,
    db=db,
    gemini_model=model,       # Your existing Gemini model variable
    models=enhancement_models,
    Scheme=Scheme,
    User=User,
)
```

---

## Step 3 — Add Semantic Tag Validation to Recommendations Pipeline

In `get_recommendations()` (the `/api/recommendations` route), before returning results, add semantic validation:

```python
from semantic_tagger import SemanticMatchValidator, SchemeTagProfile
from confidence_invoker import ConfidenceScorer

semantic_validator = SemanticMatchValidator()
scorer = ConfidenceScorer()

# Filter recommendations through semantic validator
filtered_recommendations = []
for rec in recommendations:
    tag_record = SchemeSemanticTag.query.filter_by(scheme_id=rec['id']).first()
    if tag_record:
        try:
            tp = SchemeTagProfile.from_json(tag_record.tags_json)
            passes, violations, delta = semantic_validator.validate(tp.tags, raw_profile)
            if not passes:
                continue  # Task 2: semantic failure = NOT eligible
            rec['semanticConfidence'] = delta
        except Exception:
            pass
    filtered_recommendations.append(rec)
```

---

## Step 4 — Add Contextual Assistant to Frontend

In `index.html` and `all_schemes.html`, before `</body>`:

```html
<script src="/contextual_assistant.js"></script>
```

The script auto-initializes. It reads `window.currentUser.profile` for the sanitized profile. Ensure this is set after login:

```javascript
// In your login success handler:
window.currentUser = { profile: data.user.profile };
```

---

## New API Endpoints

### Task 1 — Semantic Tagging
```
POST /api/admin/semantic-tags/batch
     Body: { "only_untagged": true }
     → Triggers background batch tagging

GET  /api/admin/semantic-tags/<scheme_id>
     → Get tags for a specific scheme

POST /api/admin/semantic-tags/<scheme_id>
     → Tag a single scheme on-demand

GET  /api/admin/semantic-tags/coverage
     → Coverage statistics
```

### Task 3 — Confidence Check
```
POST /api/schemes/<scheme_id>/confidence-check
     → Returns confidence score + optional AI validation
     → Requires login
```

### Task 4 — False Positive Reporting
```
POST /api/feedback/false-positive
     Body: { "scheme_id": 123, "reason": "I am not eligible for this" }
     → Reports FP, analyzes root cause

GET  /api/admin/false-positives/analysis
     → Aggregated FP patterns (admin)

POST /api/admin/false-positives/<report_id>/apply-fix
     → Apply suggested semantic tag fix (admin)
```

### Task 5 — Profile Schema Recommendations
```
GET  /api/admin/profile-schema/missing-fields
     → Aggregated missing field analysis + form addition recommendations
```

### Task 6 — Continuous Learning
```
POST /api/admin/learning/run-cycle
     → Trigger a learning cycle

GET  /api/admin/learning/history
     → Learning cycle history
```

### Task 7 — Contextual Assistant
```
POST /api/contextual-assist
     Body: {
       "selected_text": "...",
       "user_action": "explain|summarize|eligibility|ask",
       "question": "Optional question for 'ask' action",
       "user_profile": { sanitized profile object }
     }
     → Returns AI-powered response
```

### Task 8 — Privacy Validation
```
POST /api/privacy/validate-profile
     Body: { raw profile object }
     → Returns sanitized version + removed PII fields
```

---

## Privacy Guarantee (Task 8)

The system implements a two-layer PII protection:

1. **Frontend**: `contextual_assistant.js` filters the profile client-side before sending
2. **Backend**: `_sanitize_profile_strict()` in `confidence_invoker.py` re-sanitizes before every AI call

**Fields NEVER sent to AI:**
- `name`, `email`, `mobile`, `phone`
- `aadhaar`, `aadhaar_number`, `pan`, `pan_number`
- `voter_id`, `passport`, `bank_account_number`
- `dob`, `date_of_birth`, `address`
- `aadhaar_linked_bank`, `mobile_linked_bank`
- Any field containing `id`, `number`, `linked` (document identifiers)

**Fields sent to AI (demographics + eligibility flags only):**
- `age`, `gender`, `state`, `district`, `residence`
- `education_level`, `caste_category`, `religion`
- `income_annual`, `is_bpl`, `ration_card_type`
- Status flags: `is_farmer`, `is_student`, `is_disabled`, etc.

---

## Architecture Overview

```
User Request
     │
     ▼
[Rule Engine v2.0]          ← Existing (deterministic)
     │
     ▼
[Semantic Tag Validator]    ← Task 2 (semantic_tagger.py)
  Tags from DB ──────────── Task 1 (batch pre-tagged by AI)
     │
     ▼
[Confidence Scorer]         ← Task 3 (confidence_invoker.py)
     │
     ├── HIGH confidence → Return result
     │
     └── LOW confidence → [AI Fallback Validator]  ← Task 3
                              │
                              ▼
                         Privacy check → Task 8
                         Sanitized profile only

User feedback → [FP Analyzer]     ← Task 4
              → [Pattern Generalizer]
              → Update semantic tags

Background → [Continuous Learner]  ← Task 6
           → [Profile Advisor]     ← Task 5
           → Recommendations

Frontend → [Contextual Assistant]  ← Task 7
         → Text selection popup
         → Privacy-safe profile
```

---

## Running the First Batch Tag

After deployment, trigger initial batch tagging via Admin panel or API:

```bash
curl -X POST https://your-app.onrender.com/api/admin/semantic-tags/batch \
  -H "Content-Type: application/json" \
  -d '{"only_untagged": true}' \
  --cookie "session=<admin_session>"
```

This will:
1. Extract semantic tags for all untagged schemes using Gemini + regex hybrid
2. Store tags in `scheme_semantic_tag` table
3. Enable semantic validation in all future eligibility checks
