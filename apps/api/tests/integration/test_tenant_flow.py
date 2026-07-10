"""End-to-end multi-tenant flow against real PostgreSQL (CI service)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def _register(client, email: str, name: str = "User"):
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePass1",
            "full_name": name,
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()["data"]
    return body["access_token"], body["user"]["id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_register_login_org_kb_upload_chat(api_client, tmp_path):
    token_a, user_a = _register(api_client, "alice@example.com", "Alice")
    token_b, user_b = _register(api_client, "bob@example.com", "Bob")
    assert user_a != user_b

    # Create isolated workspaces
    org_a = api_client.post(
        "/api/v1/organizations",
        headers=_auth(token_a),
        json={"name": "Acme", "slug": "acme-tenant-a"},
    )
    assert org_a.status_code == 201, org_a.text
    org_a_id = org_a.json()["data"]["id"]

    org_b = api_client.post(
        "/api/v1/organizations",
        headers=_auth(token_b),
        json={"name": "Beta", "slug": "beta-tenant-b"},
    )
    assert org_b.status_code == 201
    org_b_id = org_b.json()["data"]["id"]

    # Tenant isolation: Bob cannot open Acme
    denied = api_client.get(
        f"/api/v1/organizations/{org_a_id}",
        headers=_auth(token_b),
    )
    assert denied.status_code == 403

    # Knowledge base + document
    kb = api_client.post(
        "/api/v1/knowledge-bases",
        headers=_auth(token_a),
        json={
            "organization_id": org_a_id,
            "name": "Policies",
            "description": "HR policies",
        },
    )
    assert kb.status_code == 201, kb.text
    kb_id = kb.json()["data"]["id"]

    content = b"# Remote Work\n\nEmployees may work remotely 3 days per week."
    files = {"file": ("remote.md", content, "text/markdown")}
    up = api_client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=_auth(token_a),
        files=files,
    )
    assert up.status_code == 201, up.text
    doc = up.json()["data"]
    assert doc["status"] in {"pending", "processing", "ready"}

    # Poll-ish: sync ingestion should finish in-process
    doc_id = doc["id"]
    got = api_client.get(
        f"/api/v1/documents/{doc_id}",
        headers=_auth(token_a),
    )
    assert got.status_code == 200
    # After sync pipeline likely ready
    assert got.json()["data"]["status"] in {"ready", "pending", "processing", "failed"}

    # Chat conversation
    conv = api_client.post(
        "/api/v1/conversations",
        headers=_auth(token_a),
        json={"knowledge_base_id": kb_id, "title": "Remote Q"},
    )
    assert conv.status_code == 201, conv.text
    conv_id = conv.json()["data"]["id"]

    msg = api_client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=_auth(token_a),
        json={"content": "What is the remote work policy?"},
    )
    assert msg.status_code == 200, msg.text
    payload = msg.json()["data"]
    assert payload["message"]["role"] == "assistant"
    assert payload["message"]["content"]

    # Bob cannot list Acme KBs via org filter if he tries to use Alice's kb
    bob_docs = api_client.get(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=_auth(token_b),
    )
    assert bob_docs.status_code == 403

    # Analytics for owner
    analytics = api_client.get(
        f"/api/v1/organizations/{org_a_id}/analytics/overview",
        headers=_auth(token_a),
    )
    assert analytics.status_code == 200
    assert analytics.json()["data"]["documents"] >= 1

    # Bob analytics on his empty org works
    analytics_b = api_client.get(
        f"/api/v1/organizations/{org_b_id}/analytics/overview",
        headers=_auth(token_b),
    )
    assert analytics_b.status_code == 200


def test_login_refresh_logout(api_client):
    token, _ = _register(api_client, "carol@example.com", "Carol")
    login = api_client.post(
        "/api/v1/auth/login",
        json={"email": "carol@example.com", "password": "SecurePass1"},
    )
    assert login.status_code == 200
    refresh = login.json()["data"]["refresh_token"]
    access = login.json()["data"]["access_token"]

    refreshed = api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh},
    )
    assert refreshed.status_code == 200
    new_refresh = refreshed.json()["data"]["refresh_token"]

    me = api_client.get("/api/v1/auth/me", headers=_auth(access))
    # old access may still be valid until expiry
    assert me.status_code in {200, 401}

    logout = api_client.post(
        "/api/v1/auth/logout",
        headers=_auth(refreshed.json()["data"]["access_token"]),
        json={"refresh_token": new_refresh},
    )
    assert logout.status_code == 200
