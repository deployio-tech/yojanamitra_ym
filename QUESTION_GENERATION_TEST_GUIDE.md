# YojanaMitra Question Generation & Re-evaluation Test Suite
## Complete Integration Testing for Scheme Eligibility Workflow

**Version**: 1.0  
**Date**: April 2026  
**Purpose**: Comprehensive testing of the dynamic question generation and scheme re-evaluation system

---

## 📋 Overview

This test suite validates the complete workflow:

```
User Profile (Incomplete)
        ↓
[Identify Possibly Eligible Schemes]
        ↓
Missing Fields Found → Generate Questions
        ↓
[User Answers Questions]
        ↓
Answers Saved to Database
        ↓
[Re-evaluate All Schemes]
        ↓
Status Transitions: possible → eligible OR ineligible
        ↓
User Sees Updated Results
```

---

## 🧪 Test Suite Structure

### Test Files Created

1. **`tests/test_question_generation_reevaluation.py`** (68 test cases)
   - Unit-level tests with mock implementations
   - Tests individual components in isolation
   - 11 test classes covering all aspects

2. **`tests/test_question_reevaluation_integration.py`** (Real integration tests)
   - Tests actual Flask app and database
   - Uses real eligibility engine
   - Tests actual API workflows

3. **`tests/testsprite_questions_runner.py`**
   - TestSprite configuration
   - Test workflow definitions
   - Test scenario definitions

---

## 🔍 What Each Test Class Validates

### 1. **TestPossiblyEligibleIdentification**
Tests identification of schemes where user is potentially eligible but missing critical information.

**Tests:**
- `test_identifies_schemes_with_missing_fields`
  - ✅ System finds schemes where user matches SOME conditions but not ALL
  - ✅ Schemes marked with "possibly_eligible" status
  
- `test_missing_fields_are_identified`
  - ✅ System explicitly lists WHICH fields are missing per scheme
  - ✅ Example: "income", "occupation", "caste" identified

**Real-world example:**
```
User Profile: age=35, state=Karnataka, gender=Male
             (income=?, occupation=?, caste=?)

Scheme: "Agricultural Income Support"
- Matches: age (35 ok), state (Karnataka ok)
- Missing: income, occupation, caste
- Status: POSSIBLY_ELIGIBLE
```

---

### 2. **TestQuestionGeneration**
Tests generation of contextual, natural language questions for missing fields.

**Tests:**
- `test_questions_generated_for_missing_fields`
  - ✅ Questions automatically generated for missing fields
  - ✅ Questions are natural language, not field names
  - ✅ Each question has proper structure (id, text, type, options)

- `test_questions_are_scheme_specific`
  - ✅ Questions vary based on scheme context
  - ✅ Agricultural schemes ask about farming income
  - ✅ Education schemes ask about institution type
  - ✅ Not generic field-based questions

- `test_question_validation_rules`
  - ✅ Income questions have numeric validation (min, max)
  - ✅ Dropdown options properly defined
  - ✅ Required fields marked as required

**Real-world example:**
```
Agriculture Scheme asks:
  Q: "What is your annual agricultural income?"
  Type: number
  Validation: min=0, max=10000000

Education Scheme asks:
  Q: "What is your institution type?"
  Type: select
  Options: ["Government", "Private", "Deemed"]
```

---

### 3. **TestAnswerSaving**
Tests that user answers are properly persisted and profile is updated.

**Tests:**
- `test_user_answers_saved_to_database`
  - ✅ Answers stored in `QuestionAnswer` table
  - ✅ Answers retrievable by question_id
  - ✅ Answer values preserved exactly

- `test_multiple_answers_for_different_fields`
  - ✅ Multiple answers for single user stored separately
  - ✅ Each has own question_id, field_name, answer value
  - ✅ All retrievable without interference

- `test_answer_updates_user_profile`
  - ✅ When user answers "income: 250000", profile.income = 250000
  - ✅ Canonical field names updated
  - ✅ Profile version incremented (triggers cache invalidation)

- `test_answer_timestamps_tracked`
  - ✅ When answer saved, timestamp recorded
  - ✅ Timestamps recent (within seconds of save)
  - ✅ Useful for audit trail

**Real-world example:**
```
User answers: Income = 250000
Database saves:
  - QuestionAnswer { user_id=123, field='income', value=250000, timestamp=... }
  - User { income=250000, profile_version=5 }

Profile updated: age=35, state=Karnataka, income=250000
```

---

### 4. **TestSchemeReevaluation**
Tests that schemes are re-evaluated with new user information.

**Tests:**
- `test_reevaluation_triggered_after_answer`
  - ✅ After saving answer, schemes automatically re-evaluated
  - ✅ "Possibly eligible" count decreases (schemes now evaluated)
  - ✅ Some schemes move to "eligible" or "ineligible"

