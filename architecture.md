# YojanaMitra System Architecture

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          YOJANAMITRA SYSTEM ARCHITECTURE                            │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌───────────────────────┐
                                    │   SCHEME SOURCES      │
                                    │   (Web Scraping)      │
                                    └───────────┬───────────┘
                                                │
                    ┌───────────────────────────┘
                    ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│  1. SCHEME INTAKE & PROCESSING PIPELINE (app/pipeline/)                             │
├───────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                       │
│    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    │
│    │  NORMAL- │───▶│    AI    │───▶│  FIELD   │───▶│ QUALITY  │───▶│  EXPIRY  │    │
│    │  IZATION │    │EXTRACTION│    │ NORMALIZ │    │ SCORING  │    │DETECTION│    │
│    │          │    │(Gemini)  │    │          │    │          │    │          │    │
│    └──────────┘    └────┬─────┘    └──────────┘    └──────────┘    └──────────┘    │
│                          │                                                         │
│                          ▼                                                         │
│                   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│                   │ DUPLICATE   │───▶│ VALIDATION  │───▶│   PUBLISH   │          │
│                   │ DETECTION  │    │    PASS     │    │   TO DB     │          │
│                   └─────────────┘    └─────────────┘    └──────┬──────┘          │
│                                                                 │                 │
└─────────────────────────────────────────────────────────────────┼─────────────────┘
                                                                  │
                                                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  2. SCHEME STORAGE (Database)                                                       │
