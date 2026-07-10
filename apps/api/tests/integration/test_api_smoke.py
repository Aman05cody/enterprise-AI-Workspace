"""API smoke tests (no external DB required for openapi/health paths)."""

from fastapi.testclient import TestClient

from eaw.main import app

client = TestClient(app)


def test_health() -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_openapi_available() -> None:
    res = client.get("/openapi.json")
    assert res.status_code == 200
    body = res.json()
    assert body["info"]["title"]
    paths = body["paths"]
    assert "/health" in paths or any("health" in p for p in paths)
    assert any("/auth/login" in p for p in paths)
    assert any("knowledge-bases" in p for p in paths)


def test_docs() -> None:
    res = client.get("/docs")
    assert res.status_code == 200


def test_version_endpoint() -> None:
    res = client.get("/api/v1/version")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "version" in data
    assert data.get("phase") == 11


def test_auth_login_validation() -> None:
    res = client.post("/api/v1/auth/login", json={"email": "not-an-email", "password": "x"})
    assert res.status_code == 422


def test_protected_route_requires_auth() -> None:
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
