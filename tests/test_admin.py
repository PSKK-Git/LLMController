import pytest


@pytest.mark.asyncio
async def test_create_org_requires_admin_token(client):
    resp = await client.post("/admin/organizations", json={"name": "Acme"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_org_and_key(client, monkeypatch):
    monkeypatch.setattr("llmcontroller.config.settings.admin_token", "secret")
    headers = {"X-Admin-Token": "secret"}

    org_resp = await client.post("/admin/organizations", json={"name": "Acme"}, headers=headers)
    assert org_resp.status_code == 200
    org_id = org_resp.json()["org_id"]

    key_resp = await client.post(
        "/admin/api-keys", json={"org_id": org_id, "name": "prod"}, headers=headers
    )
    assert key_resp.status_code == 200
    body = key_resp.json()
    assert body["api_key"].startswith("sk-")
    assert "api_key_id" in body
