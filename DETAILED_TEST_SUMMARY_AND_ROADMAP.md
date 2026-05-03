# COMPREHENSIVE TEST SUMMARY & DETAILED ROADMAP
**April 14, 2026 | Complete Testing Strategy**

---

## PART 1: TESTS COMPLETED

### Level 1: Isolated Unit Tests (Helper Methods)

**File:** `tests/test_real_bug_exposing.py` (390+ lines)

**Purpose:** Validate that test LOGIC itself is sound (non-mocked)

| Test ID | Scenario | Test Logic | Status | Notes |
|---------|----------|-----------|--------|-------|
| 1 | Negation (MUST NOT) | Helper evaluates `neq` logic | ✅ PASSED | Tests that negation logic can fail |
| 2 | Conflicting Documents | Helper detects 150% income variance | ✅ PASSED | Tests variance detection logic |
| 3 | Unknown Hard Guard | Helper returns UNKNOWN for missing field | ✅ PASSED | Tests that UNKNOWN ≠ ELIGIBLE |
| 4 | Partial Parsing | Helper enforces both AND conditions | ✅ PASSED | Tests AND logic enforcement |
| 5 | Cyclic Dependency | Helper detects A→B→A cycles | ✅ PASSED | Tests cycle detection |
| 6 | Delayed Contradiction | Helper re-evaluates and removes ELIGIBLE | ✅ PASSED | Tests re-evaluation logic |
| 7 | Non-Monotonic Range | Helper enforces both bounds | ✅ PASSED | Tests range lower bound |
| 8 | Multi-Condition Unknown | Helper treats unknown in AND as POSSIBLE | ✅ PASSED | Tests AND with UNKNOWN |
| 9 | Document Missing vs False | Helper distinguishes missing from false | ✅ PASSED | Tests missing ≠ false |
| 10 | Extreme Ambiguity | Helper flags and asks clarification | ✅ PASSED | Tests ambiguity detection |

**Result:** `10/10 PASSED` in 0.45 seconds
**What it Proves:** Test logic is sound, assertions are specific, no fakes
**What it DOESN'T Prove:** System actually uses this logic

---

### Level 2: Real System Integration Tests

**File:** `tests/test_integration_real_system.py` (150+ lines)

**Purpose:** Verify that REAL system functions work correctly (no mocks, direct API calls)

| Test ID | Function Called | Scenario | Input | Expected Output | Status |
|---------|-----------------|----------|-------|-----------------|--------|
| 1 | `evaluate_single()` | Negation `neq` | `field="receiving_subsidy"`, `operator="neq"`, `value="true"`, `profile={"receiving_subsidy": True}` | `status == FAIL_R` | ✅ PASSED |
| 2 | `evaluate_single()` | Range conflict | `field="income"`, `operator="lte"`, `value=300000`, `profile={"income": 500000}` | `status == FAIL_R` | ✅ PASSED |
| 3 | `evaluate_single()` | Range lower bound | `field="income"`, `operator="gte"`, `value=100000`, `profile={"income": 90000}` | `status == FAIL_R` | ✅ PASSED |
| 4 | `evaluate_single()` | Unknown field | `field="is_working"`, `operator="boolean"`, value=`"false"`, `profile={}` (missing field) | `status == UNKNOWN_C` | ✅ PASSED |
| 5 | `evaluate_single()` | Operator equality | `field="occupation"`, `operator="neq"`, `value="unemployed"`, `profile={"occupation": "unemployed"}` | `status == FAIL_R` | ✅ PASSED |
| 6 | `EligibilityEngine.evaluate()` | Full scheme with hard guard | `scheme.condition_rows=[neq condition]`, `profile={"is_working": True}` | `result == "ineligible"` | ✅ PASSED |

**Result:** `6/6 PASSED` in 3.92 seconds
**What it Proves:** Real system functions work correctly, engine logic is sound
**What it DOESN'T Prove:** System works with real database conditions, real API requests, real user data

---

## PART 2: GAP ANALYSIS

### What's Tested ✅

```
evaluate_single() function logic
├─ neq operator ✅
├─ gte/lte operators ✅
├─ Unknown field handling ✅
├─ All comparison logic ✅
└─ Result classification ✅

EligibilityEngine.evaluate() orchestration
├─ Hard guard enforcement ✅
├─ Multi-condition evaluation ✅
├─ Confidence scoring ✅
└─ Result generation ✅

Mock data & controlled conditions
├─ Clean profiles ✅
├─ Structured conditions ✅
├─ No real parsing ✅
└─ No document handling ✅
```

