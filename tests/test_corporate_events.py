from __future__ import annotations

from datetime import date

from app import corporate_events, graph


def _event(event_type: corporate_events.CorporateEventType, event_date: date):
    return corporate_events.CorporateEvent(
        symbol="RELIANCE",
        event_type=event_type,
        event_date=event_date,
        title="Quarterly event",
        source="test",
    )


def test_duplicate_events_are_removed_stably():
    event = _event(corporate_events.CorporateEventType.EARNINGS, date(2026, 9, 20))

    assert corporate_events.deduplicate_events([event, event]) == [event]


def test_identity_matching_uses_symbol_or_isin_only():
    event = _event(corporate_events.CorporateEventType.EARNINGS, date(2026, 9, 20))
    event.isin = "INE123"

    assert corporate_events.events_for_identity([event], symbol="OTHER", isin="INE123") == [event]
    assert corporate_events.events_for_identity([event], symbol="OTHER", isin="INE999") == []


def test_malformed_rows_do_not_abort_collection():
    rows = [
        {"symbol": "RELIANCE"},
        {
            "symbol": "RELIANCE",
            "event_type": "EARNINGS",
            "event_date": "2026-09-20",
            "title": "Results",
            "source": "test",
        },
    ]

    events = corporate_events.parse_event_rows(rows)

    assert len(events) == 1


def test_earnings_inside_ten_day_window_blocks():
    event = _event(corporate_events.CorporateEventType.EARNINGS, date(2026, 9, 25))

    assert (
        corporate_events.blackout_reason(
            [event], "RELIANCE", as_of=date(2026, 9, 18), holding_days=10
        )
        == "CORPORATE_EVENT_BLACKOUT:EARNINGS"
    )


def test_event_after_window_does_not_block():
    event = _event(corporate_events.CorporateEventType.EARNINGS, date(2026, 9, 29))

    assert corporate_events.blackout_reason(
        [event], "RELIANCE", as_of=date(2026, 9, 18), holding_days=10
    ) is None


def test_dividend_inside_window_is_evidence_but_not_hard_blackout():
    event = _event(corporate_events.CorporateEventType.DIVIDEND, date(2026, 9, 20))

    assert corporate_events.blackout_reason(
        [event], "RELIANCE", as_of=date(2026, 9, 18), holding_days=10
    ) is None
    assert corporate_events.to_evidence_items([event])[0].kind == "CORPORATE_EVENT"


def test_graph_rejects_earnings_blackout(monkeypatch):
    event = _event(corporate_events.CorporateEventType.EARNINGS, date.today())

    result = graph.run_symbol(
        "RELIANCE",
        snapshot={"daily_close": 100.0, "rsi": 30.0, "ema_200": 90.0, "atr": 2.0},
        events=[event],
    )

    assert result["execution_details"]["status"] == "REJECTED"
