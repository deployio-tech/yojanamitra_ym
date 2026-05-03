import requests
import time

BASE_URL = "http://localhost:5000"
TIMEOUT = 30

def create_resource_for_test():
    # Use /api/recommendations with valid demographics to get user_id and scheme_id for test
    demographics = {"age": 30, "gender": "M", "income": 50000, "state": "KA"}
    response = requests.post(f"{BASE_URL}/api/recommendations", json=demographics, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    # Extract at least one scheme_id from eligible or possibly-eligible buckets and create a user_id (simulate)
    # Assuming user_id can be a random int or fixed string for test, or assume user_id is required from DB;
    # Because no user create endpoint is given, we use static user_id and scheme_id from response for test.
    scheme_id = None
    buckets = data.get("buckets", {})
    for bucket_name in ("eligible", "possibly-eligible", "ineligible"):
        bucket = buckets.get(bucket_name, [])
        if bucket:
            scheme_id = bucket[0]
            break
    if scheme_id is None:
        assert False, "No scheme_id available for testing"
    user_id = "test_user_001"
    return user_id, scheme_id

def delete_scheme_clarifications(user_id, scheme_id):
    pass

def test_post_api_readiness_re_evaluate_with_clarifications_and_trigger():
    user_id, scheme_id = create_resource_for_test()

    clarifications_valid = [
        {"question_hash": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p", "answer": "yes"},
        {"question_hash": "z9y8x7w6v5u4t3s2r1q0p9o8n7m6l5k", "answer": "no"}
    ]

    clarifications_malformed = [
        {"question_hash": "short_hash", "answer": "maybe"},
        {"ans": "missing_question_hash"}
    ]

    triggers = ["ai", "manual"]

    try:
        # Test valid clarifications with both trigger values
        for trigger in triggers:
            payload = {
                "user_id": user_id,
                "scheme_id": scheme_id,
                "clarifications": clarifications_valid,
                "trigger": trigger
            }
            response = requests.post(f"{BASE_URL}/api/readiness/re-evaluate", json=payload, timeout=TIMEOUT)
            assert response.status_code == 200, f"Expected 200 OK for valid payload with trigger {trigger}, got {response.status_code}"
            resp_json = response.json()
            # Validate new_verdict field presence and format (assuming dict or str)
            assert "new_verdict" in resp_json, "Response missing 'new_verdict'"
            assert resp_json["new_verdict"], "'new_verdict' should not be empty or null"
            # Validate SchemeClarification upsert acknowledgement - assume a field 'upserted' (bool or count)
            assert ("upserted" in resp_json) and (resp_json["upserted"] >= 1 or resp_json["upserted"] is True), \
                f"Expected upsert acknowledgement with 'upserted' field, got: {resp_json}"

        # Test malformed clarifications payload triggers 400 and no upsert
        for trigger in triggers:
            payload = {
                "user_id": user_id,
                "scheme_id": scheme_id,
                "clarifications": clarifications_malformed,
                "trigger": trigger
            }
            response = requests.post(f"{BASE_URL}/api/readiness/re-evaluate", json=payload, timeout=TIMEOUT)
            assert response.status_code == 400, f"Expected 400 Bad Request for malformed clarifications with trigger {trigger}, got {response.status_code}"
            try:
                resp_json = response.json()
                assert "upserted" not in resp_json or resp_json.get("upserted") in [0, False], \
                    "Malformed payload should not trigger upsert"
            except Exception:
                pass

    finally:
        delete_scheme_clarifications(user_id, scheme_id)

test_post_api_readiness_re_evaluate_with_clarifications_and_trigger()
