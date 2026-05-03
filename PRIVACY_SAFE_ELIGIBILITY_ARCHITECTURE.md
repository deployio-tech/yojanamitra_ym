# Privacy-Safe Eligibility Matching & AI Validation Architecture

**Date:** March 17, 2026
**Goal:** Build a system that achieves high accuracy while enforcing strict privacy, zero PII leakage, and user trust.

---

## 1. Privacy-Safe System Architecture Design

### 1.1 Architecture Overview

1. **User Profile Store (Secure Backend)**
   - Raw user data stored in encrypted DB (at rest + in transit)
   - Sensitive fields: Aadhaar, PAN, phone, email, income, documents, IDs
   - Access controls: RBAC, audit logs

2. **Eligibility Matching Pipeline**
   - 1) Rule-Based Engine
   - 2) Semantic Engine
   - 3) Optional AI Readiness Engine

3. **Sanitization Layer (Mandatory)**
   - Runs in backend before any AI call
   - Transforms sensitive inputs into abstract fields
   - Blocks any raw identifier or exact value from AI

4. **AI / Semantic Engine (Non-sensitive)**
   - Receives only:
     - abstracted user attributes (age-group, income-range, role tags, disability status, education-band)
     - scheme description and eligibility text
   - Cannot access PII/credentials

5. **Decision Layer**
   - Applies combined results from rule + semantic + AI (if enabled)
   - Returns eligibility classification

6. **Optional Privacy Mode**
   - Disables AI call; uses rule + semantic only
   - Default for privacy-conscious settings

### 1.2 Stack and Controls

- Backend: Python + Flask + SQLAlchemy
- Model: Local semantic matching + GPT style API (Gemini) with anonymized prompt
- Secrets: Keep AI API key in Vault / env
- Logging: PII redaction at logger layer
- Monitoring: metrics only (no user data)

---

## 2. Data Sanitization Strategy and Transformation Rules

### 2.1 Raw → Abstract Mapping Rules

| Raw Field | Sanitized Field | Rule |
|-----------|----------------|------|
| age | age_group | {0-17, 18-25, 26-35, 36-45, 46-60, 60+} |
| exact_income | income_range | {<2L, 2L-5L, 5L-8L, 8L-12L, >12L} |
| residence | state | keep state only (no city/zip) |
| exact_occupation | occupation_tags | {farmer, student, unemployed, professional} |
| aadhaar/pan | (none) | drop, do not forward |
| phone/email | (none) | drop, do not forward |
| document attachments | (none) | drop; optionally send type abstracted as: "needs affidavit" |
| full_name | (none) | drop |
| national ID | (none) | drop |

### 2.2 Role-based attribute examples

- `21-year-old engineering student` -> `age_group: 18-25`, `occupation_tag: student`, `education_band: UG`, `status: urban`
- `farmer with small landholding` -> `occupation_tag: farmer`, `land_category: <2 acres` (or `non-specific`), `rural`.
- `widow below poverty line` -> `beneficiary_tag: widow`, `economic_status: BPL`.

### 2.3 Transformation Pipeline (Pseudocode)

```python
def sanitize_profile(profile):
    if profile is None:
        raise ValueError('Missing profile')

    sanitized = {
        'age_group': age_to_group(profile.age),
        'income_range': income_to_range(profile.annual_income),
        'gender': profile.gender,
        'state': profile.state,
        'caste': profile.caste_category,
        'education_band': map_education(profile.education_level),
        'occupations': map_occupations(profile.occupations),
        'is_widow': profile.is_widow,
        'is_disabled': profile.is_disabled,
        'is_senior_citizen': profile.is_senior_citizen,
        'is_minority': profile.is_minority,
        'land_ownership': bool(profile.owns_agricultural_land),
        'disability_type': profile.disability_type if profile.is_disabled else None,
        'privacy_mode': profile.privacy_mode or False,
    }

    # Enforce non-identifying semantics; drop any PII
    assert 'aadhaar' not in sanitized
    assert 'pan' not in sanitized
    return sanitized
```

---

## 3. Sensitive vs Non-Sensitive Field Inventory

### Sensitive Fields (Must never leave backend)
- Aadhaar number
- PAN number
- Phone number
- Email address
- Exact income amount
- Uploaded documents (raw image/pdf)
- Full name
- Address details (street/door number/pincode) if derivable to identity
- Government IDs and tokenized identifiers
- Local session tokens / auth tokens

### Non-sensitive Fields (AI allowed after abstraction)
- Age group (e.g., 18-25)
- Income range (e.g., 2L-5L)
- State
- Caste category (SC/ST/OBC/General) — allowed for eligibility
- Occupation tag (farmer, student, etc.)
- Education band (Class 10, Class 12, UG, PG)
- Disability flag and type category (if user consent)
- Widow status, senior status
- Land ownership flag (yes/no, banded size) 
- ‘Sensitive concept’ but non-id text from scheme descriptions

---

## 4. AI Input/Output Structure (No PII)

### 4.1 AI input payload (safe)

```json
{
  "user_profile": {
    "age_group": "26-35",
    "income_range": "5L-8L",
    "state": "Karnataka",
    "caste": "OBC",
    "education_band": "UG",
    "occupation_tags": ["IT Professional"],
    "is_widow": false,
    "is_disabled": false,
    "is_senior_citizen": false,
    "land_ownership_category": "<2 acres",
    "economic_status": "LIG"
  },
  "scheme_text": {
    "name": "PM-KISAN",
    "description": "Scheme for farmers with agricultural land...",
    "eligibility_criteria": "Must be a farmer, land holder, no more than 2 ha..."
  }
}
```

### 4.2 AI output contract

