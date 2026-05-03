import requests

BASE_URL = "http://localhost:5000"
TIMEOUT = 30

def test_get_api_readiness_verify_pool_with_clarification_reference():
    # Step 1: Create a readiness check to obtain a valid clarification_reference
    readiness_check_url = f"{BASE_URL}/api/readiness/check"
    readiness_check_payload = {
        "user_id": "test-user-123",
        "scheme_id": "test-scheme-abc",
        "profile_snapshot": {
            "age": 30,
            "gender": "M",
            "income": 50000,
            "state": "KA"
        }
    }
    headers = {"Content-Type": "application/json"}

    clarification_reference = None

    try:
        # POST readiness check to get clarification_reference
        resp = requests.post(readiness_check_url, json=readiness_check_payload, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        # Validate presence of readiness_status and clarification_reference
        assert "readiness_status" in data, "Missing readiness_status in response"
        assert "clarification_reference" in data, "Missing clarification_reference in response"
        clarification_reference = data["clarification_reference"]
        assert isinstance(clarification_reference, str) and len(clarification_reference) > 0, "Invalid clarification_reference"

        # Step 2: Use clarification_reference to GET clarification history and past answers
        verify_pool_url = f"{BASE_URL}/api/readiness/verify-pool"
        params = {"clarification_ref": clarification_reference}

        verify_resp = requests.get(verify_pool_url, params=params, headers=headers, timeout=TIMEOUT)
        verify_resp.raise_for_status()
        verify_data = verify_resp.json()

        # Validate the response structure includes clarification history and answers for that reference
        # We expect at least some keys related to history and past answers; exact keys not specified
        # So assert it's a dictionary and not empty
        assert isinstance(verify_data, dict), "Response is not a JSON object"
        assert len(verify_data) > 0, "Clarification history response is empty"

        # Optionally, check for presence of keys that indicate history and past answers
        # Based on PRD "clarification history and past answers associated with that reference"
        # Commonly keys may be 'history', 'answers', 'clarification_reference'
        assert "clarification_reference" in verify_data or "history" in verify_data or "answers" in verify_data, \
            "Response missing expected keys such as clarification_reference, history, or answers"

    finally:
        # Cleanup not needed since no resource creation beyond readiness check (no persistent resource)
        pass

test_get_api_readiness_verify_pool_with_clarification_reference()