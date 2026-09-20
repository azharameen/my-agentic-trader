"""Operator-controlled profile stored in the shared LangGraph long-term store.

Uses the native LangGraph `BaseStore` abstraction (namespaced key/value JSON
documents) instead of an ad hoc table, so the operator profile is a real
long-term-memory namespace: reusable by the chat agent, inspectable the same
way as any other store entry, and portable if a future ADR ever swaps the
backing store implementation.
"""

from __future__ import annotations

from app import store

_NAMESPACE = ("operator_profile",)
_KEY = "default"

_FIELDS = {
    "horizon",
    "capital",
    "exclusions",
    "risk_preference",
    "notification_preferences",
}


def load() -> dict:
    item = store.get_store().get(_NAMESPACE, _KEY)
    return dict(item.value) if item else {}


def save(values: dict) -> dict:
    current = load()
    current.update({key: value for key, value in values.items() if key in _FIELDS})
    store.get_store().put(_NAMESPACE, _KEY, current)
    return current
