# AGENTS.md — NIFTY 100 Swing Trading Research Assistant

Local-first, containerized decision-support system: deterministic multi-strategy screening → sequential multi-agent qualitative research filter (Bear Critic, Bull Analyst, Synthesizer via native LangChain providers) → deterministic risk gates → human approval via Telegram → paper execution → PostgreSQL audit (ADR-023).

**Read first:** [README.md](README.md) (setup and CLI), then the canonical
documentation under [`docs/`](docs/): [architecture](docs/architecture.md),
[PRD](docs/prd.md), [references](docs/reference.md), [architecture decisions](docs/architecture-decisions.md),
and [tasks](docs/tasks.md). The root `ARCHITECTURE.md` is only a compatibility
link. Do not duplicate canonical documentation here.

## Systematic SDLC & Agentic Governance

All development follows the formal governance lifecycle in [`docs/sdlc-process.md`](docs/sdlc-process.md):

- **Canonical Documentation First:** Treat `docs/` as the single source of truth for product scope, architecture, sources, decisions, and tasks.
- **Task Lifecycle:** Tasks move through `backlog` → `discuss` → `todo` → `active` → `onhold` → `inreview` → `done` (or `deferred`).
- **Strict SDLC Gates:**
  1. *Gate 1 (Planning):* Tasks move to `todo` only when scoped with accepted ADRs and full nested hierarchy (Task → Sub-Tasks → Milestones → Checklists).
  2. *Gate 2 (Implementation):* Maximum 1–2 `active` tasks at a time. Never start coding without meeting entry criteria.
  3. *Gate 3 (Verification):* Move to `inreview` only when all checklists are `[x]`, `python -m pytest -q` passes (100%), and `ruff`/`mypy` checks pass.
  4. *Gate 4 (Completion & Container Build):* Move to `done` only after synchronizing `prd.md`, `architecture.md`, `reference.md`, building frontend assets (`cd frontend && npm run build`), and building Docker containers (`docker compose build` / `docker compose up --build -d`) so that the latest live app is running and accessible.
- **Folder-Level Rule Enforcement:** Specialized subfolder instructions apply:
  - [`app/AGENTS.md`](app/AGENTS.md): Pure Python risk math, fail-closed handlers, typed models, secret masking, and post-task Docker build.
  - [`tests/AGENTS.md`](tests/AGENTS.md): `tmp_path` isolation, external network mocking, deterministic assertions.
  - [`docs/AGENTS.md`](docs/AGENTS.md): Canonical documentation maintenance, ADR requirements, task ledger formatting.
  - [`config/AGENTS.md`](config/AGENTS.md): `get_settings()` singleton, `SecretStr` for credentials, `.env.example` synchrony.

## Commands

```bash
python -m app.main scan                         # one-shot: scan NIFTY 100, push proposals to Telegram
python -m app.main run <SYMBOL>                 # run a single symbol through the graph (testing)
python -m app.main refresh-universe             # force a live refresh of the NIFTY 100 constituent list
python -m app.main evaluate                     # report paper trading performance against NIFTY 100 benchmark
python -m app.main serve                        # start scheduler + Telegram bot (long-running)
python -m app.main dashboard                    # start Visual Analytics Web Dashboard (FastAPI + SPA)
docker compose up --build                       # three services (postgres sidecar + trading-engine + dashboard)
pytest -q                                       # unit tests (risk, screener, universe, graph, monitor)
```

**Telegram is the complete control plane** — no web UI/port exists. In the running bot: `/scan` (universe scan), `/run SYMBOL` (single symbol), `/trades` (audit log), `/pending` (proposals awaiting approval), `/performance` (alpha vs benchmark & metrics), Approve/Reject buttons on proposal cards, and free-text questions routed to the conversational research agent (`app/chat_agent.py`, a ReAct agent that is **read/trigger-only** — it can never approve/reject a trade). The CLI `scan`/`run` do the same via `app/pipeline.py` (shared with the bot — keep them in sync).

- Python 3.11+, plain `pip install -r requirements.txt` (no pyproject/Makefile).
- `pytest -q` runs the suite under `tests/`. Call `get_settings.cache_clear()` after mutating env vars in a test.

## Hard invariants — do not break

