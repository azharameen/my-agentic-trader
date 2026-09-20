# Configuration Rules — config/AGENTS.md

This directory houses application settings, Pydantic configuration models, and
static seed files for TrAId.

## Core Configuration Invariants

1. **Singleton Access Pattern:**
   - Always access configuration via `get_settings()` from `config/settings.py`.
   - Never instantiate `Settings()` directly in application code.
   - `get_settings()` is cached via `@lru_cache`. In tests, call
     `get_settings.cache_clear()` after modifying environment variables.
2. **SecretStr for Credentials:**
   - All API keys, tokens, database passwords, and connection URLs with
     credentials must be typed as `pydantic.SecretStr`.
   - Never use plain `str` for sensitive credentials to prevent leaks in logs,
     stack traces, or serialization dumps.
3. **Twelve-Factor Configuration:**
   - Configuration is strictly read from environment variables or `.env`.
   - Application code must never dynamically rewrite or mutate `.env` on disk
     at runtime.
4. **Environment Example Sync:**
   - Every new setting added to `config/settings.py` must have a corresponding
     entry and explanatory comment in `.env.example`.
5. **Universe Seed Immutability:**
   - `config/universe/nifty100_seed.csv` is committed as a permanent offline
     fallback baseline. Code must never write to or delete this file.
   - Dynamic caches belong strictly in `data/universe/`.