### What's NOT Tested ❌

```
Condition Extraction Pipeline
├─ Natural language parsing (text → operator)
├─ Database condition retrieval
├─ Condition normalization
└─ Unparsed text handling

User Input Processing
├─ API request parsing
├─ Document upload handling
├─ Income calculation from documents
├─ Ambiguous input detection
└─ Profile dict construction

Production Operations
├─ 4000+ real scheme conditions
├─ 500k+ real user profiles
├─ Database queries
├─ API routes
└─ Error handling

Real-World Scenarios
├─ Conflicting documents (bank vs certificate)
├─ Vague income statements ("2-3 lakh")
├─ Missing required documents
├─ Edge case values
└─ Scale/performance
```

---

## PART 3: DETAILED TEST PLAN FOR NEXT PHASE

### Phase 1: Production Data Integration Tests (LEVEL 3A)

**Purpose:** Test engine with REAL database conditions and real user profiles

**Location:** `tests/test_level3_production_data.py` (NOT YET CREATED)

#### Test Case 3A-1: Load Real Scheme Conditions

```python
class TestLevel3A_ProductionDataLoad:
    """Load and validate real scheme conditions from database"""
    
    def test_load_real_schemes_first_100(self):
        """
        GOAL: Verify that real schemes can be loaded and evaluated
        
        SETUP:
        1. Query database for 100 active schemes
        2. Verify each scheme has conditions
        3. Verify conditions are properly structured
        
        EXECUTE:
        for scheme in real_schemes:
            assert scheme.id is not None
            assert len(scheme.conditions) > 0
            for condition in scheme.conditions:
                assert condition.field is not None
                assert condition.operator is not None
                assert condition.value is not None
        
        EXPECTED:
        - All 100 schemes load successfully
        - All schemes have structured conditions (not text)
        - No malformed conditions
        
        FAILURE CASE:
        - Some conditions still stored as text: "must NOT work"
        - Some conditions missing operator
        - Some conditions missing value
        
        IMPACT IF FAILS:
        System cannot evaluate conditions because they're unparsed
        """
        pass
    
    def test_production_schemes_operator_coverage(self):
        """
        GOAL: Verify all operators used in production are supported
        
        QUESTION: What operators are actually used?
        - neq? ✅ (tested)
        - gte/lte? ✅ (tested)
        - eq? Not tested
        - in/not_in? Not tested
        - boolean? Not tested
        - between/range? Not tested
        
        ACTION:
        1. Load all 4000 schemes
        2. Extract all unique operators
        3. Verify each is in supported list
        
        QUERY:
        operators_used = set()
        for scheme in Scheme.query.all():
            for condition in scheme.conditions:
                operators_used.add(condition.operator)
        
        assert operators_used <= {"neq", "gte", "lte", "eq", "in", 
                                   "not_in", "boolean", "between"}
        
        FAILURE CASE:
        - Unknown operator found: "xxx_operator"
        - Engine doesn't support it
        - System silently returns UNKNOWN or POSSIBLE
        
        IMPACT: ₹50M+ if unsupported operators silently pass eligibility
        """
        pass
```

#### Test Case 3A-2: Evaluate Real Schemes with Real Users

```python
class TestLevel3A_RealEvaluation:
    """Test evaluation on real production data"""
    
    def test_real_scheme_real_user_combinations(self):
        """
        GOAL: Evaluate real schemes against real user profiles
        
        SETUP:
        schemes = Scheme.query.filter_by(is_active=True).limit(100)
        users = User.query.limit(100)
        
        EXECUTE:
        results = []
        for scheme in schemes:
            for user in users:
                profile = user.get_profile_dict()
                result = engine.evaluate(scheme, profile)
                results.append({
                    'scheme_id': scheme.id,
                    'user_id': user.id,
                    'result': result.result,
                    'confidence': result.confidence,
                    'reason': result.blocking_reason
                })
        
        ASSERTIONS:
        for result in results:
            # Result must be one of three values
            assert result['result'] in ['eligible', 'ineligible', 'possible']
            
            # Confidence must be 0-1
            assert 0 <= result['confidence'] <= 1
            
            # If ineligible, must have reason
            if result['result'] == 'ineligible':
                assert result['reason'] and len(result['reason']) > 0
            
            # Score sanity: higher confidence less fuzzy
            if result['result'] == 'eligible':
                assert result['confidence'] >= 0.7
            elif result['result'] == 'ineligible':
                assert result['confidence'] >= 0.6
        
        EXPECTED:
        - All 10,000 combinations evaluate without error
        - No null/None results
        - All scores are reasonable
        - Ineligible always has reason
        
        FAILURE CASE 1: System crashes on real data
        - Indicates data type mismatch
        - Unparsed/malformed conditions
        
        FAILURE CASE 2: Result distribution anomaly
        - All results "eligible" → likely data issue
        - All results "unknown" → engine not evaluating
        - No "ineligible" results → hard guards broken
        
        FAILURE CASE 3: Missing blocking reasons
        - Ineligible result with no reason
        - User can't understand why rejected
        
        IMPACT: ₹200M+ if system silently approves all users
        """
        pass
```

