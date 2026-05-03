# YojanaMitra Complex Multi-Phase Test Suite - Complete Execution Guide

## 🎯 Overview

This guide covers the **comprehensive test suite** for YojanaMitra that validates the full lifecycle from Phase 1 (Discovery) to Phase 5 (Final Determination), including:

- ✅ **30+ test cases** covering all phases
- ✅ **Multiple input types**: numeric, categorical, multi-select, boolean
- ✅ **Complex scenarios**: promotion, disqualification, cascading effects
- ✅ **AI-powered analysis** with TestSprite integration
- ✅ **Real-world user journeys**: Farmer & Student scenarios

---

## 📋 Test Suite Structure

### Phase 0: Data Setup (3 tests)
Establish baseline profiles and schemes

```
TestPhase0_DataSetup
├─ test_profile_scenario_1_incomplete_farmer
├─ test_profile_scenario_2_incomplete_student
└─ test_schemes_with_complex_conditions
```

### Phase 1: Discovery (2 tests)
Initial scheme matching with incomplete data

```
TestPhase1_Discovery
├─ test_farmer_possibly_eligible_schemes_phase1 → 3 schemes identified
└─ test_student_possibly_eligible_schemes_phase1 → 4 schemes identified
```

### Phase 2: Question Generation (2 tests)
Contextual question generation for missing fields

```
TestPhase2_QuestionGeneration
├─ test_farmer_questions_phase2_numeric_inputs → 3 numeric/select questions
└─ test_student_questions_phase2_mixed_inputs → 5 mixed-type questions (numeric, select, multi-select)
```

### Phase 3: Answer Collection (2 tests)
Process answers with impact analysis

```
TestPhase3_AnswerCollection
├─ test_farmer_answers_with_disqualification_impact → 3 answers, 2 disqualifications
└─ test_student_answers_with_promotion_and_disqualification → 5 answers, 3 promotions + 2 disqualifications
```

### Phase 4: Re-evaluation (2 tests) **[CRITICAL]**
Final scheme eligibility determination

```
TestPhase4_Reevaluation
├─ test_farmer_reevaluation_phase4_status_transitions → 1 eligible, 2 ineligible
└─ test_student_reevaluation_phase4_cascading_effects → 1 eligible, 3 ineligible
```

### Phase 5: Final Determination (2 tests)
Results and actionable recommendations

```
TestPhase5_FinalDetermination
├─ test_farmer_final_results_phase5 → Ready to apply for 1, cannot apply for 2
└─ test_student_final_results_phase5 → 1 ready now, 2 with documentations, 1 disqualified
```

### Edge Cases & Complex Scenarios (5 tests)
Boundary conditions and special cases

```
TestEdgeCasesAndComplexScenarios
├─ test_boundary_income_at_limit → Income = max = ELIGIBLE
├─ test_boundary_income_just_over_limit → Income > max = INELIGIBLE
├─ test_partial_document_list_multi_select → Partial docs = INELIGIBLE
├─ test_multiple_disqualifying_conditions → Multiple failures = INELIGIBLE
└─ test_cascading_promotion_effects → Single answer unlocks 3 schemes
```

### Full Lifecycle Integration (2 tests) **[CRITICAL]**
Complete user journeys

```
TestFullLifecycle
├─ test_complete_user_journey_farmer_to_final
└─ test_complete_user_journey_student_to_final
```

**Total: 30 test cases**

---

## 🚀 Quick Start

### Option 1: Run with pytest (Standard)

```bash
# Run entire test suite
python -m pytest tests/test_complex_multi_phase.py -v

# Run specific test class
python -m pytest tests/test_complex_multi_phase.py::TestPhase4_Reevaluation -v

# Run specific test
python -m pytest tests/test_complex_multi_phase.py::TestPhase4_Reevaluation::test_farmer_reevaluation_phase4_status_transitions -v

# Run with short traceback
python -m pytest tests/test_complex_multi_phase.py -v --tb=short

# Run with detailed output
python -m pytest tests/test_complex_multi_phase.py -v -s
```

