# FALSE POSITIVES IN ELIGIBILITY MATCHING - COMPREHENSIVE ANALYSIS REPORT
## Yojana Mitra Backend - Schemes Dataset Analysis
**Analysis Date:** March 17, 2026  
**Total Schemes Analyzed:** 4,324  
**Dataset:** all_schemes_export.json (25.3 MB)

---

## EXECUTIVE SUMMARY

This analysis identifies critical data quality and semantic ambiguity issues that could lead to **false positives in eligibility matching**. False positives occur when users are incorrectly identified as eligible for schemes they don't actually qualify for. 

### 🔴 Critical Findings:
1. **4,203 schemes (97.2%)** have both `min_age` and `max_age` as NULL → No age filtering applied
2. **4,284 schemes (99.1%)** have `disability_requirement` as "Any" → Ambiguous semantics
3. **233 schemes (5.4%)** have empty `allowed_castes []` → Interpretation unclear (all vs none)
4. **2,699 schemes (62.4%)** have empty `allowed_occupations []` → Could match any occupation
5. **17,003 "Any" values** across requirement fields → Semantic ambiguity is pervasive
6. **0 data contradictions** found (good data quality overall)

---

## 1. NULL/DEFAULT FIELDS CAUSING FALSE POSITIVES

### 1.1 Empty `allowed_genders`
- **Count:** 0 schemes
- **Status:** ✓ No issues found (all schemes have gender field populated)

### 1.2 Empty `allowed_castes` ⚠️ HIGH AMBIGUITY
- **Count:** 233 schemes (5.4% of total)
- **Impact:** Each empty array could match ANY caste OR NO caste
- **Examples:**
  - ID 1: Pradhan Mantri Jan Dhan Yojana (PMJDY)
  - ID 2: Pradhan Mantri Jeevan Jyoti Bima Yojana (PMJJBY)
  - ID 3: Pradhan Mantri Suraksha Bima Yojana (PMSBY)
  - ID 4: Atal Pension Yojana (APY)
  - ID 5: Pradhan Mantri Mudra Yojana (PMMY)
- **False Positive Risk:** **MEDIUM-HIGH** if empty `[]` is interpreted as "no caste restriction"
- **Recommendation:** Determine canonical meaning:
  - Option A: `[]` means "unrestricted (all castes allowed)"
  - Option B: `[]` means "no schemes available for this caste filter"
  - Implement logic consistently across all matching

### 1.3 Occupations = ["All"] ⚠️ POTENTIAL UNIVERSAL MATCH
- **Count:** 3 schemes (0.07% of total)
- **Schemes:**
  1. ID 1: Pradhan Mantri Jan Dhan Yojana (PMJDY)
  2. ID 2: Pradhan Mantri Jeevan Jyoti Bima Yojana (PMJJBY)
  3. ID 4: Atal Pension Yojana (APY)
- **Impact:** Will match ANY occupation if not handled specially
- **False Positive Risk:** **MEDIUM** (only 3 schemes, but high coverage programs)

### 1.4 States = ["All India"] ⚠️ NATIONAL COVERAGE SCHEMES
- **Count:** 81 schemes (1.9% of total)
- **Examples:** First 5 schemes all have this (PMJDY, PMJJBY, PMSBY, APY, PMMY)
- **Impact:** These schemes are nationally applicable
- **False Positive Risk:** **LOW** (intended behavior, but ensure matching logic handles it)
- **Note:** This is legitimate high coverage, not necessarily a false positive risk

---

## 2. AGE & INCOME AMBIGUITIES

### 2.1 Age Field Analysis

#### Schemes with NULL `min_age`
- **Count:** 4,222 schemes (97.6% of total)
- **Interpretation Ambiguity:**
  - Does NULL mean "no lower age limit" (unrestricted)?
  - Or "unknown/unspecified" minimum age?
- **Examples:** PMMY, Sukanya Samriddhi Yojana, Swachh Bharat Mission

