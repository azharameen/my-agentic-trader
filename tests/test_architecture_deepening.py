from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from app import checkpoint, market_data, screener, state, universe
from config.settings import get_settings


def _ohlcv() -> pd.DataFrame:
    prices = pd.Series(
        [100 + ((index % 20) - 10) + index * 0.1 for index in range(260)],
        dtype=float,
    )
    return pd.DataFrame(
        {
            "Open": prices,
            "High": prices + 1,
            "Low": prices - 1,
            "Close": prices,
            "Volume": 1_000_000.0,
        }
    )


def test_market_data_result_preserves_source_provenance():
    result = market_data.MarketDataResult(
        frame=_ohlcv(),
        source="test",
        fetched_at=datetime.now(timezone.utc),
    )

    assert result.source == "test"
    assert result.frame is not None
    assert result.fetched_at.tzinfo is not None


def test_screener_uses_one_history_loader_for_single_and_universe_paths(monkeypatch):
    monkeypatch.setenv("RESEARCH_CACHE_ENABLED", "false")
    get_settings.cache_clear()
    calls: list[str] = []

    def fake_history(symbol: str, period: str) -> market_data.MarketDataResult:
        calls.append(symbol)
        return market_data.MarketDataResult(
            frame=_ohlcv(),
            source="test",
            fetched_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(screener, "_load_history", fake_history)
    monkeypatch.setattr(screener, "_passes_setup_filter", lambda row: True)

    single = screener.get_symbol_snapshot("TEST")
    many = screener.scan_nifty_universe(["TEST"])

    assert single is not None
    assert many
    assert calls == ["TEST.NS", "TEST.NS"]
    assert single["data_source"] == "test"
    assert many[0]["data_source"] == "test"


def test_checkpoint_reset_clears_shared_connection():
    checkpoint.reset()
    assert checkpoint.current_connection() is None


def test_proposal_card_is_validated_once():
    card = state.ProposalCard(
        symbol="TEST",
        entry_price=100.0,
        soft_stop=97.0,
        hard_stop=95.0,
        target_price=110.0,
        quantity=10,
        risk_amount=100.0,
        risk_to_reward=2.0,
        thesis="Routine pullback.",
        catalyst_type="EARNINGS_NOISE",
        proposed_at=datetime.now(timezone.utc).isoformat(),
    )

    assert state.ProposalCard.model_validate(card.model_dump()) == card


def test_universe_resolution_reuses_rows_until_refresh(monkeypatch, tmp_path):
    universe.clear_cache()
    path = tmp_path / "nifty100.csv"
    monkeypatch.setenv("UNIVERSE_CACHE_PATH", str(path))
    universe.get_settings.cache_clear()

    rows = universe._parse_csv(
        "Company Name,Industry,Symbol,Series,ISIN Code\n"
        + "\n".join(f"Company {i},Sector,SYM{i},EQ,INE{i}" for i in range(100))
    )
    monkeypatch.setattr(universe, "fetch_live_universe", lambda: rows)

    first = universe.get_symbol_company_names()
    second = universe.get_symbol_company_names()

    assert first == second
    assert universe.cache_size() == 1
