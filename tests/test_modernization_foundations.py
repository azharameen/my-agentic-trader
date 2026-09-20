from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app import evidence, executor, regime, risk
from app.risk import calculate_risk
from config.settings import get_settings


def test_regime_blocks_new_entries_when_vix_is_extreme():
    result = regime.evaluate_regime(vix=26.0, nifty_close=100.0, nifty_ema_50=105.0)

    assert result.allow_new_entries is False
    assert result.risk_multiplier == 0.0
    assert "INDIA_VIX" in result.reasons


def test_regime_halves_risk_when_vix_is_elevated():
    result = regime.evaluate_regime(vix=23.0, nifty_close=110.0, nifty_ema_50=105.0)

    assert result.allow_new_entries is True
    assert result.risk_multiplier == 0.5
    assert result.reasons == ["INDIA_VIX_ELEVATED"]


def test_elevated_regime_scales_deterministic_risk_budget():
    normal = calculate_risk("NORMAL", entry_price=100.0, atr=2.0, portfolio_capital=100_000)
    reduced = calculate_risk(
        "REDUCED", entry_price=100.0, atr=2.0, portfolio_capital=100_000,
        risk_multiplier=0.5,
    )

    assert normal is not None and reduced is not None
    assert reduced.risk_amount == normal.risk_amount / 2
    assert reduced.quantity == normal.quantity // 2


def test_regime_blocks_when_nifty_is_below_ema():
    result = regime.evaluate_regime(vix=15.0, nifty_close=99.0, nifty_ema_50=100.0)

    assert result.allow_new_entries is False
    assert result.risk_multiplier == 0.0
    assert result.reasons == ["NIFTY_BELOW_EMA_50"]


def test_market_safety_rejects_circuit_and_surveillance_flags():
    assert risk.market_safety_rejection(circuit_locked=True) == "CIRCUIT_LOCKED"
    assert risk.market_safety_rejection(asm_gsm_flag=True) == "ASM_GSM_SURVEILLANCE"
    assert risk.market_safety_rejection() is None


def test_delivery_costs_are_deterministic():
    costs = risk.calculate_delivery_costs(buy_value=100_000.0, sell_value=110_000.0)

    assert costs.stt == 210.0
    assert costs.stamp_duty == 15.0
    assert costs.total > costs.stt


def test_paper_close_records_net_pnl_after_delivery_costs():
    proposal = calculate_risk("COSTTEST", entry_price=100.0, atr=2.0, portfolio_capital=100_000)
    assert proposal is not None
    opened = executor.record_open_trade(
        proposal=proposal,
        rsi=30.0,
        ema_200=90.0,
        atr=2.0,
        thesis="test",
        human_decision="APPROVED",
    )

    closed = executor.close_trade(opened["trade_id"], exit_price=110.0)

    assert closed["gross_pnl"] > closed["realized_pnl"]
    assert closed["transaction_costs"]["total"] > 0


def test_evidence_snapshot_rejects_missing_and_conflicting_items():
    for status in ("MISSING", "CONFLICT"):
        snapshot = evidence.EvidenceSnapshot(
            items=[
                evidence.EvidenceItem(
                    kind="NEWS",
                    payload={"headline": "x"},
                    provenance=evidence.Provenance(
                        source="test",
                        fetched_at=datetime.now(timezone.utc),
                        validation_status=status,
                    ),
                )
            ]
        )
        with pytest.raises(ValueError, match=f"Evidence is {status}"):
            evidence.validate_snapshot(snapshot)


def test_evidence_snapshot_rejects_stale_items():
    snapshot = evidence.EvidenceSnapshot(
        items=[
            evidence.EvidenceItem(
                kind="MARKET",
                payload={"close": 100},
                provenance=evidence.Provenance(
                    source="test",
                    fetched_at=datetime.now(timezone.utc) - timedelta(minutes=10),
                ),
            )
        ]
    )

    with pytest.raises(ValueError, match="Evidence is stale"):
        evidence.validate_snapshot(snapshot, max_age_seconds=60)


def test_evidence_snapshot_uses_configured_default_age(monkeypatch):
    monkeypatch.setenv("EVIDENCE_MAX_AGE_SECONDS", "60")
    get_settings.cache_clear()
    snapshot = evidence.EvidenceSnapshot(
        items=[
            evidence.EvidenceItem(
                kind="MARKET",
                payload={"close": 100},
                provenance=evidence.Provenance(
                    source="test",
                    fetched_at=datetime.now(timezone.utc) - timedelta(minutes=2),
                ),
            )
        ]
    )

    with pytest.raises(ValueError, match="Evidence is stale"):
        evidence.validate_snapshot(snapshot)
    get_settings.cache_clear()