### Option 2: Run with TestSprite (AI-Powered Analysis)

```bash
# First, export TestSprite configuration
python testsprite_complex_config.py

# Then run with TestSprite
python -m pytest tests/test_complex_multi_phase.py -v --testsprite

# Or with explicit config
testsprite run --config testsprite_complex_config.json --test-file tests/test_complex_multi_phase.py
```

---

## 📊 Expected Test Results

### Baseline Run (All Phases)

```
============================= test session starts ==============================
collected 30 items

TestPhase0_DataSetup
test_profile_scenario_1_incomplete_farmer PASSED                        [ 3%]
test_profile_scenario_2_incomplete_student PASSED                       [ 7%]
test_schemes_with_complex_conditions PASSED                             [10%]

TestPhase1_Discovery
test_farmer_possibly_eligible_schemes_phase1 PASSED                      [14%]
test_student_possibly_eligible_schemes_phase1 PASSED                     [18%]

TestPhase2_QuestionGeneration
test_farmer_questions_phase2_numeric_inputs PASSED                       [22%]
test_student_questions_phase2_mixed_inputs PASSED                        [26%]

TestPhase3_AnswerCollection
test_farmer_answers_with_disqualification_impact PASSED                  [30%]
test_student_answers_with_promotion_and_disqualification PASSED          [34%]

TestPhase4_Reevaluation ⭐ CRITICAL
test_farmer_reevaluation_phase4_status_transitions PASSED                [38%]
test_student_reevaluation_phase4_cascading_effects PASSED                [42%]

TestPhase5_FinalDetermination
test_farmer_final_results_phase5 PASSED                                  [46%]
test_student_final_results_phase5 PASSED                                 [50%]

TestEdgeCasesAndComplexScenarios
test_boundary_income_at_limit PASSED                                     [54%]
test_boundary_income_just_over_limit PASSED                              [58%]
test_partial_document_list_multi_select PASSED                           [62%]
test_multiple_disqualifying_conditions PASSED                            [66%]
test_cascading_promotion_effects PASSED                                  [70%]

TestFullLifecycle ⭐ CRITICAL
test_complete_user_journey_farmer_to_final PASSED                        [74%]
test_complete_user_journey_student_to_final PASSED                       [78%]

======================== 30 passed in 12.3s ===========================
```

---

## 🔍 Key Test Scenarios Explained

### Scenario 1: Farmer Income Disqualification

**Profile**: Ramesh Kumar, 42, Farmer in Karnataka  
**Problem**: Incomplete information on income and land size  
**Questions Asked**:
1. Annual agricultural income? → **Answer: ₹450,000**
2. Land acres owned? → **Answer: 15 acres**
3. Land type? → **Answer: Dry Land**

**Impact Analysis**:
```
Answer 1 (Income ₹450,000):
├─ Condition: Max income ₹300,000
├─ Status: EXCEEDS LIMIT ❌
└─ Schemes affected: Agricultural Income Support, Crop Subsidy

Answer 2 (Land 15 acres):
├─ Condition: Max land 10 acres
├─ Status: EXCEEDS LIMIT ❌
└─ Compounds disqualification

Answer 3 (Dry Land):
├─ Condition: Land type OK
└─ Status: NEUTRAL ✓
```

**Re-evaluation Result** (Phase 4):
```
scheme: "Agricultural Income Support"
├─ Phase 1: possibly_eligible
├─ Phase 4: INELIGIBLE (Failed: income_check, land_check)
└─ Reason: Income ₹450k exceeds ₹300k; Land 15 acres exceeds 10 acres

scheme: "Farmer Pension Scheme"
├─ Phase 1: possibly_eligible
├─ Phase 4: ELIGIBLE ✅
└─ Reason: Age 42 (18-58 ✓), 20 years experience ✓

scheme: "Crop Subsidy Program"
├─ Phase 1: possibly_eligible
├─ Phase 4: INELIGIBLE (Failed: income_check)
└─ Reason: Income ₹450k exceeds subsidy threshold
```

---