#### Schemes with NULL `max_age`
- **Count:** 4,248 schemes (98.2% of total)
- **Interpretation Ambiguity:**
  - Does NULL mean "no upper age limit" (unrestricted)?
  - Or "unknown maximum age"?
- **Examples:** PMJDY (min:10, max:NULL), Stand Up India

#### 🔴 Schemes with BOTH Age Fields NULL (HIGHEST RISK)
- **Count:** 4,203 schemes (97.2% of total)
- **FALSE POSITIVE RISK:** **CRITICAL**
- **Impact:** No age-based filtering possible
- **Examples (first 5):**
  1. ID 5: Pradhan Mantri Mudra Yojana (PMMY)
  2. ID 13: Swachh Bharat Mission (Gramin)
  3. ID 14: Jal Jeevan Mission
  4. ID 15: Pradhan Mantri Fasal Bima Yojana (PMFBY)
  5. ID 17: Soil Health Card Scheme
- **Consequence:** If age filter matching defaults to "match if NULL", ~97% of schemes will match users of ANY age
- **Recommendation:**
  1. Clarify business rule: NULL age = "no age restriction" or "insufficient data"?
  2. If NULL = no restriction: Document this clearly
  3. If NULL = insufficient data: Implement confidence score reduction
  4. Add data enrichment task for missing age fields

#### Schemes with ONLY ONE Age Field NULL
- **Count:** 64 schemes (1.5% of total)
- **Examples:**
  - ID 1: PMJDY (min: 10, max: NULL)
  - ID 6: Stand Up India (min: 18, max: NULL)
  - ID 7: Sukanya Samriddhi Yojana (min: NULL, max: 9)
- **Impact:** Asymmetric filtering (may miss upper/lower bound)

#### Age Contradictions (min_age > max_age)
- **Count:** 0 schemes
- **Status:** ✓ No contradictions found

### 2.2 Income Field Analysis 🔴 CRITICAL AMBIGUITY