├───────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                       │
│    SCHEME TABLE                                                                      │
│    ├── id, name, description, category                                              │
│    ├── min_age, max_age, min_income, max_income                                     │
│    ├── allowed_genders, allowed_castes, allowed_states                              │
│    ├── is_active, extraction_status, expires_at                                     │
│                                                                                       │
│    CONDITION TABLE (NEW ENGINE)                                                     │
│    ├── scheme_id (FK)                                                               │
│    ├── field, operator, value                                                       │
│    ├── condition_type (hard/soft/acquirable)                                        │
│    ├── confidence, source_fragment, is_ambiguous                                    │
│    └── source (manual/extraction/migration)                                         │
│                                                                                       │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  3. USER ONBOARDING FLOW                                                             │
├───────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                       │
│    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    │
│    │ REGISTER │───▶│  LOGIN   │───▶│ COMPLETE │───▶│ UPLOAD   │───▶│  SYNC    │    │
│    │          │    │          │    │ PROFILE  │    │DOCUMENTS │    │PROFILE   │    │
│    └──────────┘    └──────────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘    │
│                                          │               │               │          │
│                                          ▼               ▼               ▼          │
│                                   ┌─────────────────────────────────────────────┐    │
│                                   │          USER PROFILE (60+ fields)         │    │
│                                   │  • age, gender, income, occupation          │    │
│                                   │  • caste, state, education                 │    │
│                                   │  • documents, achievements                  │    │
│                                   │  • special categories                       │    │
│                                   └─────────────────────────────────────────────┘    │
│                                                                                       │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  4. ELIGIBILITY EVALUATION FLOW                                                      │
├───────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                       │
│    USER REQUEST: GET /api/recommendations                                            │
│                         │                                                             │
│                         ▼                                                             │
│    ┌─────────────────────────────────────────────────────────────────────────────┐    │
│    │              ELIGIBILITY ORCHESTRATOR                                       │    │
│    │                                                                           │    │
│    │  STEP 1: PREFILTER (Fast DB-level filter)                                │    │
│    │  • is_active = True                                                     │    │
│    │  • extraction_status = "extracted"                                     │    │
│    │  • state match                                                           │    │
│    │                              │                                           │    │
│    │                              ▼                                           │    │
│    │  STEP 2: CACHE CHECK                                                     │    │
│    │  • Check EligibilityResult table                                        │    │
│    │                              │                                           │    │
│    │                              ▼                                           │    │
│    │  STEP 3: CONTEXT SCORING (ContextualReasoner)                           │    │
│    │  • State match, occupation match, target group mapping                   │    │
│    │  → Returns 0.0-1.0 plausibility signal                                  │    │
│    │                              │                                           │    │
│    │                              ▼                                           │    │
│    │  STEP 4: TIER DETERMINATION                                             │    │
│    │  Tier 1: Full evaluation + questions                                    │    │
│    │  Tier 2: Full evaluation (no questions)                                │    │
│    │  Tier 3: Hard conditions only (fast)                                    │    │
│    │                              │                                           │    │
│    │                              ▼                                           │    │
│    │  STEP 5: ELIGIBILITY ENGINE (Multi-Pass)                               │    │
│    │                                                                           │    │
│    │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │    │
│    │  │ PASS 1: HARD    │  │ PASS 2: SOFT    │  │ PASS 3:         │          │    │
│    │  │     GATE        │  │     SCORE       │  │    ACQUIRABLE   │          │    │
│    │  │                 │  │                 │  │                 │          │    │
│    │  │ Any HARD FAIL  │  │ UNKNOWN soft   │  │ Surface things  │          │    │
│    │  │ → INELIGIBLE   │  │ → reduce conf  │  │ to gather       │          │    │
│    │  └─────────────────┘  └─────────────────┘  └─────────────────┘          │    │
│    │                                                                           │    │
│    │  OUTPUT: result, confidence, missing_fields, clarification_needed        │    │
│    │                              │                                           │    │
│    │                              ▼                                           │    │
│    │  STEP 6: RESULT RANKING                                                 │    │
│    │  • THRESH_ELIGIBLE → Fully eligible                                     │    │
│    │  • THRESH_POSSIBLE → Possibly eligible                                  │    │
│    │  • THRESH_MAYBE → Maybe eligible                                        │    │
│    │                              │                                           │    │
│    │                              ▼                                           │    │
│    │  STEP 7: QUESTION GENERATION                                           │    │
│    │  • Select only POSSIBLE schemes                                        │    │
│    │  • Map to canonical concepts                                           │    │
│    │  • Prioritize by impact score (HARD*3 + SOFT*1)                        │    │
│    │                                                                           │    │
│    │  HUMANIZATION OUTPUT:                                                   │    │
│    │  "You are a citizen of India"                                          │    │
│    │  "Your annual income must be at most ₹2,50,000"                         │    │
│    │  "You should not have an existing savings account"                     │    │
│    └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  5. RESPONSE TO USER                                                                  │
├───────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                       │
│    {                                                                                  │
│      "recommendations": [...],     # Fully eligible                                  │
│      "possibly_eligible": [...],    # Possible but need more info                    │
│      "questions": [...],           # Dynamic questions                               │
│      "meta": {...}                                                                 │
│    }                                                                                  │
│                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  6. QUESTION ANSWERING LOOP (Optional)                                              │
├───────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                       │
│    USER ANSWERS QUESTION → SAVE → UPDATE PROFILE → RE-EVALUATE → NEW QUESTIONS      │
│                                                                                       │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Summary Flow

```
SCHEME SOURCE → SCRAPING → GEMINI → CONDITIONS → DB
                                              ↓
                                    USER REQUEST
                                              ↓
                            PREFILTER → CACHE → CONTEXT → EVALUATE → RANK
                                              ↓                         
                                      POSSIBLE? → QUESTIONS → ANSWERS → RE-EVALUATE
                                              ↓
                                        FINAL RESPONSE
```

## Core Components

| Component | File | Purpose |
|-----------|------|---------|
| EligibilityOrchestrator | app/engine/__init__.py | Ties everything together |
| EligibilityEngine | app/engine/eligibility.py | Multi-pass evaluation |
| QuestionEngine | app/engine/questions.py | Question generation |
| ContextualReasoner | app/engine/context.py | Plausibility scoring |
| ResultRanker | app/engine/scorer.py | Confidence-based ranking |
| Humanization | app/engine/eligibility.py | Human-readable hints |

## Database Models

