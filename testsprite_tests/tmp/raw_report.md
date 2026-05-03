
# TestSprite AI Testing Report(MCP)

---

## 1️⃣ Document Metadata
- **Project Name:** yojanamitra_complete
- **Date:** 2026-04-18
- **Prepared by:** TestSprite AI Team

---

## 2️⃣ Requirement Validation Summary

#### Test TC001 register_login_then_get_api_recommendations
- **Test Code:** [TC001_register_login_then_get_api_recommendations.py](./TC001_register_login_then_get_api_recommendations.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 78, in <module>
  File "<string>", line 56, in test_register_login_then_post_api_recommendations
  File "/var/lang/lib/python3.12/site-packages/requests/models.py", line 1024, in raise_for_status
    raise HTTPError(http_error_msg, response=self)
requests.exceptions.HTTPError: 405 Client Error: METHOD NOT ALLOWED for url: http://localhost:5000/api/recommendations

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/fcea3aee-a38d-4035-af27-1d9fbc63a3b0/923d67d0-53ce-4028-bdc3-9b02c4e7ad5e
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC002 post_api_recommendations_refresh_with_readiness_after_login
- **Test Code:** [TC002_post_api_recommendations_refresh_with_readiness_after_login.py](./TC002_post_api_recommendations_refresh_with_readiness_after_login.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 66, in <module>
  File "<string>", line 22, in test_post_api_recommendations_refresh_with_readiness_after_login
AssertionError: Registration failed: {
  "error": "Missing required fields"
}


- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/fcea3aee-a38d-4035-af27-1d9fbc63a3b0/101088ea-beb1-4fd2-815e-eb64b0bdfa96
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC003 post_api_resolve_questions_bulk_with_real_session_and_scheme_ids
- **Test Code:** [TC003_post_api_resolve_questions_bulk_with_real_session_and_scheme_ids.py](./TC003_post_api_resolve_questions_bulk_with_real_session_and_scheme_ids.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 57, in <module>
  File "<string>", line 18, in test_post_api_resolve_questions_bulk_with_real_session_and_scheme_ids
AssertionError: Recommendations failed: <!doctype html>
<html lang=en>
<title>405 Method Not Allowed</title>
<h1>Method Not Allowed</h1>
<p>The method is not allowed for the requested URL.</p>


- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/fcea3aee-a38d-4035-af27-1d9fbc63a3b0/2d6a72f6-6f1a-423c-8d5a-7799a102823a
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC004 post_api_readiness_re_evaluate_with_answers_array_and_scheme_id
- **Test Code:** [TC004_post_api_readiness_re_evaluate_with_answers_array_and_scheme_id.py](./TC004_post_api_readiness_re_evaluate_with_answers_array_and_scheme_id.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 76, in <module>
  File "<string>", line 21, in test_post_api_readiness_re_evaluate_with_answers_array_and_scheme_id
AssertionError: Registration failed: {
  "message": "Registration successful",
  "user": {
    "email": "user_37956f87-c05e-46fb-ad32-ef124e20b9c8@example.com",
    "id": 38,
    "mobile": "",
    "name": "Test User",
    "profile": {
      "is_bpl": false,
      "is_citizen": true,
      "is_student": false
    }
  }
}


- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/fcea3aee-a38d-4035-af27-1d9fbc63a3b0/4a097613-63e1-494c-9ca9-78aa6496deaf
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC005 post_api_readiness_re_evaluate_throttling_and_validation
- **Test Code:** [TC005_post_api_readiness_re_evaluate_throttling_and_validation.py](./TC005_post_api_readiness_re_evaluate_throttling_and_validation.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 112, in <module>
  File "<string>", line 17, in test_post_api_readiness_re_evaluate_throttling_and_validation
AssertionError

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/fcea3aee-a38d-4035-af27-1d9fbc63a3b0/66db602f-e967-4018-89f3-702fb661cec9
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---


## 3️⃣ Coverage & Matching Metrics

- **0.00** of tests passed

| Requirement        | Total Tests | ✅ Passed | ❌ Failed  |
|--------------------|-------------|-----------|------------|
| ...                | ...         | ...       | ...        |
---


## 4️⃣ Key Gaps / Risks
{AI_GNERATED_KET_GAPS_AND_RISKS}
---