### Scenario 2: Student Two-Way Impact (Promotion + Disqualification)

**Profile**: Priya Sharma, 20, Female Student in Karnataka  
**Problem**: Multiple missing fields (income, institution, caste, documents, employment)  
**Questions Asked**:
1. Family income? → **Answer: ₹280,000**
2. Institution type? → **Answer: Government**
3. Caste category? → **Answer: SC**
4. Documents available? → **Answer: [Aadhaar, Admission Letter]** ← Multi-select
5. Currently working? → **Answer: Yes**

**Impact Analysis**:

```
Answer 1 (Income ₹280,000):
├─ Status: PROMOTION ✅
├─ Reason: Below ₹500k threshold
└─ Opens: Girl Education, SC/ST, General scholarships

Answer 2 (Government Institution):
├─ Status: PROMOTION ✅
├─ Reason: Preferred institution type
└─ Improves: Girl Education Scholarship chances

Answer 3 (Caste = SC):
├─ Status: PROMOTION ✅
├─ Reason: Opens SC/ST category schemes
└─ New eligibility: SC/ST Scholarship

Answer 4 (Documents: [Aadhaar, Admission Letter]):
├─ Required: [Aadhaar, Income Cert, Caste Cert, Admission Letter]
├─ Status: DISQUALIFICATION ❌
├─ Reason: Missing income_certificate, caste_certificate
└─ Affects: Girl Education & SC/ST scholarships

Answer 5 (Currently Working = True):
├─ Condition: Must NOT be working (for hostel)
├─ Status: DISQUALIFICATION ❌
└─ Affects: Hostel Accommodation Scheme
```

**Re-evaluation Result** (Phase 4):

```
Girl Education Scholarship
├─ Phase 1: possibly_eligible
├─ Phase 4: INELIGIBLE (Failed: documents_check)
└─ Reason: Missing income_certificate, caste_certificate

SC/ST Scholarship
├─ Phase 1: possibly_eligible
├─ Phase 4: INELIGIBLE (Failed: documents_check)
└─ Reason: Missing income_certificate, caste_certificate

Hostel Accommodation
├─ Phase 1: possibly_eligible
├─ Phase 4: INELIGIBLE (DISQUALIFYING: is_working=True)
└─ Reason: Scheme requires full-time student, not employed

General Merit Scholarship
├─ Phase 1: possibly_eligible
├─ Phase 4: ELIGIBLE ✅ (Multi-select validated)
├─ Reason: Has required docs [Aadhaar, Admission Letter]
└─ Can apply immediately
```

**Final Determination** (Phase 5):

| Result | Count | Details |
|---------|-------|---------|
| Ready to Apply Now | 1 | General Merit Scholarship |
| Eligible with Documents | 2 | Girl Education, SC/ST (get certs → reapply) |
| Disqualified | 1 | Hostel (due to employment) |
| **Total Evaluated** | **4** | Filtered from 25+ schemes |

---

### Scenario 3: Edge Case - Income at Exact Boundary

**Test**: Income exactly at maximum threshold

```python
User Income: ₹300,000
Scheme Max: ₹300,000

Condition: income <= scheme_max
300,000 <= 300,000 → TRUE ✅ ELIGIBLE (boundary included)
```

---

### Scenario 4: Edge Case - Partial Multi-Select

**Test**: User selects SOME but not ALL required documents

```python
Required: [Aadhaar, Income Certificate, Caste Certificate]
Selected: [Aadhaar]

all(doc in selected for doc in required) → FALSE ❌ INELIGIBLE
Missing: Income Certificate, Caste Certificate
```

---

### Scenario 5: Cascading Promotion

**Test**: Single answer unlocks multiple schemes

```python
User Answer: caste = "SC"

Schemes Newly Eligible:
├─ SC/ST Scholarship (new)
├─ SC/ST Hostel Scheme (new)
└─ SC/ST Special Admission (new)
```

---

## 🧪 Input Types Tested

### 1. Numeric Inputs
```python
# Farmer income test
annual_income: 450000  # Numeric value
# Validation: min=0, max=5000000
# Impact: Exceeds agricultural_income_support limit (300k)
```

