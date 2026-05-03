import requests
import uuid
import string
import random

BASE_URL = "http://localhost:5000"
TIMEOUT = 30

def generate_random_profile_context():
    # Example valid profile_context structure (should adapt as per real API schema)
    return {
        "age": 30,
        "gender": "male",
        "income": 50000,
        "state": "KA"
    }

def generate_random_user_id():
    return str(uuid.uuid4())

def generate_random_scheme_id():
    # In a real test environment, a valid scheme_id should be used.
    # Here we use a UUID string to simulate.
    return str(uuid.uuid4())

def is_valid_question_hash(qhash):
    return isinstance(qhash, str) and len(qhash) == 32 and all(c in string.hexdigits for c in qhash)

def test_post_api_resolve_questions_for_question_generation_and_answer_routing():
    headers = {"Content-Type": "application/json"}
    
    # 1. Test POST /api/resolve-questions with valid user_id, profile_context, scheme_id
    user_id = generate_random_user_id()
    scheme_id = generate_random_scheme_id()
    valid_profile_context = generate_random_profile_context()
    
    req_payload = {
        "user_id": user_id,
        "profile_context": valid_profile_context,
        "scheme_id": scheme_id
    }

    questions = []
    try:
        resp = requests.post(
            f"{BASE_URL}/api/resolve-questions",
            json=req_payload,
            headers=headers,
            timeout=TIMEOUT,
        )
        assert resp.status_code == 200, f"Expected 200 but got {resp.status_code}"
        data = resp.json()
        assert isinstance(data, list), "Response should be a list of questions"
        assert len(data) > 0, "Questions list should not be empty"
        for question in data:
            qhash = question.get("question_hash")
            assert qhash is not None, "Each question must have question_hash"
            assert isinstance(qhash, str), "question_hash must be a string"
            assert len(qhash) == 32, f"question_hash length must be 32 but got {len(qhash)}"
            questions.append(qhash)
        
        # 2. Test POST /api/resolve-questions with empty profile_context -> expect 400
        invalid_payloads = [
            {"user_id": user_id, "profile_context": {}, "scheme_id": scheme_id},
            {"user_id": user_id, "profile_context": None, "scheme_id": scheme_id},
            {"user_id": user_id, "scheme_id": scheme_id},  # Missing profile_context
            {"user_id": user_id, "profile_context": "not-a-dict", "scheme_id": scheme_id},
        ]
        
        for invalid_payload in invalid_payloads:
            r = requests.post(
                f"{BASE_URL}/api/resolve-questions",
                json=invalid_payload,
                headers=headers,
                timeout=TIMEOUT,
            )
            assert r.status_code == 400, f"Expected 400 for invalid payload but got {r.status_code}"
            rjson = r.json()
            assert "error" in rjson or "message" in rjson, "400 response should have error message"
        
        # 3. If questions list empty, cannot continue answer routing test
        if not questions:
            return
        
        # 4. Test submitting answers referencing question_hash for routing results
        # Iterate over question hashes to test both profile-update and re-evaluate scenarios
        for qhash in questions:
            # Construct an answer payload
            # We don't know real expected answer content structure, so send generic answer
            answer_payload = {
                "question_hash": qhash,
                "answer": "test_answer_value"
            }
            r = requests.post(
                f"{BASE_URL}/api/resolve-questions",
                json=answer_payload,
                headers=headers,
                timeout=TIMEOUT,
            )
            assert r.status_code == 200, f"Expected 200 for answer routing but got {r.status_code}"
            rjson = r.json()
            assert "routing_result" in rjson, "Response must include routing_result"
            routing_result = rjson["routing_result"]
            assert routing_result in ("profile-update", "re-evaluate"), f"Unexpected routing_result: {routing_result}"

            if routing_result == "re-evaluate":
                assert "re-evaluate_payload" in rjson, "re-evaluate action must include re-evaluate_payload"
                ree_payload = rjson["re-evaluate_payload"]

                # POST to /api/readiness/re-evaluate with returned payload and trigger 'ai'
                ree_payload.update({"trigger": "ai"})
                ree_resp = requests.post(
                    f"{BASE_URL}/api/readiness/re-evaluate",
                    json=ree_payload,
                    headers=headers,
                    timeout=TIMEOUT,
                )
                assert ree_resp.status_code == 200, f"Expected 200 from re-evaluate but got {ree_resp.status_code}"
                ree_data = ree_resp.json()
                # Verify presence of new_verdict and some kind of acknowledgement/upsert confirmation
                assert "new_verdict" in ree_data, "re-evaluate response must have new_verdict"
                # Assuming some confirmation field like 'upsert_acknowledged' or similar
                # The PRD states upsert confirmation, we loosely check for presence of keys
                assert any(k in ree_data for k in ("upsert_acknowledged", "upsert_confirmation", "scheme_clarification_upsert")), \
                    "re-evaluate response should confirm SchemeClarification upsert"

        # 5. Test with invalid/unknown question_hash -> expect 404 with error 'question not found'
        invalid_question_hashes = [
            "0"*32,
            "f"*31 + "g",  # invalid hexdigit
            "".join(random.choices(string.ascii_letters + string.digits, k=32)),
        ]
        for invalid_qhash in invalid_question_hashes:
            invalid_answer_payload = {
                "question_hash": invalid_qhash,
                "answer": "some answer"
            }
            r = requests.post(
                f"{BASE_URL}/api/resolve-questions",
                json=invalid_answer_payload,
                headers=headers,
                timeout=TIMEOUT,
            )
            assert r.status_code == 404, f"Expected 404 for unknown question_hash but got {r.status_code}"
            err = r.json()
            err_msg = err.get("error") or err.get("message") or ""
            assert "question not found" in err_msg.lower(), f"Expected error message 'question not found', got: {err_msg}"

    finally:
        # No resource deletion API described, skip explicit cleanup
        pass

test_post_api_resolve_questions_for_question_generation_and_answer_routing()