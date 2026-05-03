import requests
import uuid

BASE_URL = "http://localhost:5000"
TIMEOUT = 30


def test_post_api_recommendations_refresh_with_readiness_after_login():
    session = requests.Session()

    # Step 1: Register with unique email
    unique_email = f"test_{uuid.uuid4()}@example.com"
    register_payload = {
        "email": unique_email,
        "password": "TestPassword123!"
    }
    register_resp = session.post(
        f"{BASE_URL}/api/register",
        json=register_payload,
        timeout=TIMEOUT
    )
    assert register_resp.status_code == 200, f"Registration failed: {register_resp.text}"

    # Step 2: Login with same credentials
    login_payload = {
        "email": unique_email,
        "password": "TestPassword123!"
    }
    login_resp = session.post(
        f"{BASE_URL}/api/login",
        json=login_payload,
        timeout=TIMEOUT
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    assert "session" in session.cookies, "Session cookie not set after login"

    # Step 3: Authenticated call to POST /api/recommendations/refresh-with-readiness
    refresh_resp = session.post(
        f"{BASE_URL}/api/recommendations/refresh-with-readiness",
        timeout=TIMEOUT
    )
    assert refresh_resp.status_code == 200, f"Refresh with readiness failed: {refresh_resp.text}"

    refresh_json = refresh_resp.json()
    # Validate response contains recommendations and possibly_eligible arrays
    assert "recommendations" in refresh_json, "Missing 'recommendations' in response"
    assert isinstance(refresh_json.get("recommendations"), list), "'recommendations' is not a list"
    assert "possibly_eligible" in refresh_json, "Missing 'possibly_eligible' in response"
    assert isinstance(refresh_json.get("possibly_eligible"), list), "'possibly_eligible' is not a list"

    # Validate readiness filtering metadata presence (check any key with 'readiness' or related metadata)
    assert (
        any(k in refresh_json for k in ["readiness_metadata", "readiness_filtering", "readiness_filtering_metadata"]) or
        any(k.startswith("readiness") for k in refresh_json.keys())
    ), "Readiness filtering metadata missing in response"

    # Step 4: Unauthenticated call to POST /api/recommendations/refresh-with-readiness returns 401
    unauth_session = requests.Session()
    unauth_resp = unauth_session.post(
        f"{BASE_URL}/api/recommendations/refresh-with-readiness",
        timeout=TIMEOUT
    )
    assert unauth_resp.status_code == 401, f"Unauthenticated call did not return 401: {unauth_resp.status_code} {unauth_resp.text}"


test_post_api_recommendations_refresh_with_readiness_after_login()