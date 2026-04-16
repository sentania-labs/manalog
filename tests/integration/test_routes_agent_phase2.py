"""Phase 2 behavior tests for /api/v1/agent/* — register returns a valid
agent_id/token, upload accepts a well-formed payload and returns 202
with a known response shape.
"""
from __future__ import annotations

import uuid


async def test_register_returns_agent_id(client) -> None:
    payload = {
        "username": "testuser",
        "password": "hunter2",
        "machine_name": "test-pc",
        "platform": "windows",
    }
    resp = await client.post("/api/v1/agent/register", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert "agent_id" in body
    assert "api_token" in body
    # agent_id must be a valid UUID
    uuid.UUID(body["agent_id"])
    assert isinstance(body["api_token"], str)
    assert len(body["api_token"]) > 0


def _minimal_upload_payload(mtgo_match_id: str = "MTGO-PHASE2-1") -> dict:
    return {
        "agent_id": str(uuid.uuid4()),
        "match": {
            "mtgo_match_id": mtgo_match_id,
            "format": "modern",
            "match_type": "league",
            "result": "win",
            "my_wins": 2,
            "opponent_wins": 1,
        },
    }


async def test_upload_returns_202(client) -> None:
    resp = await client.post("/api/v1/agent/upload", json=_minimal_upload_payload())
    assert resp.status_code == 202


async def test_upload_response_shape(client) -> None:
    payload = _minimal_upload_payload("MTGO-PHASE2-SHAPE")
    resp = await client.post("/api/v1/agent/upload", json=payload)
    assert resp.status_code == 202
    body = resp.json()
    assert "status" in body
    assert "mtgo_match_id" in body
    assert body["mtgo_match_id"] == "MTGO-PHASE2-SHAPE"
