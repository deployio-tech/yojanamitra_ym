# YOJANAMITRA ELIGIBILITY ENGINE - DEPLOYMENT CHECKLIST

**Version:** 2.1  
**Date:** March 17, 2026  
**Status:** Ready for Production  

---

## ✅ PRE-DEPLOYMENT VALIDATION CHECKLIST

### Documentation Review
- [ ] Read DELIVERABLES_SUMMARY.md (5 min)
- [ ] Review EXECUTIVE_REPORT.md (20 min)
- [ ] Technical team reviews COMPREHENSIVE_ELIGIBILITY_SOLUTION.md (40 min)
- [ ] All stakeholders understand 7-layer gate system

### Code Quality
- [ ] eligibility_engine_strict_v21.py reviewed (peer review)
- [ ] test_eligibility_engine.py reviewed
- [ ] No syntax errors
- [ ] All imports available (Python 3.8+)
- [ ] Type hints correct
- [ ] Docstrings complete

### Data Preparation
- [ ] all_schemes_export.json available and readable
- [ ] Data backup created
- [ ] validate_schemes_data.py script created from template
- [ ] Validation script executed: `python validate_schemes_data.py --input all_schemes_export.json --output schemes_validated.json`
- [ ] Validation report reviewed: validation_report.json
- [ ] No critical errors in validation report
- [ ] Schemes_validated.json generated successfully

### Testing
- [ ] Test suite executes without errors
- [ ] All 20 test profiles validate (profile_completeness >60%)
- [ ] False positive scenarios identified and documented
- [ ] No unexpected exceptions in test run
- [ ] Test report generated: test_suite_report.txt

### Performance Testing
- [ ] Baseline performance measured (single profile)
- [ ] Batch performance tested (all 4,324 schemes)
- [ ] Single scheme evaluation: <1ms
- [ ] Full batch evaluation: <5 seconds
- [ ] Memory usage within limits
- [ ] No memory leaks detected

### Integration Testing
- [ ] app.py can import eligibility_engine_strict_v21
- [ ] build_scheme_rule_from_json() works on sample schemes
- [ ] Batch evaluation endpoint tested
- [ ] Response format verified
- [ ] No import errors

### Security Review
- [ ] No hardcoded secrets
- [ ] No SQL injection vulnerabilities (N/A - no SQL)
- [ ] No malicious code paths
- [ ] Input validation in place
- [ ] Error messages don't leak sensitive data

### Compliance Review
- [ ] Audit trail complete (rejection reasons logged)
- [ ] Decisions reproducible (deterministic)
- [ ] No discrimination in logic (all protected categories handled equally)
- [ ] GDPR considerations addressed (no personal data leakage)
- [ ] Accessibility considerations (results logged in plain text)

### Monitoring Preparation
- [ ] Error logging configured
- [ ] Metrics collection setup
- [ ] False positive detection logic ready
- [ ] Alert thresholds defined (>2% FP rate = alert)
- [ ] Dashboard template created

### Documentation for Ops
- [ ] Runbook created for common issues
- [ ] Escalation procedures documented
- [ ] Performance baselines recorded
- [ ] Alert definitions documented
- [ ] Rollback procedure tested

---

## 🚀 DEPLOYMENT PROCEDURE

### Phase 1: Staging Deployment (Low Risk)

1. **Preparation**
   - [ ] Checkout code from repository
   - [ ] Deploy eligibility_engine_strict_v21.py to staging/python/
   - [ ] Deploy test_eligibility_engine.py to staging/tests/
   - [ ] Upload schemes_validated.json to staging/data/

2. **Configuration**
   - [ ] Update app.py (staging version) with new imports
   - [ ] Add /api/eligibility-check-strict endpoint
   - [ ] Configure error logging
   - [ ] Setup metrics collection

3. **Validation in Staging**
   - [ ] Import everything without errors
   - [ ] Run smoke test (1 profile, 10 schemes)
   - [ ] Run full test suite (20 profiles, 4,324 schemes)
   - [ ] Check performance metrics
   - [ ] Verify audit logs are being generated

