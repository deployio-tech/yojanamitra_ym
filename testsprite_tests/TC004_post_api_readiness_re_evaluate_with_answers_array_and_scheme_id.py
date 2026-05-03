import requests
import uuid
import time

BASE_URL = "http://localhost:5000"
TIMEOUT = 30

def test_post_api_readiness_re_evaluate_with_answers_array_and_scheme_id():
    session = requests.Session()
    unique_email = f"user_{uuid.uuid4()}@example.com"
    password = "TestPass123!"

    # Register new user
    register_payload = {
        "email": unique_email,
        "password": password,
        "confirm_password": password,
        "name": "Test User"  # Added name field as possibly required
    }
    r = session.post(f"{BASE_URL}/api/register", json=register_payload, timeout=TIMEOUT)
    assert r.status_code == 200, f"Registration failed: {r.text}"
    user_id = r.json().get("user", {}).get("id")
    assert user_id is not None, "User ID not found in registration response"

    # Login with same credentials
    login_payload = {
        "email": unique_email,
        "password": password
    }
    r = session.post(f"{BASE_URL}/api/login", json=login_payload, timeout=TIMEOUT)
    assert r.status_code == 200, f"Login failed: {r.text}"
    assert 'session' in session.cookies, "Session cookie not set after login"

    # Get possible scheme_ids from POST /api/recommendations with demographics
    demographics_payload = {
        "age": 30,
        "gender": "M",
        "income": 30000,
        "state": "KA"
    }
    r = session.post(f"{BASE_URL}/api/recommendations", json=demographics_payload, timeout=TIMEOUT)
    assert r.status_code == 200, f"POST /api/recommendations failed: {r.text}"
    json_resp = r.json()
    possibly_eligible = json_resp.get('possibly-eligible', [])
    assert isinstance(possibly_eligible, list), "possibly-eligible not a list"
    assert len(possibly_eligible) > 0, "No possibly-eligible schemes found to test with"
    scheme_id = possibly_eligible[0]
    assert scheme_id is not None, "No scheme id found in possibly-eligible"

    # Prepare clarifications array with dummy question_hash
    question_hash_dummy = "0" * 32

    clarifications = [{
        "question_hash": question_hash_dummy,
        "answer": "test answer"
    }]

    payload = {
        "user_id": user_id,
        "scheme_id": scheme_id,
        "clarifications": clarifications,
        "trigger": "manual"  # Added trigger field as per PRD
    }

    # POST to /api/readiness/re-evaluate
    r = session.post(f"{BASE_URL}/api/readiness/re-evaluate", json=payload, timeout=TIMEOUT)
    try:
        assert r.status_code == 200, f"POST /api/readiness/re-evaluate failed: {r.status_code} {r.text}"
        resp = r.json()
        # Validate response contains new_verdict and database upsert acknowledgement
        assert "new_verdict" in resp, "Response missing 'new_verdict'"
        assert "upsert_status" in resp, "Response missing 'upsert_status'"
    finally:
        pass

test_post_api_readiness_re_evaluate_with_answers_array_and_scheme_id()
