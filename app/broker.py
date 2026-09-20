"""Broker adapter boundary for paper execution and a future real broker."""

from __future__ import annotations

from typing import Protocol

from app.state import TradeProposal


class BrokerAdapter(Protocol):
    """Minimal execution contract; no LLM or strategy code depends on a broker."""

    def open_trade(
        self,
        proposal: TradeProposal,
        rsi: float = 0.0,
        ema_200: float = 0.0,
        atr: float = 0.0,
        thesis: str = "",
        human_decision: str = "",
        news_headlines: list[str] | None = None,
        evidence_snapshot_id: str | None = None,
        strategy_name: str | None = None,
        market_regime: str | None = None,
        catalyst_type: str | None = None,
        source_set: list[str] | None = None,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        cache_hits: list[str] | None = None,
    ) -> dict:
        """Open a position and return an auditable execution record."""

    def close_trade(self, trade_id: str, exit_price: float, mistake_category: str | None = None) -> dict:
        """Close a position and return an auditable execution record."""


class PaperBroker:
    """Adapter over the PostgreSQL paper-execution implementation."""

    def open_trade(
        self,
        proposal: TradeProposal,
        rsi: float = 0.0,
        ema_200: float = 0.0,
        atr: float = 0.0,
        thesis: str = "",
        human_decision: str = "",
        news_headlines: list[str] | None = None,
        evidence_snapshot_id: str | None = None,
        strategy_name: str | None = None,
        market_regime: str | None = None,
        catalyst_type: str | None = None,
        source_set: list[str] | None = None,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        cache_hits: list[str] | None = None,
    ) -> dict:
        from app import executor

        return executor.record_open_trade(
            proposal,
            rsi,
            ema_200,
            atr,
            thesis,
            human_decision,
            news_headlines,
            evidence_snapshot_id,
            strategy_name,
            market_regime,
            catalyst_type,
            source_set,
            llm_provider,
            llm_model,
            cache_hits,
        )

    def close_trade(self, trade_id: str, exit_price: float, mistake_category: str | None = None) -> dict:
        from app import executor

        return executor.close_trade(trade_id, exit_price, mistake_category)


class LiveBroker:
    """Explicit fail-closed placeholder until a broker is reviewed and wired."""

    def open_trade(
        self,
        proposal: TradeProposal,
        rsi: float = 0.0,
        ema_200: float = 0.0,
        atr: float = 0.0,
        thesis: str = "",
        human_decision: str = "",
        news_headlines: list[str] | None = None,
        evidence_snapshot_id: str | None = None,
        strategy_name: str | None = None,
        market_regime: str | None = None,
        catalyst_type: str | None = None,
        source_set: list[str] | None = None,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        cache_hits: list[str] | None = None,
    ) -> dict:
        raise RuntimeError("LIVE order routing is not implemented.")

    def close_trade(self, trade_id: str, exit_price: float, mistake_category: str | None = None) -> dict:
        raise RuntimeError("LIVE order routing is not implemented.")


def get_broker(mode: str) -> BrokerAdapter:
    """Resolve the adapter without ever silently enabling live trading."""
    if mode == "PAPER_TRADING":
        return PaperBroker()
    if mode == "LIVE":
        return LiveBroker()
    raise ValueError(f"Unsupported trading mode: {mode}")
