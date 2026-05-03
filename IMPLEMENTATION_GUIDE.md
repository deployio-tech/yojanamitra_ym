# YOJANAMITRA ELIGIBILITY ENGINE - IMPLEMENTATION GUIDE

**Version:** 2.1 (Production Ready)  
**Date:** March 17, 2026  
**Status:** Ready for Deployment

---

## QUICK START

### Files to Deploy:

1. **eligibility_engine_strict_v21.py** - Core matching engine (7-layer gates)
2. **test_eligibility_engine.py** - Comprehensive test suite (20 profiles)
3. **validate_schemes_data.py** - Data validation & cleaning (from template below)
4. **COMPREHENSIVE_ELIGIBILITY_SOLUTION.md** - Complete design documentation
5. **FALSE_POSITIVES_ANALYSIS_REPORT.md** - Detailed analysis of issues

### Integration Steps:

```bash
# Step 1: Validate current data
python validate_schemes_data.py --input all_schemes_export.json --output schemes_validated.json

# Step 2: Run test suite
python test_eligibility_engine.py

# Step 3: Test against real schemes
python integration_test.py --schemes schemes_validated.json

# Step 4: Deploy to production
# Update app.py to import new engine
```

---

## DATA CLEANING & VALIDATION

### Template for validate_schemes_data.py

create this file at: `c:\ymf\yojana-mitra-backend\validate_schemes_data.py`

```python
\"\"\"
Data Validation & Cleaning for Schemes Dataset
Applies semantic normalization to prevent false positives
\"\"\"

import json
import logging
from typing import Dict, List, Tuple
from eligibility_engine_strict_v21 import (
    normalize_requirement_value, RequirementValue
)

logger = logging.getLogger(__name__)


class SchemeValidator:
    \"\"\"Validate and clean schemes data.\"\"\"
    
    VALID_STATES = {
        "AN", "AP", "AR", "AS", "BR", "CG", "CH", "CT", "DL", "DN", "GA", "GJ",
        "HR", "HP", "JK", "JH", "KA", "KL", "LD", "MP", "MH", "MN", "ML", "MZ",
        "NL", "OD", "PB", "PY", "RJ", "SK", "TG", "TR", "TN", "UP", "UK", "WB",
    }
    
    VALID_GENDERS = {"Male", "Female", "Transgender", "All"}
    
    REQUIREMENT_VALUES = {"Any", "Yes", "No"}
    
    def __init__(self):
        self.issues = {
            "errors": [],
            "warnings": [],
            "fixes_applied": [],
            "statistics": {},
        }
    
    def validate_scheme(self, scheme: Dict, scheme_index: int) -> Tuple[bool, Dict]:
        \"\"\"Validate single scheme, apply fixes.\"\"\"
        
        # Check required fields
        if not scheme.get("id"):
            self.issues["errors"].append(f"Scheme {scheme_index}: Missing ID")
            return False, scheme
        
        scheme_id = scheme["id"]
        
        # Fix & validate states
        if scheme.get("allowed_states"):
            # If specifically "All India", keep it
            if scheme["allowed_states"] != ["All India"]:
                # Validate each state
                invalid = [s for s in scheme["allowed_states"] if s not in self.VALID_STATES]
                if invalid:
                    self.issues["warnings"].append(
                        f"Scheme {scheme_id}: Invalid states {invalid} - treating as 'All India'"
                    )
                    scheme["allowed_states"] = ["All India"]
        
        # Fix & validate genders
        if scheme.get("allowed_genders"):
            invalid = [g for g in scheme["allowed_genders"] if g not in self.VALID_GENDERS]
            if invalid:
                self.issues["warnings"].append(
                    f"Scheme {scheme_id}: Invalid genders {invalid} - treating as 'All'"
                )
                scheme["allowed_genders"] = ["All"]
        
        # Normalize requirement fields to semantic values
        req_fields = [
            "disability_requirement", "minority_requirement",
            "senior_citizen_requirement", "widow_requirement"
        ]
        
        for field in req_fields:
            if field in scheme:
                original = scheme[field]
                normalized = normalize_requirement_value(original)
                if original != normalized.value:
                    scheme[field] = normalized.value
                    self.issues["fixes_applied"].append(
                        f"Scheme {scheme_id}: {field} '{original}' → '{normalized.value}'"
                    )
        
        # Age validation
        if scheme.get("min_age") and scheme.get("max_age"):
            if scheme["min_age"] > scheme["max_age"]:
                self.issues["errors"].append(
                    f"Scheme {scheme_id}: min_age ({scheme['min_age']}) > max_age ({scheme['max_age']})"
                )
                return False, scheme
        
        # Income validation
        if scheme.get("min_income") and scheme.get("max_income"):
            if scheme["min_income"] > scheme["max_income"]:
                self.issues["errors"].append(
                    f"Scheme {scheme_id}: min_income > max_income"
                )
                return False, scheme
        
        return True, scheme
    
    def validate_all_schemes(self, schemes: List[Dict]) -> List[Dict]:
        \"\"\"Validate and clean entire dataset.\"\"\"
        
        valid_schemes = []
        invalid_count = 0
        
        for idx, scheme in enumerate(schemes):
            valid, cleaned_scheme = self.validate_scheme(scheme, idx)
            if valid:
                valid_schemes.append(cleaned_scheme)
            else:
                invalid_count += 1
        
        # Statistics
        self.issues["statistics"] = {
            "total_input": len(schemes),
            "total_valid": len(valid_schemes),
            "total_invalid": invalid_count,
            "error_count": len(self.issues["errors"]),
            "warning_count": len(self.issues["warnings"]),
            "fixes_applied_count": len(self.issues["fixes_applied"]),
        }
        
        return valid_schemes
    
    def save_report(self, filename: str):
        \"\"\"Save validation report.\"\"\"
        report = {
            "timestamp": str(__import__("datetime").datetime.now()),
            "issues": self.issues,
        }
        with open(filename, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Validation report saved to {filename}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate and clean schemes dataset")
    parser.add_argument("--input", required=True, help="Input JSON file")
    parser.add_argument("--output", required=True, help="Output JSON file")
    parser.add_argument("--report", default="validation_report.json", help="Report file")
    
    args = parser.parse_args()
    
    # Load schemes
    with open(args.input) as f:
        schemes = json.load(f)
    
    # Validate
    validator = SchemeValidator()
    valid_schemes = validator.validate_all_schemes(schemes)
    
    # Save cleaned data
    with open(args.output, "w") as f:
        json.dump(valid_schemes, f, indent=2)
    
    # Save report
    validator.save_report(args.report)
    
    # Print summary
    stats = validator.issues["statistics"]
    print(f"\\nValidation Complete:")
    print(f"  Input schemes: {stats['total_input']}")
    print(f"  Valid schemes: {stats['total_valid']}")
    print(f"  Invalid schemes: {stats['total_invalid']}")
    print(f"  Errors: {stats['error_count']}")
    print(f"  Warnings: {stats['warning_count']}")
    print(f"  Fixes applied: {stats['fixes_applied_count']}")


if __name__ == "__main__":
    main()
```

