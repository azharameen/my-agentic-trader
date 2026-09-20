from __future__ import annotations

from app import profile, store


def test_operator_profile_round_trips_and_rejects_unknown_fields():
    profile.save({"horizon": "swing", "risk_preference": "moderate"})

    assert profile.load() == {"horizon": "swing", "risk_preference": "moderate"}


def test_operator_profile_updates_existing_values():
    profile.save({"horizon": "swing", "capital": 100000})
    profile.save({"horizon": "longer-term"})

    assert profile.load() == {"horizon": "longer-term", "capital": 100000}


def test_operator_profile_is_backed_by_the_shared_langgraph_store():
    profile.save({"horizon": "swing"})

    item = store.get_store().get(("operator_profile",), "default")

    assert item is not None
    assert item.value == {"horizon": "swing"}