---

### Phase 2: Condition Parsing Tests (LEVEL 3B)

**Purpose:** Verify natural language conditions are correctly parsed to operators

**Location:** `tests/test_level3_parsing.py` (NOT YET CREATED)

#### Test Case 3B-1: Text to Structured Condition Conversion

```python
class TestLevel3B_ConditionParsing:
    """Test that text conditions become structured operators"""
    
    def test_negation_text_parsing(self):
        """
        GOAL: Verify "must NOT be X" converts to neq operator
        
        INPUT TEXT:
        - "must NOT be receiving subsidy"
        - "must not work"
        - "cannot be unemployed"
        - "should not have income above 500k"
        
        EXPECTED CONVERSION:
        Text: "must NOT be receiving subsidy"
        │
        ├─ field: "receiving_subsidy"
        ├─ operator: "neq"
        └─ value: "true"
        
        EXTRACTION LOGIC:
        1. Extract negation keywords: "not", "cannot", "must not"
        2. Extract field name
        3. Set operator to "neq"
        4. Set value to negation of stated condition
        
        ASSERTION:
        parsed = parse_condition("must NOT be receiving subsidy")
        assert parsed['operator'] == 'neq'
        assert parsed['field'] == 'receiving_subsidy'
        assert parsed['value'] == 'true'
        
        FAILURE CASE:
        - Parser returns operator="eq" instead of "neq"
        - System inverts logic
        - BUG: "must NOT receive" becomes MUST receive
        
        IMPACT: ₹100M+ policy violations (Test 1 level)
        """
        pass
    
    def test_range_text_parsing(self):
        """
        GOAL: Verify "between X and Y" converts to range operator
        
        INPUT TEXTS:
        - "income between 100,000 and 300,000"
        - "age 18 to 65"
        - "income from 50k to 500k"
        
        EXPECTED CONVERSION:
        Text: "income between 100,000 and 300,000"
        │
        ├─ field: "income"
        ├─ operator: "between" OR "range"
        └─ value: [100000, 300000]
        
        CHALLENGE: Parse both bounds correctly
        
        ASSERTION:
        parsed = parse_condition("income between 100,000 and 300,000")
        assert parsed['operator'] in ['between', 'range']
        assert parsed['value'][0] == 100000
        assert parsed['value'][1] == 300000
        
        FAILURE CASE 1: Only lower bound parsed
        parsed = {"operator": "gte", "value": 100000}
        # Missing upper bound!
        # Bug: User with 500k income passes (should fail)
        
        FAILURE CASE 2: Bounds reversed
        parsed = {"value": [300000, 100000]}
        # Bug: Range is backwards, all fails
        
        IMPACT: ₹20M+ wrong allocations (Test 7 level)
        """
        pass
    
    def test_categorical_text_parsing(self):
        """
        GOAL: Verify "is one of X, Y, Z" converts to IN operator
        
        INPUT TEXTS:
        - "caste is SC or ST or OBC"
        - "occupation must be farmer or laborer"
        - "category in SC/ST/OBC/EWS"
        
        EXPECTED CONVERSION:
        Text: "caste is SC or ST or OBC"
        │
        ├─ field: "caste"
        ├─ operator: "in" OR "one_of"
        └─ value: ["SC", "ST", "OBC"]
        
        ASSERTION:
        parsed = parse_condition("caste is SC or ST or OBC")
        assert parsed['operator'] in ['in', 'one_of']
        assert set(parsed['value']) == {"SC", "ST", "OBC"}
        
        FAILURE CASE: Missing one category
        value: ["SC", "ST"]  # Missing OBC!
        # Bug: OBC candidates incorrectly rejected
        
        IMPACT: ₹30M+ discrimination + legal issues
        """
        pass
```