4. **Monitoring Setup**
   - [ ] Verify error logs flowing to central log system
   - [ ] Test alert system (intentional error trigger)
   - [ ] Confirm false positive detection working
   - [ ] Dashboard showing metrics

5. **Sign-Off**
   - [ ] Tech lead: Code quality ✓
   - [ ] QA lead: Testing complete ✓
   - [ ] DevOps lead: Deployment ready ✓
   - [ ] Product lead: Functionality correct ✓

### Phase 2: Production Deployment (Blue-Green)

1. **Pre-Deployment**
   - [ ] Create database backup (schemes data)
   - [ ] Create code backup (old app.py)
   - [ ] Notify on-call team
   - [ ] Prepare rollback procedure
   - [ ] Set deployment window (low traffic time)

2. **Green Deployment**
   - [ ] Deploy new code to production-green environment
   - [ ] Run smoke tests on green (1 profile, 10 schemes)
   - [ ] Run full test suite on green
   - [ ] Verify performance metrics

3. **Traffic Switch**
   - [ ] Route 10% traffic to production-green
   - [ ] Monitor for 30 minutes
   - [ ] Check error rates (<0.1%), false positive rate (<1%)
   - [ ] Check performance metrics (<5 sec/batch)

4. **Rollout**
   - [ ] If good: Route 50% traffic to green
   - [ ] Monitor for 1 hour
   - [ ] If good: Route 100% traffic to green
   - [ ] If issues: Rollback to blue immediately

5. **Post-Deployment**
   - [ ] Monitor error logs for first 24 hours
   - [ ] Daily review of false positive rate for 1 week
   - [ ] Weekly review for 1 month
   - [ ] Generate deployment success report

---

## 📊 SUCCESS CRITERIA

### Quantitative Metrics
- [ ] False positive rate: <1% (measure across 1,000+ queries)
- [ ] Response time: <5 seconds per full batch
- [ ] Single scheme evaluation: <1ms
- [ ] System uptime: >99.9%
- [ ] Error rate: <0.1%

### Qualitative Metrics
- [ ] No user complaints about eligibility errors (in 2-week period)
- [ ] All rejection reasons are clear and correct
- [ ] Audit trail is complete and compliant
- [ ] Zero instances of data corruption

### Compliance Metrics
- [ ] All decisions reproducible (deterministic)
- [ ] Audit trail accessible for legal review
- [ ] No discriminatory patterns detected
- [ ] False positive patterns documented for improvement

---

## 🛑 ROLLBACK TRIGGER CONDITIONS

Immediately rollback if ANY of these occur:

1. **False Positive Rate >2%** (>2 in 100 recommendations wrong)
2. **Response Time >10 seconds** (batch evaluation)
3. **Error Rate >0.5%** (>5 errors per 1,000 requests)
4. **Data Corruption** (validation failures on schemes)
5. **Security Issue** (injection, data leak, etc.)
6. **Critical Bug** (unhandled exception on 50%+ of profiles)

### Rollback Procedure

```bash
# Immediate (< 5 minutes)
1. Switch traffic back to production-blue (0% to green)
2. Verify traffic all flowing to blue
3. Check error rates dropping

# Investigation (next 1 hour)
4. Save logs/metrics from green deployment
5. Create incident report
6. Root cause analysis
7. Identify fix

# Resolution (next 2-4 hours)
8. Implement fix in code
9. Re-test in staging
10. Re-deploy with fix
11. Gradual traffic switch to green-v2
```

---

## 📈 POST-DEPLOYMENT MONITORING

### Daily (First Week)
- [ ] False positive rate <1%
- [ ] Response times <5 sec
- [ ] Error rate <0.1%
- [ ] No critical bugs

### Weekly (First Month)
- [ ] Analyze false positives found
- [ ] Check for patterns in rejections
- [ ] Performance optimization if needed
- [ ] Update test suite if new edge cases found

### Monthly (Ongoing)
- [ ] Comprehensive metrics report
- [ ] User feedback analysis
- [ ] Performance optimization opportunities
- [ ] Feature requests/improvements