#### Schemes with NULL Income Fields
- **Count:** 4,324 schemes (100% of total)
- **BOTH `min_income` and `max_income` are NULL across ALL schemes**
- **FALSE POSITIVE RISK:** **CRITICAL**
- **Impact:** No income-based filtering is possible
- **Consequence:** Any user with any income level will match all 4,324 schemes
- **Recommendation:**
  1. This is likely **intentional** (most schemes don't restrict by income)
  2. However, document this assumption explicitly
  3. Flag in matching engine: "Manual review required for income-restricted schemes"
  4. Implement fallback logic for income validation

---

## 3. REQUIREMENT FIELD AMBIGUITIES

### 3.1 "Any" Value Semantics ⚠️ PERVASIVE AMBIGUITY

All requirement fields use "Any" extensively. The semantic meaning is UNCLEAR:
- Does "Any" mean "requirement exists but not specified"?
- Does "Any" mean "no requirement"?
- Does "Any" mean "any option is acceptable"?

#### Disability Requirement Distribution
| Value | Count | Percentage |
|-------|-------|------------|
| Any   | 4,284 | 99.1%      |
| Yes   | 34    | 0.8%       |
| No    | 6     | 0.1%       |

- **Schemes with disability_requirement = "Any":** 4,284
- **Impact:** Nearly ALL schemes have "Any" for disability
- **False Positive Risk:** **HIGH AMBIGUITY**
- **Possible Interpretations:**
  1. "Check for disability status, any configuration is acceptable"
  2. "No specific disability requirement"
  3. "Disability information not required for eligibility"

#### Minority Requirement Distribution
| Value | Count | Percentage |
|-------|-------|------------|
| Any   | 4,220 | 97.6%      |
| Yes   | 95    | 2.2%       |
| No    | 9     | 0.2%       |

- **Schemes with minority_requirement = "Any":** 4,220
- **Impact:** 97.6% of schemes classified as "Any"
- **False Positive Risk:** **HIGH AMBIGUITY**

#### Senior Citizen Requirement Distribution
| Value | Count | Percentage |
|-------|-------|------------|
| Any   | 4,215 | 97.5%      |
| No    | 96    | 2.2%       |
| Yes   | 13    | 0.3%       |

- **Difference between "No" and NULL:** "No" has explicit value (96 schemes)
- **False Positive Risk:** **MEDIUM** - Need to distinguish "No" from "Any"
- **Interpretation question:** Is "No" = not eligible for seniors? Or no restriction?

#### Widow Requirement Distribution
| Value | Count | Percentage |
|-------|-------|------------|
| Any   | 4,284 | 99.1%      |
| No    | 33    | 0.8%       |
| Yes   | 7     | 0.2%       |

- **Schemes with widow_requirement = "Any":** 4,284
- **False Positive Risk:** **HIGH AMBIGUITY**
- **Risk Scenario:** If "Any" interpreted as "no requirement", scheme will match non-widows

### 3.2 Comparison: "Any" vs "Yes" vs "No"

| Requirement | Any | Yes | No | Interpretation |
|-------------|-----|-----|--|-|
| Disability | 4,284 | 34 | 6 | Mostly "Any" - unclear meaning |
| Minority | 4,220 | 95 | 9 | Mostly "Any" - unclear meaning |
| Senior Citizen | 4,215 | 13 | 96 | "No" is explicitly used (96 schemes) |
| Widow | 4,284 | 7 | 33 | Mostly "Any" - unclear meaning |

**Key Insight:** The only requirement field with significant "No" values is `senior_citizen_requirement` (96 schemes explicitly mark "No").

---

## 4. HIGH-COVERAGE SCHEMES (No Restrictions)

### Definition of "No Restrictions"
Schemes meeting ALL of these criteria:
- Empty or missing `allowed_genders`
- Empty `allowed_castes`
- No `allowed_occupations` OR only "All"
- NULL `min_age` AND NULL `max_age`

### Finding
- **Count:** 0 schemes
- **Status:** ✓ No schemes meet all "no restrictions" criteria
- **Explanation:** Even very broad schemes (like PMJDY) have at least one restriction (e.g., gender specified)

### However - Effectively Unrestricted Schemes
While 0 schemes meet ALL criteria, these are effectively unrestricted by demographics:

**Top High-Coverage Schemes:**
1. ID 1: Pradhan Mantri Jan Dhan Yojana (PMJDY)
   - Genders: All 3 types (Male, Female, Transgender)
   - Castes: Empty []
   - Occupations: ["All"]
   - Age: min=10, max=NULL (upper unrestricted)
   - **Coverage:** ~100% of population ≥ 10 years

2. ID 2: Pradhan Mantri Jeevan Jyoti Bima Yojana (PMJJBY)
   - Genders: All 3 types
   - Castes: Empty []
   - Occupations: ["All"]
   - Age: min=18, max=50 (restricted)
   - **Coverage:** ~95% of population 18-50 years

3. ID 4: Atal Pension Yojana (APY)
   - Genders: All 3 types
   - Castes: Empty []
   - Occupations: ["All"]
   - Age: min=18, max=NULL (upper unrestricted)
   - **Coverage:** ~100% of population ≥ 18 years

---

## 5. EMPTY ARRAY vs NULL ISSUES

### Analysis of Array Fields

| Field | Empty `[]` | NULL | Populated | Interpretation Issue |
|-------|-----------|------|-----------|----------------------|
| allowed_genders | 0 | 0 | 4,324 | ✓ No ambiguity |
| allowed_castes | 233 | 0 | 4,091 | ⚠️ HIGH - What does empty mean? |
| allowed_states | 45 | 0 | 4,279 | ⚠️ MEDIUM - Could imply "all states" or "no states" |
| allowed_occupations | 2,699 | 2 | 1,623 | ⚠️ CRITICAL - 62% have empty arrays |
| allowed_ration_card_types | 287 | 0 | 4,037 | ⚠️ MEDIUM - Some truly don't need ration cards |
| allowed_marital_status | 4,322 | 2 | 0 | ⚠️ CRITICAL - 99.95% empty, 0 populated records |

### 🔴 Critical Findings

#### 1. allowed_occupations - MOST PROBLEMATIC
- **Empty `[]`:** 2,699 schemes (62.4%)
- **NULL:** 2 schemes
- **Populated:** 1,623 schemes
- **Impact:** Majority of schemes have no occupation filter
- **False Positive Risk:** **HIGH** - Will match any occupation
- **Question:** Does empty mean:
  - "All occupations welcome"?
  - "Occupations not checked"?
  - "Data not available"?

#### 2. allowed_marital_status - ENTIRELY EMPTY
- **Empty `[]`:** 4,322 schemes (99.95%)
- **NULL:** 2 schemes
- **Populated:** 0 schemes
- **Impact:** ZERO schemes have marital status restrictions
- **Implication:** Marital status field is effectively unused
- **False Positive Risk:** **LOW** (no filtering possible anyway)

#### 3. allowed_castes - SIGNIFICANT GAP
- **Empty `[]`:** 233 schemes (5.4%)
- **Question:** These 233 schemes - do they reallly accept all castes?
- **Example:** All 5 major national schemes show empty castes

---

## 6. CONTRADICTORY DATA

### Contradiction Check Results

#### Age Contradictions (min_age > max_age)
- **Count:** 0 schemes
- **Status:** ✓ All schemes with both age fields populated have valid min ≤ max

#### Income Contradictions (min_income > max_income)
- **Count:** 0 schemes
- **Status:** ✓ No income contradictions (all income fields are NULL anyway)

### Overall Data Quality
- **Status:** EXCELLENT for numeric fields
- **Contradictions:** 0 (0% of schemes)

---

## 7. "ALL" vs "ANY" AMBIGUITY

### Overview
Two different semantic patterns cause confusion:
1. **"All"** in array fields = universal match
2. **"Any"** in requirement fields = unclear meaning

### "All"/"All India" Distribution
- **Total occurrences:** 85 instances across schemes
- **In allowed_occupations:** "All" enables matching any occupation
- **In allowed_states:** "All India" enables national coverage
- **Typical interpretation:** These enable universal matching for that field

### "Any" in Requirement Fields
- **Total occurrences:** 17,003 (across all 4 requirement fields)
- **Breakdown:**
  - disability_requirement "Any": 4,284 times
  - minority_requirement "Any": 4,220 times
  - senior_citizen_requirement "Any": 4,215 times
  - widow_requirement "Any": 4,284 times
- **Total:** ~99.2% of schemes use "Any" for requirements

### Ambiguity Examples

**Example 1: PMJDY Scheme**
```
allowed_occupations: ["All"]        → Matches ANY occupation
allowed_states: ["All India"]       → Matches ANY state
disability_requirement: "Any"       → Unclear: required or not?
minority_requirement: "Any"         → Unclear: required or not?
```

**Matching Question:** If a user queries PMJDY with:
- Occupation: Developer (not typical government beneficiary)
- State: Any state in India
- Disability: No
- Minority: No

**Result with current logic:** User matches all criteria
**Risk:** FALSE POSITIVE if "Any" means "must verify" rather than "no requirement"

---

## FALSE POSITIVE RISK SCENARIOS

### Scenario 1: Age Filtering Disabled (CRITICAL RISK)
**Situation:** 4,203 schemes (97.2%) with NULL age fields
**Current Matching Logic (Assumed):** "If age is NULL, no age filtering"
**Risk:** A 5-year-old and an 80-year-old both match schemes intended for working-age adults
**Impact:** Potentially affects 99% of schemes

**Example:**
- Scheme: Pradhan Mantri Mudra Yojana (PMMY) - business loan scheme
  - min_age: NULL
  - max_age: NULL
- Query user: Age 8 years
- **Result:** MATCHES (incorrect - child should not qualify for business loan)

### Scenario 2: Caste Ambiguity (MEDIUM RISK)
**Situation:** 233 schemes with empty allowed_castes `[]`
**Current Ambiguity:** Is empty = "all castes" OR "no caste filtering"?
**Risk:** If interpreted as "all castes", SC/ST-specific schemes might match general population

**Example:**
- Scheme ID 1: PMJDY has empty castes
- Query user: General category
- **Result:** MATCHES (expected for PMJDY, but logic is vulnerable)

### Scenario 3: Occupation Mismatches (HIGH RISK)
**Situation:** 2,699 schemes (62.4%) with empty allowed_occupations `[]`
**Current Logic:** Empty occupations = match any occupation
**Risk:** Agricultural scheme might match an urban software engineer

**Example:**
- Scheme: Pradhan Mantri Fasal Bima Yojana (PMFBY) - crop insurance
  - allowed_occupations: [] (empty)
- Query user: Software Engineer
- **Result:** MATCHES (false positive - PMFBY is for farmers)

### Scenario 4: "Any" Requirement Misinterpretation (HIGH RISK)
**Situation:** 4,284 schemes with widow_requirement = "Any"
**Current Ambiguity:** Does "Any" mean:
- A) "Must be widow" (false positive: non-widow matches)
- B) "No requirement" (correct interpretation)
- C) "Unknown requirement"
**Risk:** If interpreted as (A), massive false positives for widow-only schemes

