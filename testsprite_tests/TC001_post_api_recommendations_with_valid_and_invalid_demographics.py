import requests

BASE_URL = "http://localhost:5000"
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 30

def test_post_api_recommendations_with_valid_and_invalid_demographics():
    url = f"{BASE_URL}/api/recommendations"

    # Valid demographic data
    valid_payload = {
        "age": 30,
        "gender": "M",
        "income": 50000,
        "state": "KA"
    }
    try:
        valid_response = requests.post(url, json=valid_payload, headers=HEADERS, timeout=TIMEOUT)
        assert valid_response.status_code == 200, f"Expected 200 but got {valid_response.status_code} with body {valid_response.text}"
        data = valid_response.json()
        # Validate presence of buckets and that each is a list
        assert isinstance(data, dict), "Response JSON should be an object"
        for bucket in ["eligible", "possibly-eligible", "ineligible"]:
            assert bucket in data, f"Missing bucket '{bucket}' in response"
            assert isinstance(data[bucket], list), f"Bucket '{bucket}' should be a list"
            # Optionally check scheme IDs are strings or ints
            for scheme_id in data[bucket]:
                assert isinstance(scheme_id, (int, str)), f"Scheme ID in bucket '{bucket}' should be int or str"
    except requests.RequestException as ex:
        assert False, f"Request failed during valid demographic test: {ex}"

    # Missing age field
    missing_age_payload = {
        "gender": "F",
        "income": 30000,
        "state": "MH"
    }
    try:
        missing_age_response = requests.post(url, json=missing_age_payload, headers=HEADERS, timeout=TIMEOUT)
        assert missing_age_response.status_code == 400, f"Expected 400 for missing age but got {missing_age_response.status_code} with body {missing_age_response.text}"
        error_data = missing_age_response.json()
        assert "error" in error_data or "message" in error_data, "Response should contain error or message field"
        error_msg = error_data.get("error", "") or error_data.get("message", "")
        assert "age" in error_msg.lower() or "missing" in error_msg.lower(), f"Expected error message to mention missing 'age', got: {error_msg}"
    except requests.RequestException as ex:
        assert False, f"Request failed during missing age test: {ex}"

    # Invalid gender code
    invalid_gender_payload = {
        "age": 25,
        "gender": "X",
        "income": 40000,
        "state": "TN"
    }
    try:
        invalid_gender_response = requests.post(url, json=invalid_gender_payload, headers=HEADERS, timeout=TIMEOUT)
        assert invalid_gender_response.status_code == 400, f"Expected 400 for invalid gender but got {invalid_gender_response.status_code} with body {invalid_gender_response.text}"
        error_data = invalid_gender_response.json()
        assert "error" in error_data or "message" in error_data, "Response should contain error or message field for invalid gender"
        error_msg = error_data.get("error", "") or error_data.get("message", "")
        assert "gender" in error_msg.lower() or "invalid" in error_msg.lower(), f"Expected error message to mention invalid 'gender', got: {error_msg}"
    except requests.RequestException as ex:
        assert False, f"Request failed during invalid gender test: {ex}"

test_post_api_recommendations_with_valid_and_invalid_demographics()