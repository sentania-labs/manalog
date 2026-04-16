"""Agent-facing endpoints: registration + match upload.

Bearer-token auth will be added in Phase 1.5. The upload endpoint uses
`get_current_agent` (header-sniffing stub) so the auth flow is wired
correctly even before real token validation exists.
"""
from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_agent
from app.models import AgentRegistration
from app.schemas import (
    AgentMatchUpload,
    AgentRegisterRequest,
    AgentRegisterResponse,
)

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post(
    "/register",
    response_model=AgentRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_agent(payload: AgentRegisterRequest) -> AgentRegisterResponse:
    """Register a new agent instance for this user.

    TODO(phase-1.5): verify username/password, create AgentRegistration row,
    hash + store the api_token, return the plaintext token (shown once).
    Current behavior is a stub that returns a well-formed response so the
    agent's registration flow can be exercised end-to-end.
    """
    _ = payload  # username/password validation happens in Phase 1.5
    return AgentRegisterResponse(
        agent_id=uuid.uuid4(),
        api_token=secrets.token_urlsafe(32),
    )


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_match(
    payload: AgentMatchUpload,
    agent: AgentRegistration = Depends(get_current_agent),
) -> dict:
    """Accept a match result from an agent.

    TODO(phase-1.5): upsert match row keyed on (user_id, mtgo_match_id),
    create games + plays, bump agent.last_seen.
    """
    _ = agent  # will scope the upsert once real auth lands
    return {
        "status": "queued",
        "mtgo_match_id": payload.match.mtgo_match_id,
    }
