from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from src.config.strategy_params import StrategyParameters
from src.database.base import Base
from src.database.session import build_engine
from src.services.journal_service import get_journal_entries, log_reached_zones
from tests.integration.test_reversal_service_e2e import FakeOHLCVProvider, FakeOptionsProvider
from src.services.reversal_service import analyze_symbol


def make_test_db_session():
    engine = build_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_log_reached_zones_persists_entries():
    db = make_test_db_session()
    params = StrategyParameters(bin_count=30, hvn_lvn_window=2, hvn_lvn_min_prominence_pct=0.1)
    analysis = analyze_symbol("NVDA", FakeOHLCVProvider(), FakeOptionsProvider(), params)

    new_entries = log_reached_zones(db, analysis, params)

    assert len(new_entries) >= 1
    stored = get_journal_entries(db, symbol="NVDA")
    assert len(stored) == len(new_entries)
    assert stored[0].symbol == "NVDA"
    assert stored[0].status == "REACHED"


def test_log_reached_zones_dedups_within_window():
    db = make_test_db_session()
    params = StrategyParameters(bin_count=30, hvn_lvn_window=2, hvn_lvn_min_prominence_pct=0.1)
    analysis = analyze_symbol("NVDA", FakeOHLCVProvider(), FakeOptionsProvider(), params)

    first_pass = log_reached_zones(db, analysis, params)
    second_pass = log_reached_zones(db, analysis, params)

    assert len(first_pass) >= 1
    assert len(second_pass) == 0  # deduplicated, same zone still active

    stored = get_journal_entries(db, symbol="NVDA")
    assert len(stored) == len(first_pass)


def test_get_journal_entries_filters_by_symbol():
    db = make_test_db_session()
    params = StrategyParameters(bin_count=30, hvn_lvn_window=2, hvn_lvn_min_prominence_pct=0.1)
    analysis = analyze_symbol("NVDA", FakeOHLCVProvider(), FakeOptionsProvider(), params)
    log_reached_zones(db, analysis, params)

    assert len(get_journal_entries(db, symbol="NVDA")) >= 1
    assert len(get_journal_entries(db, symbol="AAPL")) == 0
