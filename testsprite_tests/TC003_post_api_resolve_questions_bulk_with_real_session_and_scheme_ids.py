import requests

BASE_URL = "http://localhost:5000"

def test_post_api_resolve_questions_bulk_with_real_session_and_scheme_ids():
    timeout = 30

    # Step 1: POST to /api/recommendations with valid demographics
    demographics_payload = {
        "age": 30,
        "gender": "M",
        "income": 50000,
        "state": "Delhi"
    }
    rec_resp = requests.post(
        f"{BASE_URL}/api/recommendations", json=demographics_payload, timeout=timeout
    )
    assert rec_resp.status_code == 200, f"Recommendations failed: {rec_resp.text}"
    rec_data = rec_resp.json()
    assert isinstance(rec_data, dict), "Recommendations response not a dict"

    # Extract scheme IDs from any bucket that has scheme IDs
    scheme_ids = []
    for bucket in ["eligible", "possibly_eligible", "ineligible"]:
        if bucket in rec_data and isinstance(rec_data[bucket], list):
            for item in rec_data[bucket]:
                sid = item.get("id")
                if isinstance(sid, int):
                    scheme_ids.append(sid)
    assert len(scheme_ids) > 0, "No valid scheme_ids extracted from recommendations"

    # Prepare payload for /api/resolve-questions using first scheme_id
    scheme_id = scheme_ids[0]
    payload = {
        "user_id": "test-user-123",  # Dummy user_id since no login
        "profile_context": {"state": "Delhi"},
        "scheme_id": scheme_id
    }

    # Call POST /api/resolve-questions
    resolve_resp = requests.post(
        f"{BASE_URL}/api/resolve-questions", json=payload, timeout=timeout
    )
    assert resolve_resp.status_code == 200, f"resolve-questions failed: {resolve_resp.text}"
    resp_data = resolve_resp.json()
    assert isinstance(resp_data, dict), "resolve-questions response not a dict"
    assert "questions" in resp_data, "questions missing in response"
    assert isinstance(resp_data["questions"], list), "questions is not a list"
    # Validate each question item has 32-character question_hash
    for q in resp_data["questions"]:
        q_hash = q.get("question_hash")
        assert isinstance(q_hash, str) and len(q_hash) == 32, f"Invalid question_hash: {q_hash}"

    # Since no auth scheme documented, unauth test is not applicable; skipping


test_post_api_resolve_questions_bulk_with_real_session_and_scheme_ids()