### User Model (60+ fields)

**Basic:**
- id, name, email, password_hash, mobile, created_at

**Demographics:**
- age, gender, occupation, income, caste, state, education, religion, residence

**Family & Background:**
- family_type, total_family_members, is_head_of_family, annual_family_income
- father_occupation, mother_occupation, land_type, is_orphan, is_tribal

**Identity & Documents:**
- dob, aadhaar_available, district, block_taluk, domicile_status
- ration_card_available, ration_card_type
- income_certificate_available, income_cert_last_1_year

**Special Categories:**
- is_pensioner, is_widow_single_woman, is_senior_citizen
- minority_status, ews_status, is_bocw_registered
- disability, disability_percentage

**Achievements:**
- documents_available, achievement_certificates (sports, art, NCC, NSS, skill)

### Scheme Model

- Basic: id, name, description, category, benefits, application_link
- Age/Income: min_age, max_age, min_income, max_income
- Eligibility: allowed_genders, allowed_castes, allowed_states
- Requirements: bank_account_required, aadhaar_required, residence_requirement

### Condition Model (NEW Engine)

```python
field: str          # e.g., "age", "income", "caste"
operator: str       # "gte", "lte", "eq", "in", etc.
value: JSON        # The required value
condition_type: str # "hard", "soft", "acquirable"
confidence: float  # AI extraction confidence (0.0-1.0)
source_fragment: str # Original text fragment
source: str        # "manual", "extraction", "migration"
is_ambiguous: bool # Flag for ambiguous conditions
```

## API Endpoints

### Authentication
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /api/register | POST | User registration |
| /api/login | POST | User/Admin login |
| /api/logout | GET/POST | Logout |
| /api/user | GET | Get current user |

### User Profile
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /api/profile | POST | Update profile |
| /api/documents/upload | POST | Upload documents |
| /api/documents/sync-profile | POST | Sync to profile |

### Schemes & Eligibility
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /api/schemes | GET | List schemes |
| /api/recommendations | GET | Personalized recommendations |
| /api/check-eligibility | POST | Check eligibility |
| /api/deep-eligibility-search | POST | AI-powered search |

### Admin
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /api/admin/stats | GET | System statistics |
| /api/admin/users | GET | List users |
| /api/admin/pending-schemes | GET | Pending schemes |
| /api/admin/trigger-scrape | POST | Trigger scraping |

## Evaluation Logic

### Multi-Pass Eligibility

**Pass 1: Hard Gate**
- Any hard condition FAIL → INELIGIBLE immediately
- No second chances

**Pass 2: Soft Score**
- Unknown soft conditions → reduce confidence
- Calculate soft_score = passed / (passed + failed + 0.5 * unknown)

**Pass 3: Acquirable**
- Surface things user can gather/verify
- Don't block eligibility

### Question Generation

1. Identify POSSIBLE schemes (missing hard fields)
2. Extract missing fields from conditions
3. Map fields to canonical concepts (concept_registry.json)
4. Generate human-readable questions
5. Filter already-answered questions
6. Prioritize by impact score (HARD*3 + SOFT*1)
7. Return batched questions (max 3)

### Humanization System

```python
# Before
"is_citizen_of_india needs clarification"

# After
"You are a citizen of India"
"Your annual income must be at most ₹2,50,000"
"You should not have an existing savings account"
```

Features:
- Sentence case with proper nouns
- Indian currency format (₹2,50,000)
- Modal verbs (must for hard, should for soft)
- Articles (a/an)

## Current Statistics

| Metric | Value |
|--------|-------|
| Total Schemes | 4,212 |
| Active Schemes | 4,212 |
| User Profile Fields | 60+ |
| Condition Types | hard, soft, acquirable |

## Files Modified (During Session)

| File | Purpose |
|------|---------|
| app/engine/eligibility.py | Added humanization system |
| app/engine/questions.py | Fixed question generation |
| audit_full_system.py | Full audit script |
| test_humanize.py | Testing humanization |
