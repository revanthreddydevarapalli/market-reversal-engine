"""GET /symbols -- the tracked universe, so the frontend can offer a
search/autocomplete instead of requiring an exact ticker to be typed."""

from __future__ import annotations

from fastapi import APIRouter

from src.config.universe import FULL_UNIVERSE, UniverseSymbol

router = APIRouter(tags=["symbols"])


@router.get("/symbols", response_model=list[UniverseSymbol])
def get_symbols() -> list[UniverseSymbol]:
    return FULL_UNIVERSE
