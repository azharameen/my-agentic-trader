# Testing Rules — tests/AGENTS.md

This directory houses the unit, integration, and regression test suites for
TrAId. All tests must run cleanly under `python -m pytest -q`.

## Core Testing Invariants

1. **Complete Test Isolation:**
   - Tests must never touch production databases or live operational records.
   - Use the `isolated_settings` autouse fixture in `conftest.py` which truncates
     test database tables and isolates universe caches in `tmp_path`.
2. **Settings Cache Invalidation:**
   - If any test mutates an environment variable or overrides a setting, it must
     call `get_settings.cache_clear()` before and after the test to prevent state
     leakage across test modules.
3. **No Unmocked External Network Calls:**
   - Never make live network requests to Yahoo Finance, Telegram Bot API, RSS
     feeds, or LLM providers during unit test execution.
   - Use `monkeypatch`, `pytest-mock`, or `responses` to mock HTTP and SDK
     boundaries deterministically.
4. **Invariant Assertion Standard:**
   - Every risk engine test must assert:
     - No float share quantities (quantities must be positive integers).
     - Degenerate ATR ($ATR \le 0$) is rejected deterministically.
     - Hard stop loss is strictly below entry for long setups.
     - Position size strictly adheres to the 1% portfolio risk rule.
   - Every graph test must assert:
     - Interrupt behavior halts execution at `human_approval`.
     - Invalid resume command values fail closed to `rejected`.
5. **Coverage & Regressions:**
   - Whenever fixing a bug or adding a feature, add both positive (happy path)
     and negative (failure, timeout, malformed data, fail-closed) test cases.
   - Aim to maintain minimum 80% test coverage across `app/`.