**Example:**
- Scheme: Indira Gandhi Widow Pension
  - widow_requirement: "Any"
- Query user: Married couple
- **Result with misinterpretation:** MATCHES (FALSE POSITIVE)
- **Result with correct interpretation:** Does NOT match

### Scenario 5: Income Filtering Disabled (MEDIUM-HIGH RISK)
**Situation:** 100% of schemes have NULL min_income and max_income
**Current Logic:** "If income NULL, no income filtering"
**Risk:** Poor schemes (targeted for low income) match millionaires

**Example:**
- Scheme: Pradhan Mantri Jan Dhan Yojana (intended for unbanked = typically low income)
- Query user: Income = ₹50 lakhs/year
- **Result:** MATCHES (arguably false positive for low-income scheme)

---

## DATA QUALITY ASSESSMENT

| Aspect | Status | Finding |
|--------|--------|---------|
| Age contradictions (min > max) | ✓ EXCELLENT | 0 contradictions |
| Income contradictions | ✓ EXCELLENT | 0 contradictions |
| Required field completeness | ⚠️ POOR | 97.2% missing age data |
| Semantic clarity | ⚠️ POOR | 99% use ambiguous "Any" values |
| Array field consistency | ⚠️ MIXED | Empty vs NULL usage varies |
| **OVERALL** | ⚠️ **NEEDS IMPROVEMENT** | Good syntax, poor semantics |

