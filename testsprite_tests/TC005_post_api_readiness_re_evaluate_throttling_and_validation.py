import requests
import time
import uuid

BASE_URL = "http://localhost:5000"
TIMEOUT = 30

def test_post_api_readiness_re_evaluate_throttling_and_validation():
    session = requests.Session()
    # Step 1: Register user
    unique_email = f"test_{uuid.uuid4()}@example.com"
    register_payload = {
        "email": unique_email,
        "password": "TestPassword123!"
    }
    r = session.post(f"{BASE_URL}/api/register", json=register_payload, timeout=TIMEOUT)
    assert r.status_code == 200 or r.status_code == 201

    # Step 2: Login
    login_payload = {
        "email": unique_email,
        "password": "TestPassword123!"
    }
    r = session.post(f"{BASE_URL}/api/login", json=login_payload, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "session" in session.cookies

    # Step 3: Fetch initial pool from /api/recommendations (POST)
    # According to PRD, /api/recommendations is POST with demographics
    demographics_payload = {"age":30, "gender":"M", "income":50000, "state":"KA"}
    r = session.post(f"{BASE_URL}/api/recommendations", json=demographics_payload, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    possibly_eligible = data.get("possibly-eligible", [])
    assert isinstance(possibly_eligible, list) and len(possibly_eligible) > 0, "No possibly eligible schemes found"
    first_item = possibly_eligible[0]
    if isinstance(first_item, int):
        scheme_id = first_item
    elif isinstance(first_item, dict) and isinstance(first_item.get("id"), int):
        scheme_id = first_item.get("id")
    else:
        assert False, "Invalid scheme_id in possibly_eligible"

    # Step 4: Trigger batch analysis /api/recommendations/readiness-reclassify with scheme_ids
    payload_reclassify = {"scheme_ids": [scheme_id]}
    r = session.post(f"{BASE_URL}/api/recommendations/readiness-reclassify", json=payload_reclassify, timeout=TIMEOUT)
    assert r.status_code == 200
    reclassify_data = r.json()
    questions = reclassify_data.get("questions", [])
    assert isinstance(questions, list) and len(questions) > 0, "No questions returned for scheme"

    question = questions[0]
    question_hash = question.get("question_hash")
    question_text = question.get("question", "dummy question")
    original_gap = question.get("original_gap", "unknown")
    assert isinstance(question_hash, str) and len(question_hash) == 32, "Invalid question_hash"

    base_clarification_obj = {
        "question_hash": question_hash,
        "answer": "test answer"
    }

    # Prepare a helper for valid payloads
    def make_payload(clarifications_array):
        return {
            "user_id": unique_email,
            "scheme_id": scheme_id,
            "clarifications": clarifications_array,
            "trigger": "manual"
        }

    # === Validation Case 1: Missing clarifications array ===
    payload_missing_clarifications = {
        "user_id": unique_email,
        "scheme_id": scheme_id,
        "trigger": "manual"
        # no "clarifications" key
    }
    r = session.post(f"{BASE_URL}/api/readiness/re-evaluate", json=payload_missing_clarifications, timeout=TIMEOUT)
    assert r.status_code == 400
    err = r.json()
    reason = err.get("reason") or err.get("error") or ""
    assert isinstance(reason, str)
    assert "no_answers_provided" in reason.lower() or "clarifications" in reason.lower()

    # === Validation Case 2: Oversized clarifications array ===
    large_clarifications = [base_clarification_obj] * 1001  # Assuming >1000 triggers "too_many_answers"
    payload_too_many = make_payload(large_clarifications)
    r = session.post(f"{BASE_URL}/api/readiness/re-evaluate", json=payload_too_many, timeout=TIMEOUT)
    assert r.status_code == 400
    err = r.json()
    reason = err.get("reason") or err.get("error") or ""
    assert isinstance(reason, str)
    assert "too_many_answers" in reason.lower() or "clarifications" in reason.lower()

    # === Throttling: repeatedly post valid clarifications in quick succession ===
    valid_clarifications = [base_clarification_obj]
    payload_valid = make_payload(valid_clarifications)

    throttling_hit = False
    throttling_status_code = 429
    max_attempts = 10
    for attempt in range(max_attempts):
        r = session.post(f"{BASE_URL}/api/readiness/re-evaluate", json=payload_valid, timeout=TIMEOUT)
        if r.status_code == throttling_status_code:
            throttling_hit = True
            break
        assert r.status_code == 200, f"Unexpected status code {r.status_code} on attempt {attempt + 1}"

    assert throttling_hit, f"Did not receive expected throttling status {throttling_status_code} after {max_attempts} rapid requests"

test_post_api_readiness_re_evaluate_throttling_and_validation()