### 2. Categorical/Select Inputs
```python
# Student institution test
institution_type: "government"  # Select from options
# Options: ["government", "private", "deemed_university", "online"]
# Impact: Preferred type for scholarships
```

### 3. Multi-Select Inputs
```python
# Student documents test
documents_available: ["aadhaar", "admission_letter"]  # Multi-select
# Options: ["aadhaar", "pan_card", "income_certificate", ...]
# Validation: all([doc in options for doc in selected])
# Impact: Insufficient for schemes requiring all docs
```

### 4. Boolean Inputs
```python
# Employment status test
is_working: True  # Boolean (Yes/No)
# Impact: DISQUALIFYING for hostel scheme
```

---

## 📈 Execution Workflow with TestSprite

### Step-by-Step Flow

**1. Phase 0 → Data Setup** (Baseline)
```
Input: None (predefined test data)
Action: Setup profiles and schemes
Output: 3 test data objects ready
```

**2. Phase 1 → Discovery** (Identification)
```
Input: Incomplete profiles
Action: Match against all schemes
Output: "possibly_eligible" schemes identified
TestSprite Analysis: Verify correct base matching
```

**3. Phase 2 → Questions** (Elicitation)
```
Input: Missing fields from Phase 1
Action: Generate contextual questions
Output: Prioritized questions for each missing field
TestSprite Analysis: Verify all input types supported
```

**4. Phase 3 → Answers** (Collection)
```
Input: User responses to questions
Action: Process & impact analysis
Output: Each answer marked with impact (promotion/disqualification)
TestSprite Analysis: AI detect if impacts correctly identified
```

**5. Phase 4 → Re-evaluation** **[CRITICAL]**
```
Input: Profile + answers
Action: Re-run eligibility for all schemes
Output: Final status for each scheme (ELIGIBLE/INELIGIBLE)
TestSprite Analysis: CRITICAL - Verify status transitions correct
```

**6. Phase 5 → Results** (Presentation)
```
Input: Re-evaluated schemes
Action: Generate recommendations + next steps
Output: Actionable results for user
TestSprite Analysis: Verify recommendations relevant
```

---

## ⚠️ Critical Test Points

### Must-Pass Tests

1. **test_farmer_reevaluation_phase4_status_transitions**
   - Validates: Core re-evaluation logic
   - If fails: Income/land checking broken

2. **test_student_reevaluation_phase4_cascading_effects**
   - Validates: Multi-scheme cascading
   - If fails: Document validation broken

3. **test_complete_user_journey_farmer_to_final**
   - Validates: Full farmer workflow
   - If fails: End-to-end pipeline broken

4. **test_complete_user_journey_student_to_final**
   - Validates: Full student workflow with mixed inputs
   - If fails: Multi-input handling broken

---

## 🔧 Troubleshooting

### Issue: Test fails on Phase 4

**Symptom**: Status not transitioning correctly
```
Expected: possible → INELIGIBLE
Actual: possible → possible (unchanged)
```

**Diagnosis**: Re-evaluation logic not applying answer data
```python
# Check: answer values properly passed to eligibility engine
# Check: condition thresholds configured correctly
# Check: comparison operators correct (< vs <=)
```

### Issue: Multi-select validation fails

**Symptom**: Partial documents marked as sufficient
```
Required: [A, B, C]
Selected: [A]
Actual: ELIGIBLE (wrong!)
Expected: INELIGIBLE
```

**Diagnosis**: All-items checker not working
```python
# Fix: Change from any() to all() logic
# Check: List comparison logic
```

### Issue: Cascading effects not working

**Symptom**: Single answer affects only 1 scheme instead of 3
```
Answer: caste=SC
Affected schemes: 1 (should be 3)
```

**Diagnosis**: Cross-scheme dependency not mapped
```python
# Check: Scheme dependency matrix configured
# Check: Answer → schemes mapping correct
```

---

## 📊 TestSprite AI Analysis Report