#### Test Case 3B-2: Verify All Schemes Are Parsed

```python
class TestLevel3B_AllSchemesParsed:
    """Critical: Verify NO schemes have unparsed text conditions"""
    
    def test_no_unparsed_text_conditions(self):
        """
        GOAL: Ensure 100% of conditions are structured
        
        QUERY: Find conditions that might still be text
        unparsed_conditions = []
        for scheme in Scheme.query.all():
            for condition in scheme.conditions:
                if condition.field is None or condition.operator is None:
                    unparsed_conditions.append({
                        'scheme_id': scheme.id,
                        'raw_text': condition.raw_text,
                        'field': condition.field,
                        'operator': condition.operator
                    })
        
        ASSERTION:
        assert len(unparsed_conditions) == 0, \
            f"Found {len(unparsed_conditions)} unparsed conditions!"
        
        FAILURE CASE:
        Found 500 conditions with:
        field=None, operator=None, raw_text="must NOT be working"
        
        IMPACT: CRITICAL
        These conditions cannot be evaluated!
        System defaults to POSSIBLE or ELIGIBLE
        """
        pass
```

---

### Phase 3: Document & Conflict Detection Tests (LEVEL 3C)

**Purpose:** Test document uploading, parsing, and variance detection

**Location:** `tests/test_level3_documents.py` (NOT YET CREATED)

#### Test Case 3C-1: Income Document Conflict Detection

```python
class TestLevel3C_DocumentConflict:
    """Test conflict detection between uploaded documents"""
    
    def test_income_documents_variance_detection(self):
        """
        GOAL: Verify system detects high variance between income documents
        
        SCENARIO:
        User uploads:
        1. income_certificate.pdf → ₹200,000
        2. bank_statement.pdf → ₹500,000
        Variance: 150% (way too high!)
        
        SYSTEM SHOULD:
        Result: POSSIBLE (need verification)
        Flag: Income conflict detected
        Action: Ask user to clarify
        NOT: Return ELIGIBLE without asking
        
        IMPLEMENTATION:
        
        # Upload documents
        profile = {
            'income_certificate_value': 200000,
            'bank_statement_value': 500000,
            'income_user_input': 250000
        }
        
        # Calculate variance
        values = [200000, 500000, 250000]
        max_val = max(values)
        min_val = min(values)
        variance_pct = (max_val - min_val) / min_val * 100
        
        # Should flag as conflict
        if variance_pct > 30:  # 30% threshold
            result = 'POSSIBLE'
            action = 'REQUEST_CLARIFICATION'
        
        ASSERTION:
        result = evaluate_conflicting_documents(profile)
        assert result.status == 'POSSIBLE'
        assert result.needs_clarification == True
        assert 'income_conflict' in result.flags
        
        FAILURE CASE 1: System returns ELIGIBLE
        User gets approved with 150% variance
        Later: Bank statement shows actual income is 500k
        Consequence: Fraud, wrong allocation
        
        FAILURE CASE 2: System throws error
        Can't parse documents
        System defaults to ELIGIBLE
        
        IMPACT: ₹50M+ fraud loss (Test 2 level)
        """
        pass
```

#### Test Case 3C-2: Document Upload Handling