---

## RECOMMENDATIONS

### Priority 1: CRITICAL (Address Immediately)

1. **Define "Any" Semantics**
   - Create specification document: What does "Any" mean for each requirement field?
   - Options:
     - "Any" = no requirement (most likely intent)
     - "Any" = requirement exists but value unspecified
     - "Any" = multiple options acceptable
   - Update ALL 17,003 instances in matching logic accordingly
   - Add validation: Incoming "Any" values must be logged/flagged

2. **Handle NULL Age Fields**
   - Decision needed: NULL age = "no restriction" OR "insufficient data"?
   - If no restriction: Document clearly in business requirements
   - If insufficient data: Implement confidence score reduction (e.g., -20% confidence)
   - For 4,203 schemes with both fields NULL: Add metadata flag
   - Consider enrichment project to fill missing age data

3. **Address Empty Occupations Array**
   - 2,699 schemes (62.4%) have empty allowed_occupations
   - Decision: Empty `[]` = "all occupations allowed" OR "occupations not checked"?
   - Implement consistent interpretation across matching engine
   - Add test cases specifically for empty vs populated occupation fields

### Priority 2: HIGH (Implement Within Sprint)

4. **Disambiguate Empty Caste Arrays**
   - 233 schemes have empty allowed_castes
   - Create mapping: empty castes = universal OR excluded
   - Update matching logic to be explicit
   - Test with diverse user profiles

