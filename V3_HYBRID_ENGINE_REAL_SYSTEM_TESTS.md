# YojanaMitra V3 Hybrid Engine - Real System Test Suite

## Overview

This is a **REAL SYSTEM TEST SUITE** — NOT a mockup test suite. Every test makes actual API calls to your backend, performs real database operations, and integrates with actual Gemini AI.

### What This Tests

✅ **All 6 Phases of the Matching Lifecycle:**
1. Phase 1: Core Database Matching (Hard Filter)
2. Phase 2: Verification Trigger & Memory Retrieval  
3. Phase 3: AI Context Analysis & Question Generation
4. Phase 4: Hybrid UI Modal Rendering
5. Phase 5: Smart Traffic Director (Answer Routing)
6. Phase 6: AI Re-Evaluation Engine

✅ **Real System Components:**
- Flask backend (`/api/*` endpoints)
- SQLite database (actual `yojanamitra.db`)
- Gemini AI integration
- `SchemeClarification` table (UPSERT operations)
- Session management & authentication
- Throttling & safety mechanisms

✅ **Real Data Flow:**
- Actual user signup → profile updates
- Database queries on real scheme data
- AI calls to Gemini with real prompts
- Database state changes (UPSERT into `scheme_clarifications`)
- 6-phase end-to-end user journey

---

## Prerequisites

### 1. Backend Running

Your Flask backend must be running:

```bash
# Terminal 1: Start the Flask server
python app.py
```

The default URL is: `http://localhost:5000`

If running on a different host/port, edit `run_v3_hybrid_tests.py`:
```python
class TestConfig:
    API_BASE_URL = "http://your-custom-url:port"
```

### 2. Database Ready

The SQLite database must have:
- ✓ `user` table (users created during tests)
- ✓ `scheme` table (at least 50 schemes)
- ✓ `scheme_clarifications` table (for storing answers)
- ✓ All related condition/eligibility tables

Check database:
```bash
python -c "import sqlite3; conn = sqlite3.connect('yojanamitra.db'); c = conn.cursor(); c.execute('SELECT COUNT(*) FROM scheme'); print('Schemes:', c.fetchone()[0])"
```

### 3. Gemini AI Configured

Your `app.py` must have `GEMINI_API_KEY` set:
```python
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-key-here")
genai.configure(api_key=GEMINI_API_KEY)
```

### 4. Python Environment

```bash
# Install pytest and dependencies
pip install pytest requests
```

---

## Running the Tests

### Quick Start: Run All Tests

```bash
# Start backend first (if not already running)
python app.py &

# Wait 5 seconds for backend to start
sleep 5

# Run complete test suite
python run_v3_hybrid_tests.py
```

This will:
1. ✓ Check system readiness (API, DB, AI)
2. ✓ Run all 22 real system tests
3. ✓ Generate detailed report
4. ✓ Save results to `report_v3_hybrid_complete.json`

### Run Individual Phases

```bash
# Phase 1: Database Matching
python run_v3_hybrid_tests.py --phase 1

# Phase 3: AI Context Analysis
python run_v3_hybrid_tests.py --phase 3

# Phase 6: Re-Evaluation Engine
python run_v3_hybrid_tests.py --phase 6
```

### Run Full Lifecycle Only

```bash
# Complete 6-phase user journey
python run_v3_hybrid_tests.py --full
```

This is the **crown test** — farmer enters → answers questions → becomes ELIGIBLE.

### Run with pytest Directly

```bash
# Run all tests with verbose output
pytest tests/test_v3_hybrid_real_system.py -v

# Run specific test class
pytest tests/test_v3_hybrid_real_system.py::TestPhase1_RealDatabaseMatching -v

# Run specific test with print statements
pytest tests/test_v3_hybrid_real_system.py::TestFullLifecycle_EndToEnd::test_FL_001_Complete_Journey_FarmerToEligible -v -s
```

---

## Test Structure

### Phase 1: Core Database Matching

**File:** `tests/test_v3_hybrid_real_system.py::TestPhase1_RealDatabaseMatching`

**Tests:**
- `P1_001`: Income-based filtering 
- `P1_002`: State-based exclusions
- `P1_003`: Age-based cutoff

