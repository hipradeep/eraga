"""API tests that do not require a database."""

import pytest

from app.main import VERSION


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == VERSION
    assert body["embedding_dim"] == 768


def test_welcome(client):
    response = client.get("/welcome")
    assert response.status_code == 200
    assert "ERAGA" in response.json()["message"]


def test_timing_header_present(client):
    assert "X-Process-Time-Ms" in client.get("/health").headers


def test_openapi_schema(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "ERAGA" in schema["info"]["title"]
    assert "/api/v1/chat/query" in schema["paths"]
    assert "/api/v1/documents" in schema["paths"]


def test_docs_ui_served(client):
    assert client.get("/docs").status_code == 200


@pytest.mark.parametrize(
    "path",
    ["/health", "/health/models", "/api/v1/chat/context-preview?question=test"],
)
def test_unauthenticated_endpoints_do_not_500(client, path):
    assert client.get(path).status_code < 500