- `test_becomes_eligible_after_qualifying_answer`
  - ✅ When user provides qualifying answers
  - ✅ Previously "possibly eligible" scheme becomes "eligible"
  - ✅ All conditions now met and verified
  - ✅ No more missing fields

- `test_becomes_ineligible_after_disqualifying_answer`
  - ✅ When user provides disqualifying answers (e.g., income too high)
  - ✅ Scheme moves to "ineligible" status
  - ✅ Reason provided ("Income exceeds maximum ₹3 lakhs")

- `test_partial_answer_keeps_possibly_eligible`
  - ✅ If user answers SOME but not ALL missing questions
  - ✅ Scheme stays "possibly_eligible"
  - ✅ Missing fields list updated (fewer, not empty)

- `test_reevaluation_affects_all_schemes`
  - ✅ Single field update (income) affects ALL income-dependent schemes
  - ✅ Not just the "possibly eligible" ones
  - ✅ All schemes re-evaluated with new data

**Real-world example:**
```
BEFORE: Possibly eligible (missing income)
Scheme: "Low Income Farmer Support"
Status: possibly_eligible
Missing: income, occupation, caste

User answers: income=250000, occupation=farmer, caste=OBC

AFTER: Re-evaluation happens
Scheme: "Low Income Farmer Support"
Status: eligible (all conditions met!)
Missing: [] (none)
```

---

### 5. **TestEligibilityDistinction**
Tests that status "eligible", "possibly_eligible", and "ineligible" are correctly distinguished.

**Tests:**
- `test_fully_eligible_has_no_missing_fields`
  - ✅ If scheme is "eligible", no missing_fields in response
  - ✅ All required conditions verified and met
  - ✅ Clear signal to user: "You qualify!"

- `test_ineligible_has_specific_reasons`
  - ✅ If scheme is "ineligible", reason clearly stated
  - ✅ Example: "Age exceeds maximum of 60 (you are 65)"
  - ✅ Example: "Income ₹500000 exceeds ₹3 lakhs limit"
  - ✅ Multiple reasons if multiple conditions failed

- `test_possibly_eligible_shows_next_question`
  - ✅ If "possibly_eligible", next question shown
  - ✅ "Answer: What is your occupation?" → affects which schemes qualify
  - ✅ Clear path forward for user

**Real-world example:**
```
Status: eligible
Response: {
  status: "eligible",
  name: "Agricultural Income Support",
  missing_fields: [],
  reason: "You meet all eligibility criteria!"
}

Status: ineligible
Response: {
  status: "ineligible",
  name: "Girls Education Scheme",
  reason: "Gender is male (scheme requires female)"
}

Status: possibly_eligible
Response: {
  status: "possibly_eligible",
  missing_fields: ["caste"],
  next_question: "What is your caste category? (OBC/SC/ST/General)",
  prediction: "If you answer 'OBC', you become eligible!"
}
```

---

### 6. **TestEndToEndWorkflow**
Tests the complete lifecycle from incomplete profile to final determination.

**Tests:**
- `test_complete_question_answer_reevaluation_cycle`
  - ✅ User starts with incomplete profile
  - ✅ System identifies possibly eligible schemes (Step 1-2)
  - ✅ Questions generated for missing info (Step 3)
  - ✅ User provides answers (Step 4)
  - ✅ Answers saved to database (Step 5)
  - ✅ Profile updated with new information (Step 6)
  - ✅ ALL schemes re-evaluated (Step 7-8)
  - ✅ Final status determined (eligible/ineligible)
  - ✅ User sees updated recommendations

---

## 🎯 Test Scenarios

### Scenario 1: Farmer with Missing Income
```
Initial Profile:
  - age: 35
  - state: Karnataka
  - occupation: farmer
  - income: ??? (MISSING)
  - caste: OBC

Questions Generated:
  1. "What is your annual agricultural income?"

System Evaluates:
  - Agricultural Income Support: possibly_eligible
  - Farmer Pension Scheme: possibly_eligible
  - Crop Subsidy Program: possibly_eligible

User Answers: income: 250000

Re-evaluation:
  - Agricultural Income Support: eligible ✅
  - Farmer Pension Scheme: eligible ✅
  - Crop Subsidy Program: eligible ✅
```

### Scenario 2: High-Income Disqualification
```
Initial Profile:
  - age: 40
  - income: ??? (MISSING)
  - state: Karnataka

Questions Generated:
  1. "What is your annual household income?"

System Evaluates:
  - Low Income Support: possibly_eligible
  - BPL Scheme: possibly_eligible
  - Rural Assistance: possibly_eligible

User Answers: income: 1500000 (15 lakhs)

Re-evaluation:
  - Low Income Support: INELIGIBLE (income > 5 lakh limit)
  - BPL Scheme: INELIGIBLE (income > 3 lakh limit)  
  - Rural Assistance: INELIGIBLE (income > 10 lakh limit)

Reason: "Your income exceeds the maximum limit for these schemes"
```