**What it validates:**
- Deterministic database rules engine
- Income threshold enforcement
- Geographic filtering
- Match score calculation

**Real API calls:**
- `POST /api/signup` → Create test user
- `POST /api/login` → Authenticate
- `POST /api/update-profile` → Update demographics
- `GET /api/recommendations` → Get matched schemes

**Database operations:**
- Read from `scheme` table
- Read from `condition` table (eligibility rules)
- Write to `user` table (profile updates)

---

### Phase 2: Verification Trigger

**File:** `tests/test_v3_hybrid_real_system.py::TestPhase2_VerificationTrigger`

**Tests:**
- `P2_001`: First verification (no prior history)
- `P2_002`: Subsequent verification (with history)

**What it validates:**
- `SchemeClarification` table queries
- Prior answer retrieval
- Iteration count tracking

**Real API calls:**
- `GET /api/readiness/questions` (indirectly through Phase 3)

**Database operations:**
- Read from `scheme_clarifications` (first call returns empty)
- Read from `scheme_clarifications` (subsequent calls return prior answers)

---

### Phase 3: AI Context Analysis

**File:** `tests/test_v3_hybrid_real_system.py::TestPhase3_AIContextAnalysis`

**Tests:**
- `P3_001`: Gap detection with real Gemini
- `P3_002`: Warning generation for disqualifications

**What it validates:**
- Gemini API integration
- Question generation with MD5 hashing
- Natural language question quality
- Warning flags for edge cases

**Real API calls:**
- `POST /api/readiness/questions` → AI generates questions

**Gemini AI:**
- Real call to `model.generate_content(prompt)`
- Prompt includes user profile + scheme rules
- Response parsed as JSON
- Questions created with stable MD5 hashes

**Database operations:**
- Read user profile (not stored, just sent to AI)
- Read scheme eligibility rules

---

### Phase 4: Hybrid UI

**File:** `tests/test_v3_hybrid_real_system.py::TestPhase4_HybridUI`

**Tests:**
- `P4_001`: Modal rendering validation

**What it validates:**
- Dropdowns for standard fields (state, occupation)
- Textboxes for AI contextual questions
- Question hash visibility in form data

**Note:** Phase 4 is implicit in the tests (UI rendering verified through form structure).

---

### Phase 5: Smart Traffic Director

**File:** `tests/test_v3_hybrid_real_system.py::TestPhase5_SmartTrafficDirector`

**Tests:**
- `P5_001`: Answer splitting (MD5 hash detection)
- `P5_002`: Standard routing to `/api/resolve-questions`
- `P5_003`: Contextual routing to `/api/readiness/re-evaluate`

**What it validates:**
- 32-character MD5 hash detection
- Answer payload splitting logic
- Two-route dispatch (standard vs contextual)

**Real API calls:**
- `POST /api/resolve-questions` → Store standard answers
- `POST /api/readiness/re-evaluate` → Process contextual answers (Phase 6)

**Database operations:**
- Write to `user` table (standard answers)
- Write to `scheme_clarifications` table (contextual answers)

---

### Phase 6: AI Re-Evaluation Engine

**File:** `tests/test_v3_hybrid_real_system.py::TestPhase6_AIReEvaluationEngine`

**Tests:**
- `P6_001`: Database history injection in AI prompt
- `P6_002`: AI verdict generation (ELIGIBLE/INELIGIBLE)
- `P6_003`: SchemeClarification UPSERT
- `P6_004`: Throttling protection (3-iteration max)

**What it validates:**
- Prior answers retrieved from database
- Fresh AI evaluation with complete context
- Verdict generation (ELIGIBLE → 95%+ score)
- Database operations (UPSERT with unique constraint)
- Throttling prevents infinite loops

**Real API calls:**
- `POST /api/readiness/re-evaluate` → AI re-evaluation

**Gemini AI:**
- Real call with extended prompt
- Prompt includes:
  - User profile (sanitized, no PII)
  - Prior clarifications (all previous answers)
  - New user answer
  - Scheme rules & exclusions
- AI responds with verdict JSON
- Response stored in database

