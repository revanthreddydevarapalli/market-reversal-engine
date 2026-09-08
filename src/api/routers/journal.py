"""GET /journal -- read back logged reached-zone entries. Writing to the
journal happens as a side effect of GET /levels/{symbol} (see
api/routers/levels.py), not through a separate write endpoint, since
v1-lite has no concept of a user manually opening/closing a position
yet -- that's the next layer of the trade engine."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.schemas.journal import JournalEntryResponse
from src.services.journal_service import get_journal_entries

router = APIRouter(tags=["journal"])


@router.get("/journal", response_model=list[JournalEntryResponse])
def list_journal_entries(
    symbol: str | None = Query(default=None, description="Filter to one symbol"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[JournalEntryResponse]:
    entries = get_journal_entries(db, symbol=symbol, limit=limit)
    return [JournalEntryResponse.model_validate(e) for e in entries]