---

## 🐛 ISSUE RESOLUTION WORKFLOW

### If False Positive Detected

1. **Document** (within 30 min)
   ```json
   {
       "scheme_id": 123,
       "scheme_name": "...",
       "user_profile": {...},
       "expected": "NOT_ELIGIBLE",
       "actual": "FULLY_ELIGIBLE",
       "reason": "...",
       "gate_reached": 0,
       "timestamp": "..."
   }
   ```

2. **Analyze** (within 1 hour)
   - Which gate failed to reject?
   - Is it a data issue or engine issue?
   - Is it an isolated case or systemic pattern?
   - How many profiles affected?

3. **Design Fix** (within 2 hours)
   - Identify root cause pattern
   - Design generalized fix (not case-specific)
   - Document fix in code comment with JIRA link

4. **Implement** (within 4 hours)
   - Update eligibility_engine_strict_v21.py
   - Update test suite with new profile
   - Test against all 20 profiles
   - Verify fix doesn't break anything else

5. **Deploy** (within 6-8 hours)
   - Tag as hotfix (git tag v2.1-hotfix-001)
   - Deploy to staging first
   - Run full test suite
   - Deploy to production
   - Monitor for next 24 hours

---

## 📋 FINAL SIGN-OFF CHECKLIST

Required approvals before production deployment:

- [ ] **CTO**: Architecture and security review approved
- [ ] **Engineering Lead**: Code quality and testing approved
- [ ] **Product Lead**: Functionality and user impact approved
- [ ] **DevOps Lead**: Deployment and monitoring approved
- [ ] **Compliance Officer**: Legal and audit requirements met
- [ ] **Data Lead**: Data quality and cleanliness verified

All sign-offs must be in writing (email or Jira ticket).

---

## 📞 EMERGENCY CONTACTS

### Critical Issues (Production Down)
- **On-Call DevOps:** [Phone: XXX-XXXX]
- **On-Call Engineer:** [Phone: XXX-XXXX]
- **CTO (Escalation):** [Phone: XXX-XXXX]

### For Questions During Deployment
- **Technical Lead:** [Email: XXX]
- **DevOps Lead:** [Email: XXX]
- **Product Lead:** [Email: XXX]

### For False Positive Issues
- **Data Quality Team:** [Email: XXX]
- **Engineering Team:** [Email: XXX]
- **Support Team:** [Email: XXX]

---

## 📝 COMPLETION TEMPLATE

```
DEPLOYMENT COMPLETION REPORT
───────────────────────────────────────

Deployment Date: [Date]
Deployment Window: [Time]
Deployed By: [Name]
Reviewed By: [Name]

PRE-DEPLOYMENT
✓ All checklists completed
✓ Approvals obtained
✓ Testing successful
✓ Monitoring ready

DEPLOYMENT RESULT
Status: [SUCCESS / PARTIAL / FAILED]
False Positive Rate: [X%]
Response Time: [Xms avg, Xms max]
Error Rate: [X%]

ISSUES ENCOUNTERED
None / [List]

RESOLUTION
[Describe]

POST-DEPLOYMENT
24h Status: [STABLE / MONITORING / ROLLED BACK]
Issues After 24h: None / [List]

Sign-Off
Deployment Lead: _________________ Date: _____
CTO: _________________ Date: _____
```

---

## 🎓 KNOWLEDGE TRANSFER

Before anyone else deploys this, they should:

1. Read DELIVERABLES_SUMMARY.md (10 min)
2. Review COMPREHENSIVE_ELIGIBILITY_SOLUTION.md (40 min)
3. Study eligibility_engine_strict_v21.py (30 min)
4. Run test suite locally (30 min)
5. Walk through this checklist with previous deployer

**Estimated Learning Time:** 2 hours

---

**Checklist Version:** 2.1  
**Last Updated:** March 17, 2026  
**Next Revision:** After first production deployment  

**Approval:**
- Technical Lead: _________________ Date: _____
- DevOps Lead: _________________ Date: _____
- CTO: _________________ Date: _____