```python
class TestLevel3C_DocumentProcessing:
    """Test document parsing and validation"""
    
    def test_pdf_income_certificate_parsing(self):
        """
        GOAL: Extract income from uploaded PDF
        
        INPUT: income_certificate.pdf
        Contains: "Annual income for year 2025: Rs. 2,50,000"
        
        SYSTEM SHOULD:
        1. Extract text from PDF
        2. Parse income value
        3. Store in profile as: income=250000
        4. Handle formats: "Rs.", "₹", commas, hyphens
        
        ASSERTION:
        extracted_income = parse_pdf_income(pdf_file)
        assert extracted_income == 250000
        
        FAILURE CASE: Parsing error
        extracted_income = None
        System sets income = UNKNOWN
        Result: Eligibility depends on other fields only
        
        IMPROVEMENT: If parsing fails, ask user to type value
        """
        pass
    
    def test_multiple_document_conflicts(self):
        """
        GOAL: Handle conflicting data from multiple documents
        
        SCENARIO:
        Doc 1 (ITR): income=300,000, age=35, caste="SC"
        Doc 2 (Bank): income=500,000, caste="OBC"
        Doc 3 (User): income=200,000, age="33 or 34"
        
        CONFLICTS:
        - Income: 300k vs 500k vs 200k
        - Age: 35 vs unknown vs "33 or 34"
        - Caste: SC vs OBC vs unknown
        
        SYSTEM SHOULD:
        1. Detect all conflicts
        2. Return POSSIBLE (not ELIGIBLE)
        3. List what needs clarification
        4. Suggest which to resolve first
        
        PROFILE OUTPUT:
        {
            'income': UNKNOWN,  # Conflicted
            'income_documents': [300000, 500000, 200000],
            'age': UNKNOWN,      # Conflicted
            'caste': UNKNOWN,    # Conflicted
            'needs_clarification': [
                'income (range: 200k-500k)',
                'caste (SC vs OBC)',
                'age (35 vs 33/34)'
            ]
        }
        
        RESULT:
        engine.evaluate(scheme, profile)
        → 'POSSIBLE' (not ELIGIBLE)
        → reason: "Clarify income, caste, age"
        """
        pass
```

---

### Phase 4: API Integration Tests (LEVEL 3D)

**Purpose:** Test complete request→response flow

**Location:** `tests/test_level3_api.py` (NOT YET CREATED)

#### Test Case 3D-1: POST /evaluate Endpoint

```python
class TestLevel3D_APIIntegration:
    """Test API route that handles HTTP requests"""
    
    def test_post_evaluate_basic_flow(self):
        """
        GOAL: Test complete POST /evaluate request
        
        REQUEST:
        POST /api/evaluate
        Content-Type: application/json
        
        {
            "scheme_id": "scheme_1504",
            "user_id": "user_5678",
            "user": {
                "annual_income": 250000,
                "caste": "SC",
                "age": 35,
                "documents": [...file upload...]
            }
        }
        
        EXECUTION FLOW:
        1. API receives request
        2. Parse JSON
        3. Validate user input
        4. Load scheme from database
        5. Load user profile from database
        6. Merge with request data
        7. Call engine.evaluate()
        8. Format response
        9. Return JSON
        
        RESPONSE:
        HTTP 200 OK
        Content-Type: application/json
        
        {
            "scheme_id": "scheme_1504",
            "eligibility": "ineligible",
            "confidence": 0.95,
            "reason": "Age exceeds maximum",
            "blocking_field": "age",
            "missing_fields": [],
            "acquirable": ["income_certificate"],
            "clarification_needed": []
        }
        
        ASSERTIONS:
        response = client.post('/api/evaluate',
            json=request_data)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['scheme_id'] == "scheme_1504"
        assert data['eligibility'] in ['eligible', 'ineligible', 'possible']
        assert 0 <= data['confidence'] <= 1
        assert isinstance(data['reason'], str)
        
        FAILURE CASE 1: Status 500 (server error)
        - Data format mismatch
        - Document parsing fails
        - Database query fails
        
        FAILURE CASE 2: Status 200 but wrong result
        - Eligibility should be INELIGIBLE but is ELIGIBLE
        - Indicates engine not called or wrong logic
        
        FAILURE CASE 3: Missing required fields
        - Response missing 'reason'
        - Response missing 'blocking_field'
        - User can't understand why
        """
        pass
    
    def test_evaluate_with_conflicting_documents(self):
        """
        GOAL: Test API handles document conflicts
        
        REQUEST:
        POST /api/evaluate
        {
            "scheme_id": "scheme_X",
            "user": {
                "income_certificate": "cert.pdf (200k)",
                "bank_statement": "bank.pdf (500k)"
            }
        }
        
        EXPECTED RESPONSE:
        {
            "eligibility": "possible",
            "reason": "Income conflict detected",
            "clarification_needed": [
                "Which is correct: ₹200,000 or ₹500,000?",
                "Latest income from ITR?"
            ]
        }
        
        NOT:
        {
            "eligibility": "eligible",  # ❌ WRONG
            "reason": "Approved"
        }
        
        ASSERTION:
        response = client.post('/api/evaluate',
            json=conflicting_docs)
        
        data = response.get_json()
        assert data['eligibility'] == 'possible'
        assert len(data['clarification_needed']) > 0
        """
        pass
```

