import hmac, hashlib, requests, json

BASE_URL = "http://localhost:8000"
SECRET = "testsecret"

BODY = {
"message_id": "m_test_1",
"from": "+919876543210",
"to": "+14155550100",
"ts": "2025-01-15T10:00:00Z",
"text": "Hello Test"
}

RAW = json.dumps(BODY).encode()

def sign(body: bytes):
    return hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def test_invalid_signature():
    r = requests.post(
    f"{BASE_URL}/webhook",
    headers={"X-Signature": "wrong", "Content-Type": "application/json"},
    data=RAW,
    )
    assert r.status_code == 401


def test_valid_insert():
    r = requests.post(
    f"{BASE_URL}/webhook",
    headers={"X-Signature": sign(RAW), "Content-Type": "application/json"},
    data=RAW,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_duplicate_idempotent():
    r = requests.post(
    f"{BASE_URL}/webhook",
    headers={"X-Signature": sign(RAW), "Content-Type": "application/json"},
    data=RAW,
    )
    assert r.status_code == 200