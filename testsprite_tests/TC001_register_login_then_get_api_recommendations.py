import requests
import uuid

BASE_URL = "http://localhost:5000"

def test_register_login_then_post_api_recommendations():
    session = requests.Session()
    timeout = 30

    # Create unique user data for registration
    unique_email = f"testuser_{uuid.uuid4()}@example.com"
    register_payload = {
        "email": unique_email,
        "password": "TestPass123!",
        "name": "Test User"
    }

    # Register user
    try:
        reg_resp = session.post(
            f"{BASE_URL}/api/register",
            json=register_payload,
            timeout=timeout,
        )
        reg_resp.raise_for_status()
        assert reg_resp.status_code == 200 or reg_resp.status_code == 201

        # Login payload uses same credentials as registration
        login_payload = {
            "email": unique_email,
            "password": "TestPass123!"
        }
        login_resp = session.post(
            f"{BASE_URL}/api/login",
            json=login_payload,
            timeout=timeout,
        )
        login_resp.raise_for_status()
        assert login_resp.status_code == 200
        # Check session cookie present
        assert "session" in session.cookies

        # Post recommendations with required demographics
        demographics_payload = {
            "age": 30,
            "gender": "M",
            "income": 50000,
            "state": "KA"
        }

        rec_resp = session.post(
            f"{BASE_URL}/api/recommendations",
            json=demographics_payload,
            timeout=timeout,
        )
        rec_resp.raise_for_status()
        assert rec_resp.status_code == 200

        rec_json = rec_resp.json()
        # Validate expected recommendation buckets: eligible, possibly-eligible, ineligible as keys
        assert isinstance(rec_json, dict)
        keys = rec_json.keys()
        buckets_present = any(
            b in keys for b in ("eligible", "possibly_eligible", "possibly-eligible", "ineligible")
        )
        meta_present = "meta" in keys

        assert buckets_present, "Expected recommendation bucket keys not found in response"
        assert meta_present, "Expected 'meta' field not found in response"

    finally:
        # Cleanup: if API supported user deletion, we would delete here
        # But the PRD does not specify such endpoint
        # So no deletion done
        pass


test_register_login_then_post_api_recommendations()