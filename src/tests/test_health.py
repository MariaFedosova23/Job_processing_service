import pytest


@pytest.mark.integration
async def test_readiness_check_ok(client):
    resp = await client.get("/health/ready")

    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["status"] == "ready"
    assert body["dependencies"]["postgres"]["status"] == "ok"
    assert body["dependencies"]["redis"]["status"] == "ok"