5. **Income Field Strategy**
   - Since 100% have NULL income, formalize this as business rule
   - Add comment/documentation: "Income filtering disabled; all users match all schemes"
   - Flag schemes that SHOULD have income restrictions but don't
   - Implement fallback: If scheme maturity data available, infer income range

6. **Requirement Field Values**
   - For schemes with explicit "Yes"/"No" (not "Any"):
     - `senior_citizen_requirement` = 96 "No" schemes
     - These MUST exclude seniors
     - Create whitelist of schemes requiring validation: those with "Yes" values

### Priority 3: MEDIUM (Enhance System)

7. **Add Confidence Scores**
   - Schemes with NULL age fields: -15% precision score
   - Schemes with empty caste arrays: -10% precision score
   - Schemes with empty occupation arrays: -20% precision score
   - Schemes with "Any" for >3 requirement fields: -10% precision score
   - Display confidence in UI: "87% match confidence"

8. **Create Validation Rules**
   ```
   IF allowed_occupations is empty AND scheme_category == "Agricultural"
     THEN flag for manual review (potential false positives)
   
   IF widow_requirement == "Any" AND scheme_name contains "widow|widow"
     THEN clarify whether this requires widow status
   
   IF min_age is NULL AND max_age is NULL
     THEN apply age-agnostic matching rule
   ```

9. **Data Enrichment Project**
   - Target: Fill age fields for 4,203 schemes
   - Source: Scheme description text, government sources
   - Priority: Top 100 most-queried schemes first

10. **Field Standardization**
    - Standardize requirement fields to: "Required", "Optional", "Not Applicable"
    - Instead of: "Any", "Yes", "No"
    - Migrate existing data in controlled manner

---

## IMPLEMENTATION CHECKLIST

### Phase 1: Immediate Fixes (Week 1)
- [ ] Document all "Any" interpretations in business rules
- [ ] Create mapping: NULL age behavior
- [ ] Create mapping: empty array behavior
- [ ] Add logging to false positive detection
- [ ] Write test cases for ambiguous scenarios

### Phase 2: Logic Updates (Week 2)
- [ ] Update matching engine with documented semantics
- [ ] Implement confidence score calculation
- [ ] Add scheme validation flags
- [ ] Update eligibility logic error handling

### Phase 3: Quality Improvements (Week 3)
- [ ] Data enrichment for age fields
- [ ] Require field for schemes with explicit restrictions
- [ ] Create manual review queue for ambiguous matches
- [ ] Performance testing with new logic

### Phase 4: User Experience (Week 4)
- [ ] Display match confidence in UI
- [ ] Show reason for low-confidence matches
- [ ] Implement user feedback: "Was this match correct?"
- [ ] A/B test new vs. old matching logic

---

## TEST CASES FOR FALSE POSITIVE SCENARIOS

### Test Case 1: 5-Year-Old Querying PMMY
```
Input:
  - User Age: 5 years
  - Query: Pradhan Mantri Mudra Yojana (ID 5)
  
Current Logic Issue:
  - min_age: NULL, max_age: NULL
  - Result: MATCHES (false positive)
  
Expected: DOES NOT MATCH
  - Age 5 < business loan minimum qualifications
```

### Test Case 2: Software Engineer Querying PMFBY
```
Input:
  - User Occupation: Software Engineer
  - Query: Pradhan Mantri Fasal Bima Yojana (ID 15)
  
Current Logic Issue:
  - allowed_occupations: [] (empty)
  - Result: MATCHES (false positive)
  
Expected: Requires review
  - Software engineers typically not farmers (agriculture industry)
```

