import requests

BASE_URL = "http://localhost:8000"


def test_stats():
    r = requests.get(f"{BASE_URL}/stats")
    assert r.status_code == 200
    data = r.json()
    assert "total_messages" in data
    assert "senders_count" in data