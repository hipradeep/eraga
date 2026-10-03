def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"


def test_welcome(client):
    response = client.get("/welcome")
    assert response.status_code == 200
    assert "ERAGA" in response.json()["message"]


def test_timing_header_present(client):
    response = client.get("/health")
    assert "X-Process-Time-Ms" in response.headers


def test_openapi_schema(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "ERAGA" in response.json()["info"]["title"]
