from __future__ import annotations

from datetime import datetime, timezone

from app import outbox
from app.state import ProposalCard


def test_enqueue_serializes_pydantic_payload_as_mapping():
    card = ProposalCard(
        symbol="TITAN",
        entry_price=100.0,
        soft_stop=97.0,
        hard_stop=95.0,
        target_price=110.0,
        quantity=1,
        risk_amount=5.0,
        risk_to_reward=2.0,
        thesis="test",
        catalyst_type="GENERAL_MARKET",
        proposed_at=datetime.now(timezone.utc),
    )
    outbox.enqueue("TRADE_PROPOSAL", "chat", card)

    captured = []
    outbox.deliver_pending(lambda recipient, payload: captured.append(payload) or True)

    assert captured[0]["symbol"] == "TITAN"


def test_delivery_unwraps_legacy_double_encoded_mapping():
    outbox.init_db()
    with outbox.sqlite3.connect(outbox._db_path()) as conn:
        conn.execute(
            "INSERT INTO notification_outbox "
            "(event_id, event_type, recipient, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            ("legacy", "TRADE_PROPOSAL", "chat", '"{\\"symbol\\": \\"TITAN\\"}"', "2026-01-01T00:00:00+00:00"),
        )
        conn.commit()

    captured = []
    outbox.deliver_pending(lambda recipient, payload: captured.append(payload) or True)

    assert captured == [{"symbol": "TITAN"}]


def test_delivery_quarantines_unrecoverable_legacy_payload():
    outbox.init_db()
    with outbox.sqlite3.connect(outbox._db_path()) as conn:
        conn.execute(
            "INSERT INTO notification_outbox "
            "(event_id, event_type, recipient, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            ("poison", "TRADE_PROPOSAL", "chat", "symbol='TITAN'", "2026-01-01T00:00:00+00:00"),
        )
        conn.commit()

    assert outbox.deliver_pending(lambda recipient, payload: True) == 0
    with outbox.sqlite3.connect(outbox._db_path()) as conn:
        row = conn.execute(
            "SELECT quarantined_at, error FROM notification_outbox WHERE event_id = ?",
            ("poison",),
        ).fetchone()
    assert row[0] is not None
    assert "Expecting value" in row[1]
    assert outbox.pending() == []