**Database operations:**
- Read from `scheme_clarifications` (prior answers)
- Read from `user` (profile context)
- Read from `scheme` (rules)
- UPSERT into `scheme_clarifications` (new answer + AI verdict)

---

### Full Lifecycle: End-to-End

**File:** `tests/test_v3_hybrid_real_system.py::TestFullLifecycle_EndToEnd`

**Crown Test:** `test_FL_001_Complete_Journey_FarmerToEligible`

**Complete 6-Phase Journey:**
```
[PHASE 1] Farmer signup with incomplete profile
          ↓
          Database matching: 2+ schemes marked as "POSSIBLY_ELIGIBLE"
          ↓
[PHASE 2] Verification trigger: Check prior history (empty on first call)
          ↓
[PHASE 3] AI generates 3+ contextual questions about missing fields
          ↓
[PHASE 4] Frontend renders modal with questions
          ↓
[PHASE 5] User submits mixed answers
          - Standard answers → /api/resolve-questions
          - Contextual answers → /api/readiness/re-evaluate
          ↓
[PHASE 6] AI re-evaluates scheme with fresh database context
          - Verdict: "ELIGIBLE"
          - Match score: 95%+
          - Answer stored in SchemeClarification table
          ↓
✅ Farmer journey complete: POSSIBLY_ELIGIBLE → ELIGIBLE
```

---

## Understanding the Test Output

### Console Output Example

```
╔════════════════════════════════════════════════════════════════╗
║         TESTSPRITE V3 HYBRID ENGINE - EXECUTION REPORT         ║
╚════════════════════════════════════════════════════════════════╝

SYSTEM READINESS CHECK
══════════════════════════════════════════════════════════════════
✓ API backend running
✓ Database accessible with required tables
✓ Gemini AI configured
✓ 156 schemes in database
══════════════════════════════════════════════════════════════════
✓ SYSTEM READY FOR TESTING

Running Phase 1 Tests
══════════════════════════════════════════════════════════════════
✓ Phase 1 PASSED

[PHASE 1] Incomplete Profile → Core Database Matching
  ✓ Market analysis complete
    - Eligible: 3
    - Possibly Eligible: 5
    - Total matched: 8

✓ Phase 1: Core Database Matching (Hard Filter)         ✓ PASSED
✓ Phase 2: Verification Trigger & Memory                ✓ PASSED
✓ Phase 3: AI Context Analysis                          ✓ PASSED
✓ Phase 5: Smart Traffic Director                       ✓ PASSED
✓ Phase 6: AI Re-Evaluation Engine                      ✓ PASSED

✓ PRODUCTION READY
```

### Report JSON (`report_v3_hybrid_complete.json`)

```json
{
  "total_phases": 5,
  "phases_passed": 5,
  "phases_failed": 0,
  "passed_phases": [1, 2, 3, 5, 6],
  "failed_phases": [],
  "duration_seconds": 145.32,
  "timestamp": "2026-04-17T10:30:45.123456"
}
```

---

## Troubleshooting

### ❌ Error: "Cannot connect to API"

**Fix:** Make sure Flask backend is running:
```bash
python app.py
```

### ❌ Error: "Database not found"

**Fix:** Ensure `yojanamitra.db` exists and has required tables:
```bash
# Rebuild database if needed
python -c "from app import db, app; app.app_context().push(); db.create_all()"
```

### ❌ Error: "Gemini API not configured"

**Fix:** Set GEMINI_API_KEY environment variable:
```bash
export GEMINI_API_KEY="sk-..." 
python app.py
```

Or update `app.py`:
```python
GEMINI_API_KEY = "your-api-key-here"
```

### ❌ Tests timeout after 5 minutes

**Cause:** AI calls are slow or database queries are frozen
**Fix:** 
- Check if Gemini API is responsive: `curl https://generativelanguage.googleapis.com`
- Check database locks: `ps aux | grep sqlite`
- Increase timeout in `run_v3_hybrid_tests.py` (default 300 seconds)

### ❌ Phase 6 fails with "429 Throttled"

