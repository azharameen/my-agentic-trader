# AGENTS.md — NIFTY 100 Swing Trading Research Assistant

Local-first, containerized decision-support system: deterministic technical screening → LLM catalyst filter (any OpenAI-compatible endpoint via `langchain-openai`; configured through `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL`) → deterministic risk gates → human approval via Telegram → paper execution → SQLite audit.

**Read first:** [README.md](README.md) (setup, CLI, config reference) and [ARCHITECTURE.md](ARCHITECTURE.md) (data flow, LangGraph HITL, risk math, persistence). Do not duplicate their content here.

## Commands

```bash
python -m app.main scan               # one-shot: scan NIFTY 100, push proposals to Telegram
python -m app.main run <SYMBOL>       # run a single symbol through the graph (testing)
python -m app.main refresh-universe   # force a live refresh of the NIFTY 100 constituent list
python -m app.main serve              # start scheduler + Telegram bot (long-running)
docker compose up --build             # single service (engine + bot)
pytest -q                             # unit tests (risk, screener, universe, graph, monitor)
```

**Telegram is the complete control plane** — no web UI/port exists. In the running bot: `/scan` (universe scan), `/run SYMBOL` (single symbol), `/trades` (audit log), `/pending` (proposals awaiting approval), Approve/Reject buttons on proposal cards, and free-text questions routed to the conversational research agent (`app/chat_agent.py`, a ReAct agent that is **read/trigger-only** — it can never approve/reject a trade). The CLI `scan`/`run` do the same via `app/pipeline.py` (shared with the bot — keep them in sync).

- Python 3.11+, plain `pip install -r requirements.txt` (no pyproject/Makefile).
- `pytest -q` runs the suite under `tests/`. Call `get_settings.cache_clear()` after mutating env vars in a test.

## Hard invariants — do not break

- **LLM never touches numbers.** `analyst.py` only classifies the *nature* of a drop via `with_structured_output(CatalystAssessment)`. All prices/stops/sizes come from `risk.py` (pure math). Never add LLM output to `TradeProposal`.
- **Fail-closed everywhere.** LLM errors/missing API key → conservative fallback → trade rejected. Per-symbol screener errors are caught and skipped. Keep broad `except` + `# noqa: BLE001` markers where they exist — they are intentional.
- **Live trading is blocked.** `executor.record_open_trade` raises `RuntimeError` when `TRADING_MODE == "LIVE"`. Paper trading is the only supported mode.
- **Audit everything.** Every decision state goes to `trade_audit_log` in `data/trading_audit.db`.

## Conventions

- Config: always `get_settings()` from `config/settings.py` (cached singleton, pydantic-settings from `.env`). Never instantiate `Settings` directly.
- Logging: `logger = logging.getLogger(__name__)`; stdout only (no file handlers).
- Symbols: NSE symbols **without** `.NS` suffix in state/proposals; `screener.py` appends `.NS` only for yfinance downloads.
- LangGraph `thread_id` is `f"trade-{symbol}-{date.today().isoformat()}"` — **one fresh thread per symbol per calendar day**. Use `graph.latest_thread_id_for(symbol)` to resolve "the current thread" (e.g. for approval callbacks) rather than assuming today's date.
- The NIFTY 100 universe is never hardcoded — always call `app.universe.get_universe()`. See its fallback chain (live fetch → cache → committed seed) below.
- Audit timestamps are UTC ISO-8601 (`datetime.now(timezone.utc)`).

## Gotchas

- `build_graph()` uses a process-wide `SqliteSaver` built from a persistent `sqlite3` connection (`_get_checkpointer()`). **Do not** use `SqliteSaver.from_conn_string()` directly — in the installed `langgraph-checkpoint-sqlite` it returns a *context manager*, not a saver, and `graph.compile(checkpointer=...)` raises `TypeError: Invalid checkpointer`. The helper also creates `data/` if missing.
- yfinance quirks in `screener.py` are load-bearing: `.NS` suffix, MultiIndex column flattening, and renaming capitalized OHLCV columns to lowercase for `pandas_ta`. Don't "clean up" these.
- `pandas-ta` is a **beta** dependency (`0.3.14b0`) — the riskiest pin; be careful upgrading pandas/numpy.
- `telegram_bot._send_proposal_to_chat` is "private" but called cross-module from `main.py` — don't rename. When the bot isn't running in-process (e.g. `scan`/`run` separate from `serve`), it falls back to a direct Bot API HTTP POST (`_send_via_bot_api`) — keep that fallback.
- **`TELEGRAM_CHAT_ID` must be the operator's chat id, not the bot's own id.** Setting it to the bot id (the number in the bot token) makes pushes fail with `403 Forbidden: the bot can't send messages to the bot`. Get your id via @userinfobot or the bot's `getUpdates` after sending `/start`.
- `KILLED` resume value works via fall-through to `rejected` in `_route_after_approval` (only `APPROVED` is special-cased). The Kill button was removed from the UI (redundant with Reject); `KILLED` is still accepted by `resume_symbol` for backward compatibility.
- **The Streamlit dashboard was removed** (archived under `legacy/dashboard/`). Telegram is now the only UI. If you ever re-add a web script, it must not be named `app.py` — Streamlit puts the script's directory on `sys.path`, so `dashboard/app.py` shadows the `app/` package and `from app import executor` fails with a circular-import error.
- **Universe CSVs live in two places on purpose.** `config/universe/nifty100_seed.csv` is committed (config/ isn't gitignored) — the trustworthy fallback baseline. `data/universe/nifty100.csv` is the gitignored, auto-refreshed runtime cache. Never hand-edit either from code; only `app/universe.py` writes the cache.
- **Checkpointer thread-safety at scale is a known, accepted limitation**, not a bug to "fix" reflexively — the single `sqlite3` connection (`check_same_thread=False`) is fine at single-operator scale; revisit only if `/scan` concurrency issues are actually observed. `pipeline.py` already guards overlapping `/scan` calls with an in-process lock (`ScanInProgressError`).

## Vestigial — don't assume it works

- **LLM calls route through the Siemens SDC gateway** via the `GOOGLE_GEMINI_BASE_URL` *system* env var (`https://llm.sdc.siemens.cloud`) if still present in your shell — the app itself uses `OPENAI_BASE_URL`/`OPENAI_API_KEY`/`OPENAI_MODEL` from `.env`, not that system var. A `401 Key Expired` means the upstream gateway key lapsed; renew it there, not a code bug. After changing `.env`, restart `serve` (settings are cached at boot; `telegram_bot._auto_configure_chat_id` is the one exception that calls `get_settings.cache_clear()` itself).