---

## INTEGRATION WITH EXISTING APP

### Step 1: Update app.py imports

```python
# Old import
from yojanamitra_eligibility_engine_v2 import ProfileNormalizer, EligibilityEngine

# New import
from eligibility_engine_strict_v21 import (
    StrictEligibilityEngine, UserProfile, SchemeEligibilityRule,
    build_scheme_rule_from_json
)
```

### Step 2: Add endpoint handler

```python
@app.route('/api/eligibility-check-strict', methods=['POST'])
def check_eligibility_strict():
    \"\"\"
    Check eligibility using strict engine (zero false positives).
    Requires complete user profile.
    \"\"\"
    data = request.json
    
    try:
        # Build user profile
        user = UserProfile(
            user_id=data.get("user_id"),
            age=data.get("age"),
            gender=data.get("gender"),
            state=data.get("state"),
            income_annual=data.get("income_annual"),
            occupation=data.get("occupation", []),
            caste_category=data.get("caste_category", "general"),
            is_widow=data.get("is_widow", False),
            is_disabled=data.get("is_disabled", False),
            disability_percentage=data.get("disability_percentage", 0),
            is_senior_citizen=data.get("is_senior_citizen", False),
            is_minority=data.get("is_minority", False),
        )
        
        # Load schemes
        with open('all_schemes_export.json') as f:
            schemes_json = json.load(f)
        
        # Convert to rules
        rules = [build_scheme_rule_from_json(s) for s in schemes_json]
        
        # Evaluate
        engine = StrictEligibilityEngine()
        results = engine.evaluate_batch(user, rules)
        
        # Filter eligible schemes
        eligible = [
            r for r in results.values()
            if r.eligibility_class.value == "FULLY_ELIGIBLE"
        ]
        
        return jsonify({
            "user_id": user.user_id,
            "total_evaluated": len(results),
            "eligible_count": len(eligible),
            "eligible_schemes": [
                {
                    "id": r.scheme_id,
                    "name": r.scheme_name,
                    "confidence": r.confidence_score,
                }
                for r in eligible[:20]  # Top 20
            ],
            "evaluation_timestamp": datetime.now().isoformat(),
        })
    
    except Exception as e:
        logger.error(f"Eligibility check error: {e}")
        return jsonify({"error": str(e)}), 400
```

