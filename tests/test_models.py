from __future__ import annotations

from datetime import datetime, timezone

from pydantic import SecretStr

from app.evidence import content_hash
from app.models import (
    DictCompatibleModel,
    ExecutionResult,
    ScanResult,
    TechnicalSnapshot,
    TradeRecord,
)
from config.settings import get_settings


def test_dict_compatible_model_access():
    class DummyModel(DictCompatibleModel):
        name: str
        value: int

    m = DummyModel(name="test", value=42)
    assert m["name"] == "test"
    assert m["value"] == 42
    assert m.get("name") == "test"
    assert m.get("nonexistent", "fallback") == "fallback"
    assert "name" in m
    assert "other" not in m


def test_technical_snapshot_instantiation():
    snap = TechnicalSnapshot(
        symbol="INFY",
        daily_close=1850.50,
        rsi=38.5,
        ema_200=1720.0,
        atr=25.4,
        volume=1200000.0,
        avg_volume_20=1000000.0,
        qualifies=True,
    )
    assert snap.symbol == "INFY"
    assert snap["daily_close"] == 1850.50
    assert snap.qualifies is True
    assert snap.data_source == "yfinance"
    assert snap.cache_hit is False

    dumped = snap.model_dump()
    assert dumped["symbol"] == "INFY"
    assert dumped["rsi"] == 38.5


def test_execution_result_instantiation():
    res = ExecutionResult(
        trade_id="abc12345",
        symbol="TCS",
        fill_price=3501.75,
        quantity=28,
    )
    assert res.trade_id == "abc12345"
    assert res.status == "OPEN_PAPER"
    assert res["fill_price"] == 3501.75
    assert res.slippage_pct == 0.05
    assert isinstance(res.filled_at, datetime)


def test_trade_record_instantiation():
    record = TradeRecord(
        trade_id="trade-999",
        timestamp=datetime.now(timezone.utc),
        symbol="RELIANCE",
        entry_price=2900.0,
        soft_stop=2850.0,
        hard_stop=2800.0,
        target_price=3100.0,
        quantity=10,
        status="OPEN_PAPER",
        rsi=41.2,
    )
    assert record.symbol == "RELIANCE"
    assert record.quantity == 10
    assert record["soft_stop"] == 2850.0
    assert record.status == "OPEN_PAPER"


def test_scan_result_instantiation():
    scan = ScanResult(
        total_symbols=100,
        qualified_symbols=["INFY", "TCS", "HCLTECH"],
        proposals_generated=2,
        vetoed_by_regime=False,
    )
    assert scan.total_symbols == 100
    assert len(scan.qualified_symbols) == 3
    assert scan.proposals_generated == 2
    assert not scan.vetoed_by_regime


def test_secret_str_masking_in_settings(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-test-openai-key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF-SECRET-TOKEN")
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2-pt-secret-key")
    get_settings.cache_clear()

    settings = get_settings()
    assert isinstance(settings.OPENAI_API_KEY, SecretStr)
    assert isinstance(settings.TELEGRAM_BOT_TOKEN, SecretStr)
    assert isinstance(settings.LANGSMITH_API_KEY, SecretStr)

    assert settings.OPENAI_API_KEY.get_secret_value() == "sk-secret-test-openai-key"
    assert settings.TELEGRAM_BOT_TOKEN.get_secret_value() == "123456:ABC-DEF-SECRET-TOKEN"
    assert settings.LANGSMITH_API_KEY.get_secret_value() == "lsv2-pt-secret-key"

    # Verify that printing or stringifying settings masks the secrets
    repr_str = repr(settings)
    assert "sk-secret-test-openai-key" not in repr_str
    assert "ABC-DEF-SECRET-TOKEN" not in repr_str
    assert "lsv2-pt-secret-key" not in repr_str

    get_settings.cache_clear()


def test_screener_deterministic_content_hash():
    dict1 = {"symbol": "INFY", "history_period": "1y", "rsi_max": 42.0}
    dict2 = {"rsi_max": 42.0, "symbol": "INFY", "history_period": "1y"}
    assert content_hash(dict1) == content_hash(dict2)