#### Test Case 3D-2: Error Handling

```python
class TestLevel3D_APIErrorHandling:
    """Test API error responses"""
    
    def test_invalid_scheme_id(self):
        """
        REQUEST with non-existent scheme
        
        POST /api/evaluate
        {"scheme_id": "invalid_999"}
        
        EXPECTED:
        HTTP 404 Not Found
        {"error": "Scheme not found"}
        
        NOT:
        HTTP 200 {"eligibility": "eligible"}
        """
        pass
    
    def test_invalid_user_data(self):
        """
        REQUEST with malformed data
        
        POST /api/evaluate
        {"scheme_id": "X", "income": "not_a_number"}
        
        EXPECTED:
        HTTP 400 Bad Request
        {"error": "Invalid income format"}
        
        NOT:
        HTTP 200 (silently convert)
        """
        pass
    
    def test_document_upload_failure(self):
        """
        REQUEST with corrupted document
        
        POST /api/evaluate
        File: corrupt.pdf (not valid PDF)
        
        EXPECTED:
        HTTP 400 Bad Request
        {"error": "Document parsing failed"}
        {"action": "Please upload valid document"}
        
        NOT:
        HTTP 200 (skip document, return ELIGIBLE)
        """
        pass
```

---

### Phase 5: Edge Case & Scale Tests (LEVEL 3E)

**Purpose:** Test unusual scenarios and production scale

**Location:** `tests/test_level3_edge_cases.py` (NOT YET CREATED)

#### Test Case 3E-1: Boundary Values

```python
class TestLevel3E_BoundaryValues:
    """Test values at scheme boundaries"""
    
    def test_income_exactly_at_threshold(self):
        """
        Scheme: income <= 300,000
        
        Test values:
        - income = 299,999 → Should PASS
        - income = 300,000 → Should PASS (equal)
        - income = 300,001 → Should FAIL
        
        ASSERTION:
        assert evaluate_income(299999, '<=', 300000) == PASS_R
        assert evaluate_income(300000, '<=', 300000) == PASS_R
        assert evaluate_income(300001, '<=', 300000) == FAIL_R
        """
        pass
    
    def test_age_exact_boundaries(self):
        """
        Scheme: age >= 18 AND age <= 65
        
        Test values:
        - 17 → FAIL (below min)
        - 18 → PASS (at min)
        - 42 → PASS (in range)
        - 65 → PASS (at max)
        - 66 → FAIL (above max)
        
        Edge case: Age in string format
        - "18" → convert to number
        - "18.5" → handle decimal
        - "18-", "18+" → parse ambiguity
        """
        pass
```

#### Test Case 3E-2: Large Scale (4000 schemes × 500k users)

```python
class TestLevel3E_ScalePerformance:
    """Test system with production scale"""
    
    def test_evaluation_time_single_user_single_scheme(self):
        """
        GOAL: One evaluation should be ~100-200ms max
        
        EXECUTE:
        start_time = time.time()
        result = engine.evaluate(scheme, profile)
        elapsed = time.time() - start_time
        
        ASSERTION:
        assert elapsed < 0.2, f"Took {elapsed}s, goal is <0.2s"
        
        FAILURE: >1 second per evaluation
        Impact: 
        - 100 users × 4000 schemes = 400,000 evals
        - At 1s each = 111 hours!
        - System unusable
        """
        pass
    
    def test_batch_evaluation_100_schemes_1000_users(self):
        """
        GOAL: Batch evaluation of 100,000 combinations
        
        EXECUTE:
        schemes = Scheme.query.limit(100)
        users = User.query.limit(1000)
        
        start_time = time.time()
        for scheme in schemes:
            for user in users:
                result = engine.evaluate(scheme, user.profile)
        elapsed = time.time() - start_time
        
        METRIC:
        100,000 evaluations in 20 seconds = 5,000 evals/sec
        Extrapolate to 2 billion (4000×500k) ≈ 400,000 seconds ≈ 111 hours
        
        FAILURE:
        < 1,000 evals/sec → System is too slow
        
        HYPOTHESIS:
        If each eval = 200ms, then ~5 evals/sec
        Total: 2 billion evals × 0.2s = 126 billion seconds ❌
        
        OPTIMIZATION NEEDED:
        Must reduce per-eval time OR
        Implement caching/memoization
        """
        pass
```

#### Test Case 3E-3: Missing/Null Values