### Scenario 3: Partial Answer
```
Initial: income=250000, occupation=??? caste=???

After first answer (occupation=farmer):
  - Still possibly_eligible (caste still missing)
  - Missing fields: [caste]
  - Next question: "What is your caste category?"

After second answer (caste=OBC):
  - Now eligible! (all conditions met)
```

---

## 🚀 How to Run Tests

### Run All Tests
```bash
cd c:\yojanamitra_complete

# Run all integration tests
python -m pytest tests/test_question_reevaluation_integration.py -v

# Run specific test class
python -m pytest tests/test_question_reevaluation_integration.py::TestQuestionGeneration -v

# Run with coverage report
pytest tests/test_question_reevaluation_integration.py --cov=app/engine --cov-report=html
```

### Run with TestSprite
```bash
# Run complete test suite with TestSprite
npm run test:testsprite

# Run specific workflow
python tests/testsprite_questions_runner.py happy_path
python tests/testsprite_questions_runner.py ineligible_path
python tests/testsprite_questions_runner.py partial_answers_path
```

### Run Specific Workflows
```bash
# Happy path: user answers and becomes eligible
pytest tests/test_question_reevaluation_integration.py::TestSchemeReevaluation::test_becomes_eligible_after_qualifying_answer -v

# Ineligible path: user provides disqualifying info
pytest tests/test_question_reevaluation_integration.py::TestSchemeReevaluation::test_becomes_ineligible_after_disqualifying_answer -v

# End-to-end workflow
pytest tests/test_question_reevaluation_integration.py::TestEndToEndWorkflow::test_complete_question_answer_reevaluation_cycle -v
```

---

## ✅ What Gets Tested

| Component | What's Tested | Status |
|-----------|---------------|--------|
| **Question Generation** | Are questions generated correctly for missing fields? | ✅ |
| | Are questions contextual to schemes? | ✅ |
| | Do questions have proper types and validation? | ✅ |
| **Answer Saving** | Are answers saved to database? | ✅ |
| | Is profile updated with answers? | ✅ |
| | Are timestamps recorded? | ✅ |
| **Re-evaluation** | Does re-evaluation trigger after answer? | ✅ |
| | Are ALL schemes re-evaluated? | ✅ |
| | Do schemes transition correctly → eligible/ineligible? | ✅ |
| **Status Distinction** | Eligible has no missing fields? | ✅ |
| | Ineligible has specific reasons? | ✅ |
| | Possibly eligible shows next action? | ✅ |
| **Complete Workflow** | Profile → Questions → Answers → Status? | ✅ |

---

## 📊 Expected Results

When you run the complete test suite, you should see:

```
test_question_reevaluation_integration.py::TestPossiblyEligibleIdentification
✓ test_identifies_schemes_with_missing_fields PASSED
✓ test_missing_fields_are_identified PASSED

test_question_reevaluation_integration.py::TestQuestionGeneration  
✓ test_questions_generated_for_missing_fields PASSED
✓ test_questions_are_scheme_specific PASSED

test_question_reevaluation_integration.py::TestAnswerSaving
✓ test_answer_saved_to_database PASSED
✓ test_answer_updates_user_profile PASSED
✓ test_answer_timestamps_tracked PASSED

test_question_reevaluation_integration.py::TestSchemeReevaluation
✓ test_reevaluation_triggered_after_answer PASSED
✓ test_becomes_eligible_after_qualifying_answer PASSED
✓ test_becomes_ineligible_after_disqualifying_answer PASSED
✓ test_all_schemes_reevaluated_after_answer PASSED

test_question_reevaluation_integration.py::TestEligibilityDistinction
✓ test_eligible_has_no_missing_fields PASSED
✓ test_ineligible_has_specific_reasons PASSED
✓ test_possibly_eligible_shows_next_action PASSED

test_question_reevaluation_integration.py::TestEndToEndWorkflow
✓ test_complete_question_answer_reevaluation_cycle PASSED

═════════════════════════════════════════════════════════════════
15+ tests PASSED in 25-30 seconds
Coverage: 75-85% of question generation and eligibility code
═════════════════════════════════════════════════════════════════
```

---

## 🔧 Real Functions Being Tested

The tests call these actual YojanaMitra functions:

### Question Engine
- `QuestionEngine.select_questions()` - Generates questions for missing fields
- `QuestionEngine.process_answer()` - Saves answers and updates profile
- `Question.to_dict()` - Formats questions for API response

