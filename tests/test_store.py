from __future__ import annotations

from app import store


def test_store_round_trips_a_namespaced_value():
    store.reset()
    shared = store.get_store()

    shared.put(("operator_profile",), "default", {"horizon": "swing"})
    item = shared.get(("operator_profile",), "default")

    assert item is not None
    assert item.value == {"horizon": "swing"}


def test_store_reset_clears_shared_instance():
    store.reset()
    assert store.current_connection() is None
