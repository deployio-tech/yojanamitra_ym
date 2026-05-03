import requests
import uuid

BASE_URL = "http://localhost:5000"
TIMEOUT = 30
HEADERS = {"Content-Type": "application/json"}


def post_api_readiness_check_with_various_scenarios():
    """
    Test POST /api/readiness/check with:
    - valid user_id, scheme_id, and profile_snapshot to receive readiness_status and clarification_reference
    - unknown scheme_id to verify 404 error response
    """

    # Helper function to create a readiness check
    def readiness_check(payload):
        url = f"{BASE_URL}/api/readiness/check"
        response = requests.post(url, headers=HEADERS, json=payload, timeout=TIMEOUT)
        return response

    # Generate a unique user_id for testing
    user_id = str(uuid.uuid4())

    # For valid scheme_id we need to find a real scheme_id, but since no direct endpoint is given, 
    # let's assume "scheme_id_valid" is known or create a resource in the system if needed.
    # Because instructions say no mocks, real backend only, we will try a known scheme_id "scheme123"
    # In case this is unknown, user to replace with a suitable scheme_id according to DB.
    scheme_id_valid = "scheme123"

    # Sample profile snapshot with minimal plausible data (assuming from product description)
    profile_snapshot = {
        "age": 30,
        "gender": "M",
        "income": 50000,
        "state": "KA"
    }

    valid_payload = {
        "user_id": user_id,
        "scheme_id": scheme_id_valid,
        "profile_snapshot": profile_snapshot
    }

    # Test 1: Valid readiness check
    response = readiness_check(valid_payload)
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    json_resp = response.json()
    assert "readiness_status" in json_resp, "Missing 'readiness_status' in response"
    assert "clarification_reference" in json_resp, "Missing 'clarification_reference' in response"
    assert isinstance(json_resp["readiness_status"], str), "'readiness_status' should be a string"
    assert json_resp["clarification_reference"], "'clarification_reference' should not be empty"

    # Test 2: Unknown scheme_id -> expecting 404
    unknown_scheme_id = "unknown-scheme-id-xyz"
    invalid_payload = {
        "user_id": user_id,
        "scheme_id": unknown_scheme_id,
        "profile_snapshot": profile_snapshot
    }

    response_not_found = readiness_check(invalid_payload)
    assert response_not_found.status_code == 404, f"Expected 404 Not Found for unknown scheme_id, got {response_not_found.status_code}"
    try:
        resp_json = response_not_found.json()
        assert "error" in resp_json or "message" in resp_json, "Expected error or message field in 404 response"
    except Exception:
        # If no JSON, pass as 404 status is key validation
        pass


post_api_readiness_check_with_various_scenarios()