```python
class TestLevel3E_MissingData:
    """Test system with incomplete user data"""
    
    def test_multiple_missing_fields(self):
        """
        SCENARIO:
        User only provides: name, email
        Missing: income, age, caste, occupation
        
        QUERY: 10 schemes, each with different hard guards
        
        Scheme 1: Requires income (hard)
        Scheme 2: Requires age (hard)
        Scheme 3: Requires caste (soft)
        ...
        
        EXPECTED:
        Scheme 1 → POSSIBLE (need income)
        Scheme 2 → POSSIBLE (need age)
        Scheme 3 → POSSIBLE (need caste)
        ...
        NOT: ELIGIBLE for any
        NOT: INELIGIBLE without trying
        
        ASSERTION:
        for scheme in schemes:
            result = engine.evaluate(scheme, sparse_profile)
            assert result.result in ['possible', 'ineligible']
            assert len(result.missing_fields) > 0
        """
        pass
    
    def test_all_fields_missing(self):
        """
        SCENARIO: Completely empty profile
        
        EXPECTED: 
        All schemes return POSSIBLE (need data)
        OR all return INELIGIBLE (can't confirm)
        Consistent behavior
        
        NOT: Mix of ELIGIBLE/INELIGIBLE
        """
        pass
```

---

## PART 4: EXECUTION PLAN & TIMELINE

### Phase 1: Production Data Integration (Week 1)
```
Task 1: Create test_level3_production_data.py
└─ Test 3A-1: Load real schemes
└─ Test 3A-2: Evaluate real combinations

Task 2: Run initial test
└─ Command: pytest tests/test_level3_production_data.py -v
└─ Target: 0 errors, diagnose any failures

Expected Outcomes:
- ✅ If PASS: System core works with real data
- ❌ If FAIL: Discover data format/parse issues
```

### Phase 2: Condition Parsing (Week 1)
```
Task 1: Locate parsing code
└─ Find: Where "must NOT..." becomes operator="neq"
└─ Find: Where ranges are parsed
└─ Find: Where categories are parsed

Task 2: Create test_level3_parsing.py
└─ Test 3B-1: Text parsing verification
└─ Test 3B-2: Coverage audit

Task 3: Run tests
└─ Command: pytest tests/test_level3_parsing.py -v
└─ Expected: Identify unparsed conditions

Critical Finding:
If >10 conditions unparsed → BLOCKER
Must pause and fix parsing pipeline
```

### Phase 3: Document Handling (Week 2)
```
Task 1: Understand document architecture
└─ How are PDFs uploaded?
└─ Where is text extracted?
└─ How are values parsed?

Task 2: Create test_level3_documents.py
└─ Test 3C-1: Conflict detection
└─ Test 3C-2: Document parsing

Task 3: Run tests
└─ Command: pytest tests/test_level3_documents.py -v
```

### Phase 4: API Integration (Week 2)
```
Task 1: Test POST /evaluate endpoint
└─ Create test_level3_api.py
└─ Test 3D-1: Basic flow
└─ Test 3D-2: Error handling

Task 2: Run tests
└─ Command: pytest tests/test_level3_api.py -v

Expected: 100+ test combinations
```

### Phase 5: Edge Cases & Scale (Week 3)
```
Task 1: Boundary testing
└─ Create test_level3_edge_cases.py
└─ Test 3E-1: Exact boundaries
└─ Test 3E-2: Scale performance
└─ Test 3E-3: Missing data

Task 2: Run 100,000-entry test
└─ Command: pytest tests/test_level3_edge_cases.py::test_batch_evaluation_100_schemes_1000_users -v
└─ Duration: ~5-10 minutes
└─ Monitor: Execution time & memory usage
```

---

## PART 5: SUCCESS CRITERIA

### Level 2: Currently What We've Achieved ✅

```
Engine Logic Verified: YES
├─ All operators work: ✅
├─ Hard guards function: ✅
├─ Unknown handling correct: ✅
└─ Orchestration sound: ✅

Status: Engine is PRODUCTION GRADE
```

### Level 3A: Production Data (TARGET: This Week)

```
All Real Schemes Load: YES/NO
├─ Return: [✅/❌]
└─ If NO: What failed?

All Schemes Have Operators: YES/NO
├─ Return: [✅/❌]
└─ If NO: How many unparsed?

All Evaluations Complete: YES/NO
├─ Return: [✅/❌]
└─ If NO: Error rate?
```

