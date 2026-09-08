"""GET /health -- liveness/readiness probe.

Phase 1 keeps this endpoint intentionally simple (app is up, and it can
report the environment it's running in). A database connectivity check
is deliberately deferred: once real ORM models exist we can do a cheap
`SELECT 1` here, but wiring that in before there is anything in the
schema would just add noise.
"""

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

from src.config.settings import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    time_utc: datetime


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.app_env.value,
        time_utc=datetime.now(UTC),
    )