**This is EXPECTED** if you run the same scheme re-evaluate >3 times.
- Tests are checking throttling protection works ✓
- Wait 10 seconds and retry

---

## Key Validations Performed

### ✓ Deterministic Database Matching (Phase 1)
- Income thresholds enforced
- Geographic filters applied
- Match scores consistent

### ✓ Memory Retrieval (Phase 2)
- SchemeClarification queries work
- Prior answers cached correctly
- Iteration count increments

### ✓ Real AI Integration (Phase 3)
- Gemini API callable and working
- Questions generated with MD5 hashes
- Prompts include full context
- Responses parsed correctly

### ✓ Hybrid Routing (Phase 5)
- standard vs contextual answers detected by MD5 hash
- Routes dispatched to correct endpoints
- Payloads formatted correctly

### ✓ Database State Changes (Phase 6)
- SchemeClarification UPSERT works
- Iteration count persisted
- AI verdicts stored
- Prior answers retrievable on next cycle

### ✓ Safety Mechanisms
- 10-second cooldown enforced
- 3-iteration maximum enforced
- 429 responses issued correctly
- Infinite loops prevented

---

## Production Deployment Checklist

Before deploying to production:

- [ ] Run full test suite: `python run_v3_hybrid_tests.py`
- [ ] Verify all 5 phases PASS
- [ ] Check full lifecycle test SUCCESS
- [ ] Monitor database for lock issues
- [ ] Verify Gemini API quota sufficient
- [ ] Load test with 100+ concurrent users
- [ ] Check response times (<5s per phase)
- [ ] Verify no SQL injection vulnerabilities
- [ ] Ensure PII never sent to AI (check sanitization)
- [ ] Monitor SchemeClarification table growth

---

## Advanced: Custom Test Scenarios

To add custom test scenarios, edit `tests/test_v3_hybrid_real_system.py`:

```python
def test_CUSTOM_MyScenario():
    """Custom test scenario."""
    api = RealAPIClient()
    
    # 1. Create user
    success, resp = api.signup_user("test@custom.com", "Pass!", "Test")
    assert success
    
    # 2. Update profile
    success, resp = api.update_profile({
        "age": 45,
        "state": "Karnataka",
        "income": 300000
    })
    assert success
    
    # 3. Get recommendations
    success, recs = api.get_recommendations()
    assert len(recs.get("possibly_eligible", [])) > 0
    
    # 4. Your custom validation here
    assert True, "My test passed!"
```

Then run:
```bash
pytest tests/test_v3_hybrid_real_system.py::test_CUSTOM_MyScenario -v -s
```

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                   YOJANAMITRA V3 HYBRID ENGINE                 │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  [PHASE 1: Core Database Matching]                            │
│  User Demographics → HARD FILTER → Eligible/Possibly/Inelig.  │
│         ↓                                                      │
│  [PHASE 2: Verification Trigger]                              │
│  Check SchemeClarification History → Prior Answers?           │
│         ↓                                                      │
│  [PHASE 3: AI Context Analysis]                               │
│  detect Gaps → Generate Questions (MD5 hashes) → Modal        │
│         ↓                                                      │
│  [PHASE 4: Hybrid UI Modal]                                   │
│  Dropdowns for Standard + Textboxes for Contextual            │
│         ↓                                                      │
│  [PHASE 5: Smart Traffic Director]                            │
│  Split by MD5 hash → Route to /resolve OR /re-evaluate        │
│    - Standard Routing: /api/resolve-questions → Profile DB    │
│    - Contextual Routing: /api/readiness/re-evaluate → AI      │
│         ↓                                                      │
│  [PHASE 6: AI Re-Evaluation Engine]                           │
│  Inject DB History → Ask Gemini → UPSERT verdict → Done       │
│         ↓                                                      │
│  ✅ ELIGIBLE with 95%+ match score                             │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

---

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review test output logs: `report_v3_hybrid_complete.json`
3. Run with verbose output: `pytest ... -v -s`
4. Check Flask backend logs: `python app.py 2>&1 | tee backend.log`

---

**Last Updated:** April 17, 2026  
**Test Suite Version:** 3.0.0  
**Requires:** Flask backend running, SQLite database, Gemini API key