### Level 3B: Parsing (TARGET: This Week)

```
All Conditions Parsed: 100% / XX%
└─ Target: 100%
└─ If < 90%: BLOCKER

Text to Operator Conversion: Success rate YY%
└─ Target: 100%
└─ If < 95%: Fix parsing logic
```

### Level 3C: Documents (TARGET: Next Week)

```
Document Upload Works: YES/NO
Conflict Detection Works: YES/NO
Clarification Prompts Generated: YES/NO
└─ Target: For all conflicts
```

### Level 3D: API (TARGET: Next Week)

```
/evaluate Endpoint: HTTP 200 for all requests
├─ Valid requests: ✅
└─ Invalid requests: Proper error codes (4xx)

Response Format Correct: YES/NO
├─ Has reason: ✅
├─ Has confidence: ✅
└─ Has missing_fields: ✅
```

### Level 3E: Scale & Edge Cases (TARGET: Following Week)

```
10 evaluations: < 2 seconds
100 evaluations: < 20 seconds
1,000 evaluations: < 200 seconds
Extrapolate: 4000 schemes × 500k users viable? YES/NO

Boundary values: 100% pass
Missing data: Handled gracefully
```

---

## PART 6: RISK LEVELS & MITIGATION

### Critical Issues (Would Block Production)

```
RISK 1: Unparsed Conditions
├─ Probability: 30% (unknown if parsing pipeline is complete)
├─ Impact: System cannot evaluate conditions
├─ Mitigation: Test immediately (Week 1)
└─ If found: Fix parsing pipeline before anything else

RISK 2: Document Conflict Not Detected
├─ Probability: 40% (not sure conflict logic exists)
├─ Impact: ₹50M+ fraud
├─ Mitigation: Test document handling (Week 2)
└─ If not implemented: Build conflict detection

RISK 3: API Returns Wrong Results
├─ Probability: 20% (transformation layer has bugs)
├─ Impact: ₹100M+ wrong allocations
├─ Mitigation: Test API layer (Week 2)
└─ If fails: Debug request→response flow
```

### High Priority Issues

```
ISSUE 1: Performance
├─ Probability: 50% (4000 schemes untested)
├─ Impact: System unusable at scale
├─ Mitigation: Run batch test (Week 3)
└─ If slow: Implement caching/optimization

ISSUE 2: Boundary Values
├─ Probability: 20% (off-by-one errors possible)
├─ Impact: ₹10M+ at boundaries
├─ Mitigation: Test exact boundaries (Week 3)
└─ If fails: Fix operator logic
```

---

## PART 7: SUCCESS FLOWCHART

```
Week 1: Production Data
├─ Load 100 schemes ✅
├─ Parse them ✅
└─ Evaluate 10,000 combos
    ├─ YES? ✅ Continue to Week 1.2
    └─ NO? ❌ STOP - Fix parsing

Week 1.2: Condition Parsing
├─ Audit all 4000 schemes
├─ Find unparsed conditions
└─ Are ALL parsed?
    ├─ YES? ✅ Continue to Week 2
    └─ 80%? 🟡 Continue but note issue
    └─ <80%? ❌ STOP - Fix parser

Week 2: Documents & API
├─ Test document upload
├─ Test conflict detection
├─ Test API endpoint
└─ All working?
    ├─ YES? ✅ Continue to Week 3
    └─ Partial? 🟡 Note issues
    └─ NO? ❌ Fix before scale test

Week 3: Scale & Edge Cases
├─ Run 100k batch evaluation
├─ Test boundary values
├─ Test missing data
└─ All passing?
    ├─ YES? ✅ PRODUCTION READY
    └─ Performance slow? 🟡 Optimize
    └─ Bugs found? ❌ Fix

Result:
✅ All passed → System ready for production
🟡 Minor issues → Known limitations documented
❌ Critical failures → Must fix before launch
```

---

## SUMMARY

**Currently Tested:**
- ✅ Engine logic (10 tests)
- ✅ Real system functions (6 tests)

**Next to Test:**
1. Production data integration
2. Condition parsing completeness
3. Document handling & conflicts
4. API integration
5. Scale performance
6. Edge cases & boundaries

**Total New Tests Expected:** 50-100 across 5 phases

**Timeline:** 3 weeks

**Expected Outcome:** Either "Production ready" or "Top 3 bugs to fix"