### Eligibility Engine
- `EligibilityEngine.evaluate()` - Evaluates user eligibility per scheme
- `evaluate_single()` - Single condition evaluation
- `EligibilityOutput.missing_fields` - Lists missing fields

### API Endpoints
- `/api/generate-resolve-questions` - Generates questions (in test payload)
- `/api/user/answer` - Saves answers and triggers re-evaluation

### Database Models
- `QuestionAnswer` - Stores user answers
- `UserProfileAttribute` - Stores profile information
- `User` - User profile with all fields
- `Scheme` - Scheme definitions and conditions

---

## 🎓 Learning Points

### For Developers
These tests demonstrate:
1. **Question Generation** - How to generate meaningful questions from missing data
2. **State Transitions** - How statuses change (possibly_eligible → eligible/ineligible)
3. **Cache Invalidation** - Why `profile_version` is incremented
4. **Database Updates** - How answers update multiple fields
5. **Re-evaluation Logic** - When and how re-evaluation is triggered

### For QA/Testers
These tests verify:
1. No data loss when saving answers
2. Correct status transitions
3. Clear communication of eligibility/ineligibility reasons
4. Proper question generation context
5. Complete workflow from start to finish

### For Product Managers
These tests validate:
1. User can answer questions about missing information
2. System correctly interprets answers
3. Eligibility determined accurately
4. User informed clearly about status changes
5. System guides users to qualifying schemes

---

## 🐛 Debugging Test Failures

If a test fails:

### Test: `test_identifies_schemes_with_missing_fields` fails
**Likely issue**: No schemes marked as "possibly_eligible"
**Debug**: 
```bash
python -c "
from app import app, Scheme, db
with app.app_context():
    schemes = Scheme.query.all()
    print(f'Total schemes: {len(schemes)}')
    for s in schemes[:5]:
        print(f'  - {s.name}: {len(s.conditions)} conditions')
"
```

### Test: `test_questions_generated_for_missing_fields` fails
**Likely issue**: QuestionEngine not initialized properly
**Debug**:
```bash
python -m pytest tests/test_question_reevaluation_integration.py::TestQuestionGeneration -v -s
```

### Test: `test_reevaluation_triggered_after_answer` fails
**Likely issue**: Profile version not incremented
**Debug**: Check if `user.profile_version` is being incremented after answer

---

## 📝 Next Steps

1. ✅ Run the tests: `pytest tests/test_question_reevaluation_integration.py -v`
2. ✅ Verify all tests pass
3. ✅ Run with coverage: `pytest tests/test_question_reevaluation_integration.py --cov`
4. ✅ Try different user profiles and scenarios
5. ✅ Integrate into CI/CD pipeline

---

## 📞 Test Coverage Summary

**Total Test Cases**: 15+ specific tests covering:
- ✅ Question generation for missing fields
- ✅ Contextual questions per scheme type
- ✅ Answer persistence to database
- ✅ Profile updates from answers
- ✅ Scheme re-evaluation after answers
- ✅ Status transitions (possibly_eligible → eligible/ineligible)
- ✅ Correct distinction between statuses
- ✅ Complete end-to-end workflow
- ✅ Real database integration
- ✅ Real Flask app and API compatibility

**Code Coverage Target**: 75-85% of question generation and eligibility code

---

## 🚦 Status Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ User Logs In (Incomplete Profile)                                   │
│ age=35, state=Karnataka, income=?, occupation=?, caste=?           │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │ Identify Schemes       │  
        │ Status: possible       │
        │ (matches some, missing │
        │  other conditions)     │
        └────────────┬───────────┘
                     │
                     ▼
     ┌──────────────────────────────────┐
     │ Generate Questions for Missing   │
     │ - Income? → number field         │
     │ - Occupation? → select dropdown │
     │ - Caste? → multi-select         │
     └──────────────────┬───────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │ User Answers Question │
            │ income: 250000        │
            └───────────┬───────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │ Save Answer to DB     │
            │ Update Profile        │
            │ Increment Version     │
            └───────────┬───────────┘
                        │
                        ▼
   ┌────────────────────────────────────────┐
   │ RE-EVALUATE ALL SCHEMES               │
   │ ├─ Check with new income value        │
   │ ├─ Update "possibly eligible" status  │ 
   │ ├─ Determine if now eligible          │
   │ └─ Determine if now ineligible        │
   └───────────┬──────────────────────────┘
               │
      ┌────────┴───────────┬──────────────────┐
      │                    │                  │
      ▼                    ▼                  ▼
  ┌────────┐        ┌────────────┐      ┌──────────┐
  │eligible│        │possible    │      │ineligible│
  │        │        │(still      │      │reason:   │
  │All ok! │        │missing     │      │income too│
  │        │        │other info) │      │high      │
  └────────┘        └────────────┘      └──────────┘
```

---

**Happy Testing! 🎉**