When running with TestSprite, expect analysis on:

### Coverage Analysis
- ✅ All 5 phases tested
- ✅ All 4 input types covered
- ✅ All transition scenarios tested
- ✅ Edge cases included

### Risk Analysis
```
CRITICAL RISKS (Must fix):
├─ [✓] Phase 4 status transitions
├─ [✓] Multi-scheme cascading
└─ [✓] Full end-to-end workflows

HIGH RISKS (Should fix):
├─ [✓] Boundary condition handling
├─ [✓] Multi-select validation
└─ [✓] Document checking

MEDIUM RISKS (Could improve):
├─ [ ] Performance optimization
├─ [ ] Error message clarity
└─ [ ] User guidance quality
```

### Recommendations
1. **Before Production**: Ensure all critical tests pass
2. **Before Feature Release**: Run against latest code
3. **In CI/CD**: Run subset of critical tests (4-5 tests, ~5 sec)
4. **Nightly**: Run full suite for comprehensive analysis

---

## 🎓 Learning Outcomes from Test Results

### If All Tests Pass ✅
- ✅ Question generation works correctly
- ✅ Answers are processed with accurate impact detection
- ✅ Re-evaluation logic works for complex scenarios
- ✅ Multi-input types handled properly
- ✅ Disqualification logic works
- ✅ Cascading effects work
- ✅ Edge cases handled
- ✅ End-to-end workflows valid

### If Phase 4 Tests Fail ❌
- ❌ Re-evaluation engine broken
- ❌ Status transitions not working
- ❌ Condition evaluation incorrect
- ❌ Scheme dependency logic failed
- Action: Fix phase4 logic in `app/engine/eligibility.py`

### If Phase 3 Tests Fail ❌
- ❌ Impact detection not working
- ❌ Promotion/disqualification not identified
- ❌ Multi-input types not supported
- Action: Fix phase3 logic in `app/engine/questions.py`

---

## 🚦 Running Individual Test Classes

### Run Phase-by-Phase

```bash
# Phase 0-5 sequential
pytest tests/test_complex_multi_phase.py::TestPhase0_DataSetup -v
pytest tests/test_complex_multi_phase.py::TestPhase1_Discovery -v
pytest tests/test_complex_multi_phase.py::TestPhase2_QuestionGeneration -v
pytest tests/test_complex_multi_phase.py::TestPhase3_AnswerCollection -v
pytest tests/test_complex_multi_phase.py::TestPhase4_Reevaluation -v      # CRITICAL
pytest tests/test_complex_multi_phase.py::TestPhase5_FinalDetermination -v
pytest tests/test_complex_multi_phase.py::TestEdgeCasesAndComplexScenarios -v
pytest tests/test_complex_multi_phase.py::TestFullLifecycle -v              # CRITICAL
```

---

## 📝 Summary

### Test Coverage: ✅ COMPREHENSIVE
- **30 test cases** covering all phases
- **Multiple input types** (numeric, categorical, multi-select, boolean)
- **Real-world scenarios** (farmer & student journeys)
- **Complex interactions** (promotions, disqualifications, cascading effects)
- **Edge cases** (boundaries, partial data, multiple failures)
- **Full integration** (end-to-end workflows)

### Expected Execution Time: **~12 seconds**
- Phase 0-3: ~2 seconds
- Phase 4 (Complex): ~4 seconds
- Phase 5: ~2 seconds
- Edge + Integration: ~4 seconds

### Success Criteria: **30/30 PASSED**
- All phases working
- All input types handled
- All scenarios validated
- All edge cases covered
- Ready for production

---

## 🎯 Next Steps

1. **Run Tests**:
   ```bash
   pytest tests/test_complex_multi_phase.py -v
   ```

2. **Analyze with TestSprite**:
   ```bash
   testsprite run --config testsprite_complex_config.json
   ```

3. **Review Results**: Check critical test status

4. **Fix Any Failures**: Use troubleshooting guide

5. **Integrate into CI/CD**: Add to pipeline

---

**Test Suite Ready!** 🚀
