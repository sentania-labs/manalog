"""API dependencies.

Auth middleware is Phase 1.5 — for now `get_current_user` returns a
hardcoded dev User so routes can be built and exercised. Do NOT ship this
to production. The stub is intentionally loud: it does not touch the DB
and returns a synthetic object so anything that tries to persist against
it will fail fast.

`get_current_agent` mirrors the pattern for agent-authenticated routes:
it extracts a Bearer token from the Authorization header (accepting
missing tokens in stub mode) and returns a synthetic AgentRegistration.
Phase 1.5 will replace this with a real token → AgentRegistration
lookup.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import Header

from app.models import AgentRegistration, User

DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEV_AGENT_ID = uuid.UUID("00000000-0000-0000-0000-0000000000a1")


def get_current_user() -> User:
    user = User(
        id=DEV_USER_ID,
        username="dev",
        email="dev@localhost",
        hashed_password="!",  # noqa: S105 — stub, not persisted
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    return user


def get_current_agent(
    authorization: str | None = Header(default=None),
) -> AgentRegistration:
    """Resolve the calling agent from the Authorization header.

    TODO(phase-1.5): look up api_token_hash in agent_registrations,
    reject if missing/revoked, bump last_seen.
    """
    _token = authorization.split(" ", 1)[1] if authorization and " " in authorization else None
    return AgentRegistration(
        id=DEV_AGENT_ID,
        user_id=DEV_USER_ID,
        agent_id=DEV_AGENT_ID,
        machine_name="dev-agent",
        platform="stub",
        api_token_hash="!",  # noqa: S105 — stub, not persisted
        last_seen=None,
        created_at=datetime.now(timezone.utc),
        revoked_at=None,
    )