- **LLM never touches numbers.** Qualitative agents (Bear, Bull, Synthesizer) only classify the *nature* and confidence of a setup via structured Pydantic models. All prices/stops/sizes come from `risk.py` (pure math). Never add LLM output to `TradeProposal`.
- **Fail-closed everywhere.** LLM errors/missing API key → conservative fallback → trade rejected. Per-symbol screener errors are caught and skipped. Keep broad `except` + `# noqa: BLE001` markers where they exist — they are intentional.
- **Live trading is blocked.** `executor.record_open_trade` raises `RuntimeError` when `TRADING_MODE == "LIVE"`. Paper trading is the only supported mode (ADR-002).
- **Audit everything.** Every decision state goes to `trade_audit_log` in PostgreSQL (`trader_db`).
- **No agentic execution.** Research agents may collect, analyze, report, and
  trigger research runs, but may never approve, reject, buy, sell, or mutate
  risk settings. Groww is read-only unless a future ADR explicitly changes
  this invariant.

## Conventions

- Config: always `get_settings()` from `config/settings.py` (cached singleton, pydantic-settings from `.env`). Never instantiate `Settings` directly.
- Logging: `logger = logging.getLogger(__name__)`; stdout only (no file handlers).
- Symbols: NSE symbols **without** `.NS` suffix in state/proposals; `screener.py` appends `.NS` only for yfinance downloads.
- LangGraph `thread_id` is `f"trade-{symbol}-{date.today().isoformat()}"` — **one fresh thread per symbol per calendar day**. Use `graph.latest_thread_id_for(symbol)` to resolve "the current thread" (e.g. for approval callbacks) rather than assuming today's date.
- The NIFTY 100 universe is never hardcoded — always call `app.universe.get_universe()`. See its fallback chain (live fetch → cache → committed seed) below.
- Audit timestamps are UTC ISO-8601 (`datetime.now(timezone.utc)`).

## Gotchas

- `build_graph()` uses `langgraph-checkpoint-postgres` (`PostgresSaver`) and `langgraph.store.postgres` (`PostgresStore`) backed by a connection pool (`app.db.get_connection_pool()`, ADR-023).
- yfinance quirks in `screener.py` are load-bearing: `.NS` suffix and MultiIndex column flattening. The screener now computes EMA/RSI/ATR directly with pandas, so `pandas_ta` is no longer a runtime dependency.
- `telegram_bot.send_proposal_to_chat` is the public proposal-delivery entrypoint used cross-module from `pipeline.py`. When the bot isn't running in-process (e.g. `scan`/`run` separate from `serve`), it falls back to a direct Bot API HTTP POST (`_send_via_bot_api`) — keep that fallback.
- **`TELEGRAM_CHAT_ID` must be the operator's chat id, not the bot's own id.** Setting it to the bot id (the number in the bot token) makes pushes fail with `403 Forbidden: the bot can't send messages to the bot`. Get your id via @userinfobot or the bot's `getUpdates` after sending `/start`.
- `KILLED` resume value works via fall-through to `rejected` in `_route_after_approval` (only `APPROVED` is special-cased). The Kill button was removed from the UI (redundant with Reject); `KILLED` is still accepted by `resume_symbol` for backward compatibility.
- **The Streamlit dashboard was removed** (archived under `legacy/dashboard/`). Telegram is now the only UI. If you ever re-add a web script, it must not be named `app.py` — Streamlit puts the script's directory on `sys.path`, so `dashboard/app.py` shadows the `app/` package and `from app import executor` fails with a circular-import error.
- **Universe CSVs live in two places on purpose.** `config/universe/nifty100_seed.csv` is committed (config/ isn't gitignored) — the trustworthy fallback baseline. `data/universe/nifty100.csv` is the gitignored, auto-refreshed runtime cache. Never hand-edit either from code; only `app/universe.py` writes the cache.

## Vestigial — don't assume it works

- **LLM calls route through the Siemens SDC gateway** via the `GOOGLE_GEMINI_BASE_URL` *system* env var (`https://llm.sdc.siemens.cloud`) if still present in your shell — the app itself uses `OPENAI_BASE_URL`/`OPENAI_API_KEY`/`OPENAI_MODEL` from `.env`, not that system var. A `401 Key Expired` means the upstream gateway key lapsed; renew it there, not a code bug. After changing `.env`, restart `serve` (settings are cached at boot; `telegram_bot._auto_configure_chat_id` is the one exception that calls `get_settings.cache_clear()` itself).