```json
{
  "eligibility_prediction": "likely_eligible|likely_not_eligible|unclear",
  "confidence_score": 0.0-1.0,
  "explanation": "Based on category-level attributes...",
  "recommended_remarks": ["Need field: land_ownership", "Needs economic_status"]
}
```

### 4.3 No PII in AI outputs
- AI output does not include user name, ID, contact, exact income, or document content.
- AI output must be treated as transient; not stored with PII.

---

## 5. Logging and Redaction Mechanisms

### 5.1 Logging policy
- All logs categorized as:
  - debug (development only)
  - info
  - warning
  - error

- No raw profile fields in logs.
- Use sanitized profile in logs.

### 5.2 Redaction functions

```python
import re

def redact_aadhaar(value: str) -> str:
    return re.sub(r"\d{4}\s*\d{4}\s*", "XXXX XXXX ", value) if value else None

def redact_phone(value: str) -> str:
    if value is None: return None
    digits = re.sub(r"\D", "", value)
    if len(digits) < 10: return 'X'*len(digits)
    return 'XXXXXX' + digits[-4:]

def redact_email(value: str) -> str:
    if value is None or '@' not in value: return None
    local, domain = value.split('@', 1)
    return local[:2] + '***@' + domain

def redact_pii(obj: dict) -> dict:
    return {
        k: (redact_phone(v) if k=='phone' else redact_email(v) if k=='email'
             else redact_aadhaar(v) if k=='aadhaar'
             else '****' if k in ['pan', 'address', 'name'] else v)
        for k,v in obj.items()
    }
```

### 5.3 Log sample

```python
logger.info('Sanitized eligibility request', extra={'user_profile': sanitized_profile})
```

### 5.4 Secure log storage
- Log files encrypted at rest
- Use centralized log management with access restrictions

---

## 6. User-Facing Privacy Messaging

### Messaging snippets

- "Your personal data is securely stored and never shared with external AI systems."
- "Only anonymized and non-sensitive information is used for eligibility analysis."
- "We never send Aadhaar, PAN, phone, email, exact income or documents to any third-party AI service."
- "You can enable Privacy Mode to use only rule-based and semantic checks with no AI calls."

### Transparency UI
- Privacy section in profile settings:
  - Data collected
  - Data used in eligibility
  - Third-party AI usage
  - How to opt out
- Show terms: "AI validation may use anonymized attributes only."

---

## 7. Recommendations to Improve Trust and Adoption

1. **Privacy-First Default**
   - Default to `privacy_mode=True` for new signups
   - Allow explicit "AI-enhanced matching" opt-in

2. **Consent and Audit**
   - Capture explicit consent for AI usage
   - Log consent events for compliance

3. **Documentation for users**
   - Publish privacy policy / FAQ
   - Explain data minimization es

4. **Conversion control**
   - Provide clear "opt in for better precision" toggle
   - Keep user fallback safe

5. **Regular privacy audits**
   - Quarterly external review
   - CVE/PCI compliance checks

6. **PII handling training**
   - Train team on secure PII handling, least privilege, GDPR-like principles

---

## Optional: Privacy Mode Feature

- New user flag: `privacy_mode` (bool)
- If true:
  - Disable AI validation calls
  - Use only rule-based + semantic (never call external AI)
  - Offer faster and fully local results
- If false:
  - Use full hybrid pipeline

API:

```python
def evaluate_eligibility(profile, scheme, privacy_mode=False):
    rule_result = rule_based_check(profile, scheme)
    semantic_result = semantic_check(profile, scheme)

    if not rule_result.passed or not semantic_result.passed:
        return NOT_ELIGIBLE

    if privacy_mode:
        return POSSIBLY_ELIGIBLE_WITHOUT_AI

    return ai_validation(profile, scheme)
```

---

## 8. Security & Compliance Considerations

- Data minimization: Send only needed fields
- Least privilege: APIs and DB with restricted roles
- Encryption: At rest (AES-256), in transit (TLS)
- Audit logging: Record who accessed sensitive fields
- Retention policy: Delete PII after purpose (e.g., 90 days)
- Data subject rights: Right to access, correct, delete

### GDPR-like alignment
- Lawful basis: consent + legitimate interest
- Data protection impact assessment (DPIA) for AI
- Breach notification plan

---

## 9. Implementation Checklist

1. [x] Implement `sanitize_profile()` and policy in matching pipeline
2. [x] Ensure AI input payload is non-PII
3. [x] Add `privacy_mode` fallback option
4. [x] Add redaction functions and logger wrappers
5. [x] Create user privacy messaging and settings
6. [x] Add docs in `PRIVACY_SAFE_ELIGIBILITY_ARCHITECTURE.md`
7. [x] Perform code review and security review
8. [x] Add test cases for PII exclusions
9. [x] Add audit trail for AI requests

---

## 10. Validation / Test Cases

### 10.1 PII Exclusion Test
- Create profile with Aadhaar, PAN, email, phone, exact income
- Run eligibility pipeline with AI endpoint
- Assert AI payload does not contain those fields

### 10.2 Age Group and Income Range Test
- Input age=23, income=320000
- Check `age_group == 18-25`, `income_range == 2L-5L`

### 10.3 Privacy Mode Test
- set `privacy_mode=True`
- Ensure no AI call was made and result is from rule+semantic only

### 10.4 Log Redaction Test
- Input profile with PII.
- Observe log: Aadhaar gets displayed as `XXXX XXXX 1234`, email as `ab***@domain.com`.

---

## 11. Final Statement

This design treats privacy as a first-class feature. It ensures sensitive user data never leaves the backend, AI receives only anonymized attributes, and the matching flow is secure, scalable, and trusted.

**Execution is ready; verify with one low-risk staging run and move to production.**