"""Broker adapter boundary for paper execution and a future real broker."""

from __future__ import annotations

from typing import Protocol

from app.state import TradeProposal


class BrokerAdapter(Protocol):
    """Minimal execution contract; no LLM or strategy code depends on a broker."""

    def open_trade(self, proposal: TradeProposal, **metadata: object) -> dict:
        """Open a position and return an auditable execution record."""

    def close_trade(self, trade_id: str, exit_price: float, **metadata: object) -> dict:
        """Close a position and return an auditable execution record."""


class PaperBroker:
    """Adapter over the existing SQLite paper-execution implementation."""

    def open_trade(self, proposal: TradeProposal, **metadata: object) -> dict:
        from app import executor

        return executor.record_open_trade(proposal=proposal, **metadata)

    def close_trade(self, trade_id: str, exit_price: float, **metadata: object) -> dict:
        from app import executor

        return executor.close_trade(trade_id=trade_id, exit_price=exit_price, **metadata)


class LiveBroker:
    """Explicit fail-closed placeholder until a broker is reviewed and wired."""

    def open_trade(self, proposal: TradeProposal, **metadata: object) -> dict:
        raise RuntimeError("LIVE order routing is not implemented.")

    def close_trade(self, trade_id: str, exit_price: float, **metadata: object) -> dict:
        raise RuntimeError("LIVE order routing is not implemented.")


def get_broker(mode: str) -> BrokerAdapter:
    """Resolve the adapter without ever silently enabling live trading."""
    if mode == "PAPER_TRADING":
        return PaperBroker()
    if mode == "LIVE":
        return LiveBroker()
    raise ValueError(f"Unsupported trading mode: {mode}")