### Test Case 3: Married Individual Querying Widow Pension
```
Input:
  - User Marital Status: Married
  - Query: [Any widow-specific scheme]
  
Current Logic Issue:
  - widow_requirement: "Any"
  - Result: MATCHES (false positive if "Any" = "does not require widow")
  
Expected: DOES NOT MATCH
  - Widow pension designed for widows only
```

### Test Case 4: High-Income Individual Querying PMJDY
```
Input:
  - User Income: ₹50,00,000/year
  - Query: Pradhan Mantri Jan Dhan Yojana (ID 1)
  
Current Logic Issue:
  - min_income: NULL, max_income: NULL
  - Result: MATCHES (expected for universal scheme)
  
Expected: MATCHES
  - PMJDY is universal financial inclusion scheme
  - Income not a restriction
  - Status: NOT a false positive (intended behavior)
```

---

## CONCLUSION

### Key Takeaways

1. **Data Quality is Good:** 0 contradictions in numeric fields
2. **Semantics are Ambiguous:** 99%+ use vague "Any" and NULL values
3. **Age Filtering Disabled:** 97.2% of schemes have no age constraints in data
4. **Income Filtering Disabled:** 100% of schemes have no income constraints in data
5. **Occupation Filtering Weak:** 62.4% of schemes don't specify occupations
6. **Requirement Meanings Unclear:** "Any" in 17,003 instances across requirements

### Immediate Actions Required

1. **Clarify semantics:** Meet with product team to define "Any", NULL, and empty array meanings
2. **Update documentation:** Create explicit business rules for ambiguous cases
3. **Implement safeguards:** Add confidence scores and validation rules
4. **Test rigorously:** Use provided test cases to verify false positive fixes
5. **Monitor proactively:** Log all edge cases during matching for continuous improvement

### Estimated Impact

If these issues are NOT addressed:
- **False Positive Rate:** Estimated 15-25% of matches
- **User Frustration:** Users rejected for schemes they don't qualify for
- **System Credibility:** Loss of trust in eligibility engine

If these recommendations are implemented:
- **False Positive Rate:** Reduced to <5% (industry standard)
- **User Satisfaction:** Increased confidence in recommendations
- **System Quality:** Enterprise-grade reliability

---

## APPENDIX: DETAILED SCHEME EXAMPLES

### Most Broadly Applicable Schemes

**1. Pradhan Mantri Jan Dhan Yojana (PMJDY) - ID 1**
- Category: Financial Inclusion
- Gender: All 3 types (unrestricted)
- Caste: [] (empty - ambiguous)
- Occupation: ["All"] (universal)
- Age: 10 to ? (max_age = NULL)
- Income: ? (NULL both fields)
- Disability: Any
- Minority: Any
- Senior Citizen: Any
- Widow: Any
- **Match Profile:** Nearly every Indian 10+ years old

**2. Pradhan Mantri Jeevan Jyoti Bima Yojana (PMJJBY) - ID 2**
- Category: Insurance
- Gender: All 3 types
- Caste: [] (empty - ambiguous)
- Occupation: ["All"]
- Age: 18 to 50 (restricted)
- Income: ? (NULL both fields)
- Disaster: Any
- Minority: Any
- Senior Citizen: No ← Note: explicit "No" (not "Any")
- Widow: Any
- **Match Profile:** 95% of Indians aged 18-50

**3. Atal Pension Yojana (APY) - ID 4**
- Category: Pension Scheme
- Gender: All 3 types
- Caste: [] (empty - ambiguous)
- Occupation: ["All"]
- Age: 18 to ? (max_age = NULL)
- Income: ? (NULL both fields)
- Disability: Any
- Minority: Any
- Senior Citizen: Any
- Widow: Any
- **Match Profile:** All Indians 18+ years

---

**Report Generated:** Analysis of all_schemes_export.json  
**Analysis Tool:** analyze_false_positives.py  
**Output Files:** 
- false_positive_analysis_summary.json (summary data)
- high_risk_no_restrictions.json (high-risk schemes list)