---

## MONITORING & VALIDATION

### Add Monitoring Metrics

```python
class EngineMetrics:
    \"\"\"Track engine performance and false positive rate.\"\"\"
    
    def __init__(self):
        self.evaluations = []
        self.false_positives = []
    
    def log_evaluation(self, result):
        self.evaluations.append({
            "scheme_id": result.scheme_id,
            "eligible": result.eligibility_class == "FULLY_ELIGIBLE",
            "confidence": result.confidence_score,
            "gate_reached": result.gate_reached,
            "rejection_code": result.rejection_code,
        })
    
    def log_false_positive(self, scheme_id, user_id, reason):
        \"\"\"Log detected false positive for post-analysis.\"\"\"
        self.false_positives.append({
            "scheme_id": scheme_id,
            "user_id": user_id,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        })
    
    def get_false_positive_rate(self):
        if not self.evaluations:
            return 0.0
        
        eligible = sum(1 for e in self.evaluations if e["eligible"])
        fp_count = len(self.false_positives)
        
        return fp_count / eligible if eligible > 0 else 0.0
```

---

## PERFORMANCE TARGETS

| Metric | Target | Acceptable | Warning |
|--------|--------|-----------|---------|
| Evaluation/scheme | <1ms | <5ms | >5ms |
| Batch (4324 schemes) | <5s | <10s | >10s |
| Profile validation | <100µs | <1ms | >1ms |
| False positive rate | <1% | <2% | >2% |
| Confidence score accuracy | 95% | 90% | <90% |

---

## TROUBLESHOOTING

### False Positive Detected

**If a false positive is found:**

1. **Document it:**
   ```python
   {
       "scheme_id": 123,
       "user_profile": {...},
       "expected": "NOT_ELIGIBLE",
       "actual": "FULLY_ELIGIBLE",
       "reason": "Age 8 matched youth scheme",
       "gate_failed": 0,  # No gate rejected
   }
   ```

2. **Analyze the pattern:**
   - Is it an age issue? → Check Gate 4
   - Is it a requirement issue? → Check Gate 3
   - Is it an occupation issue? → Check Gate 5

3. **Design a fix:**
   - Add validation rule
   - Or correct scheme data
   - Or adjust engine logic

4. **Implement generalized fix** (not case-specific)

5. **Re-test** across all 20 test profiles

---

## ROLLBACK PLAN

If issues are detected after deployment:

```bash
# Instant rollback (< 1 minute)
git revert HEAD
# Or
mv app_new.py app.py.bak
mv app.py.old app.py

# Clear cache
redis-cli FLUSHALL

# Monitor for issues
tail -f logs/yojanamitra.log
```

---

## SUCCESS CRITERIA

✓ **Zero false positives** across test suite  
✓ **100% precision** on known negative cases  
✓ **<5 second** evaluation for 4,324 schemes  
✓ All 6 gates function correctly  
✓ Clear audit trail for compliance  
✓ No data corruption during integration  

---

## MAINTENANCE

### Weekly Tasks
- Monitor false positive rate
- Review edge cases
- Check performance metrics

### Monthly Tasks
- Analyze new false positives
- Update scheme data based on corrections
- Refresh test profiles (add new scenarios)

### Quarterly Tasks
- Full regression testing
- Performance optimization
- Security review

---

## SUPPORT & ESCALATION

**Issues found:**
1. Email: data-quality@yojanamitra.org
2. Escalate to: Product + Engineering leads
3. Create hotfix within 2 hours for critical false positives
4. Root cause analysis within 24 hours

---

**Document Version:** 1.0  
**Last Updated:** March 17, 2026  
**Next Review:** April 17, 2026
