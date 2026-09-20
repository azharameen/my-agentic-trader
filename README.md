# NIFTY 100 Cash Equity Swing Trading & Research Assistant

A **local-first, containerized** algorithmic research and decision-support system
for NIFTY 100 cash-equity (CNC) swing trading. It screens the universe daily,
uses an LLM (any OpenAI-compatible endpoint) *only* as a qualitative catalyst filter, enforces
**deterministic** risk gates (1% max account risk, ATR two-tier stops, R:R ≥ 2.0),
requires **manual human approval via Telegram** before paper execution, and logs
every decision to PostgreSQL for post-mortem analysis.

> ⚠️ **Not financial advice.** Paper trading is the default and the only
> supported mode. Live order routing is intentionally blocked until a broker
> adapter is proven.

---

## Features

- **Trustworthy, self-refreshing universe** — `app/universe.py` fetches the official NIFTY 100 constituent list, cached locally and auto-refreshed monthly; falls back to a committed seed snapshot if offline. No hardcoded symbol list anywhere.
- **Deterministic risk engine** — pure Python math, zero LLM influence on prices/sizes.
- **Two-tier ATR stops** — soft inspection stop (1.5×ATR) + hard disaster stop (2.5×ATR).
- **1% position sizing** — `Quantity = floor((Capital × 0.01) / (Entry − HardStop))`, sized off actual equity (base capital + realized P&L).
- **LLM catalyst filter** — any OpenAI-compatible model classifies the *nature*
  of a drop (earnings noise vs. structural damage) via structured output, grounded in real headlines pulled from free market RSS feeds. Fails closed.
- **Position monitor** — auto-closes open paper trades on stop/target breach on every `/scan`, so P&L is real.
- **Human-in-the-Loop** — LangGraph `interrupt()` pauses at trade generation;
  Telegram inline buttons resume with `APPROVED` / `REJECTED` / `KILLED`. Stale proposals (old + price has moved) are rejected on resume instead of executed at outdated levels.
- **Durable checkpoints** — `PostgresSaver` persists state per trade thread (one per symbol per day); survives restarts.
- **Full audit trail** — every decision state logged to PostgreSQL (`trade_audit_log`); review via `/trades` or `/pending` in Telegram.
- **Telegram is the whole UI** — no web port; `/scan`, `/run`, `/trades`, `/pending`, `/performance` + approval buttons.
- **Automatic daily scan + monthly universe refresh** — wired into `apscheduler` inside `serve`.
- **Phase 3 observability foundation** — OpenTelemetry spans cover pipeline scans and graph runs; enable console export only when debugging.
- **Phase 4 strategy seam** — deterministic setup filters resolve through `SETUP_STRATEGY`, preserving the current filter while making new indicator strategies swappable.
- **Phase 5 reliability boundaries** — broker adapter protocol keeps paper execution separate from a fail-closed LIVE placeholder, and a PostgreSQL outbox retries Telegram proposal delivery after failures.
- **Zero cloud cost** — runs entirely in local Docker with PostgreSQL 16 Alpine sidecar.

---

## Directory Structure

```text
trading_agent/
├── data/                   # Runtime data & universe cache (persistent volume)
├── logs/                   # Application logs
├── tests/                  # pytest suite (risk, screener, universe, graph, monitor)
├── config/
│   ├── settings.py         # Pydantic BaseSettings from .env
│   └── universe/
│       └── nifty100_seed.csv   # Committed fallback NIFTY 100 snapshot
├── app/
│   ├── db.py               # PostgreSQL connection pool & unified storage abstraction
│   ├── checkpoint.py       # LangGraph PostgresSaver lifecycle
│   ├── store.py            # LangGraph PostgresStore lifecycle
│   ├── state.py            # TypedDict state + Pydantic models
│   ├── universe.py         # NIFTY 100 constituent list: live fetch + cache + seed fallback
│   ├── screener.py         # yfinance + pandas technical screening (parallelized)
│   ├── news.py             # Free RSS headline ingestion for the catalyst analyst
│   ├── analyst.py          # LLM catalyst node (OpenAI-compatible endpoint)
│   ├── risk.py             # Deterministic ATR stops & 1% sizing
│   ├── monitor.py          # Auto-closes open paper trades on stop/target breach
│   ├── telegram_bot.py     # Long-polling bot: HITL buttons + /scan /run /trades /pending + chat
│   ├── executor.py         # Paper fills + PostgreSQL audit recorder
│   ├── graph.py            # LangGraph compilation, checkpoints, interrupts
│   ├── pipeline.py         # Shared scan/run orchestration (CLI + bot)
│   ├── chat_agent.py       # Conversational research agent (ReAct, read/trigger-only)
│   └── main.py             # Entry point, CLI, scheduler
├── legacy/
│   └── dashboard/          # (archived) former Streamlit UI — Telegram replaced it
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── docs/
│   ├── architecture.md
│   ├── prd.md
│   ├── reference.md
│   ├── architecture-decisions.md
│   ├── tasks.md
│   └── sdlc-process.md
├── ARCHITECTURE.md             # compatibility link to docs/architecture.md
└── README.md
```

---

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- An API key for an OpenAI-compatible LLM endpoint (OpenAI, or a gateway via `OPENAI_BASE_URL`)
- A Telegram bot (via [@BotFather](https://t.me/BotFather)) and your chat id

---

## Quick Start (Docker)

```bash
cd trading_agent

# 1. Configure environment
cp .env.example .env
#    Edit .env: set OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL,
#    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# 2. Build and run the services (app + PostgreSQL 16 sidecar)
docker compose up --build
```

The `trading-engine` service runs the LangGraph pipeline and the Telegram
long-polling bot, backed by the `postgres` sidecar container. **Telegram is the complete UI** — message the bot `/start`,
then use `/scan`, `/run SYMBOL`, `/performance`, and `/trades` (see below). No ports are
exposed; long polling is outbound-only.

---

## Local Development (no Docker)

```bash
cd trading_agent
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # then edit

# One-shot universe scan + proposals (pushes to Telegram)
python -m app.main scan

# Run a single symbol through the graph (for testing)
python -m app.main run RELIANCE

# Start scheduler + Telegram bot (long-running)
python -m app.main serve

# Check database integrity
python -m app.main check-databases

# Evaluate paper-trade outcomes
python -m app.main evaluate
```

---

## CLI Reference

| Command | Description |
| --------- | ------------- |
| `python -m app.main scan` | Check open positions, scan the NIFTY 100 universe, run each qualifier through the graph, push proposals to Telegram. |
| `python -m app.main run <SYMBOL>` | Run a single symbol through the graph (testing / manual review). |
| `python -m app.main refresh-universe` | Force a live refresh of the NIFTY 100 constituent list and report the diff. |
| `python -m app.main serve` | Start the daily scheduler (auto scan + monthly universe refresh) and the Telegram long-polling bot. |
| `python -m app.main check-databases` | Check PostgreSQL database integrity and table liveness. |
| `python -m app.main evaluate` | Evaluate paper-trade outcomes against the benchmark. |
| `python -m app.main history <SYMBOL>` | View time-travel checkpoint step history for a symbol. |

## Telegram Commands (the complete UI)

| Command | Description |
| --------- | ------------- |
| `/start` | Greet + auto-save your chat id to `.env` on first use. |
| `/scan` | Screen the NIFTY 100 universe; push every qualifying proposal with approval buttons. |
| `/run SYMBOL` | Run one symbol through the pipeline (e.g. `/run RELIANCE`). |
| `/trades` | Show the audit log: open/closed paper trades, fills, P&L. |
| `/pending` | List every proposal currently awaiting your approval. |
| `/performance` | Report paper trading performance metrics against NIFTY 100 benchmark. |
| ✅ / ❌ buttons | Approve / Reject a paused proposal (resumes the LangGraph thread). |
| Free text | Ask the research agent anything: "why did TITAN qualify?", "what are my open trades?", "run RELIANCE". Read/trigger-only — it can never approve a trade. |

---

## Human-in-the-Loop Workflow

1. The graph runs a symbol through `screener → analyst → risk`.
2. At `human_approval`, LangGraph `interrupt()` **pauses** and returns the proposal.
3. `app/pipeline.py` pushes a Markdown proposal card to Telegram with inline buttons:
   - **✅ Approve Trade** → resumes with `APPROVED` → paper fill recorded.
   - **❌ Reject** → resumes with `REJECTED` → no order.
4. The resumed thread completes and the audit row is written to PostgreSQL.

Because the pause is checkpointed via `PostgresSaver`, the approval can arrive after a container
restart without losing state.

---

## Configuration Reference

See `.env.example` for the full list. Key values:

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `TRADING_MODE` | `PAPER_TRADING` | `PAPER_TRADING` (safe) or `LIVE` (blocked). |
| `DATABASE_URL` | `postgresql://trader_admin:trader_secret@localhost:5433/trader_db` | PostgreSQL connection string. |
| `PORTFOLIO_CAPITAL` | `100000.0` | Total equity in INR. |
| `RISK_PER_TRADE_PCT` | `0.01` | 1% of equity risked per trade. |
| `ATR_SOFT_MULT` | `1.5` | Soft stop = entry − 1.5×ATR. |
| `ATR_HARD_MULT` | `2.5` | Hard stop = entry − 2.5×ATR. |
| `MIN_RISK_TO_REWARD` | `2.0` | Minimum R:R to accept a setup. |
| `RSI_OVERSOLD_MAX` | `42.0` | RSI_14 must be below this. |
| `VOLUME_RATIO_MIN` | `0.5` | Volume must exceed 0.5× the 20-day average. |
| `UNIVERSE_REFRESH_DAYS` | `30` | Runtime universe cache is re-fetched live after this many days. |
| `STALE_PROPOSAL_MINUTES` | `240` | A paused proposal older than this + price drift is rejected on resume instead of executed. |
| `SCAN_CRON_HOUR` / `SCAN_CRON_MINUTE` | `15` / `45` | Time (IST) of the automatic daily scan inside `serve`. |
| `SETUP_STRATEGY` | `pullback_in_uptrend` | Deterministic strategy implementation resolved by `app/strategies.py`. |
| `OTEL_ENABLED` | `false` | Enable OpenTelemetry spans for pipeline and graph operations. |

---

## Testing

```bash
python -m pytest -q
```

The deterministic risk engine is a pure function and is trivially unit-testable
(see `tests/test_risk.py`); the same applies to the screener filter, the
universe fallback chain, graph routing, and the position monitor — all covered
under `tests/`.

---

## Operational Runbook

**Daily EOD:**

1. Ensure `.env` is configured and the container is up (`docker compose ps`).
2. `serve` runs the scan automatically at `SCAN_CRON_HOUR:SCAN_CRON_MINUTE` IST (default 15:45, Mon-Fri) — or send `/scan` to trigger it manually anytime.
3. Review proposal cards in Telegram; approve/reject via the inline buttons. Use `/pending` to see everything still awaiting a decision.
4. Check `/trades` for the audit trail.

**Post-mortem:**

1. Send `/trades` to the bot for the open/closed trade summary (fills, P&L).
2. Full per-trade detail (RSI, EMA_200, ATR, LLM thesis, mistake category) is in
   the `trade_audit_log` table of PostgreSQL.

**Troubleshooting:**

- **No proposals arriving** — check `OPENAI_API_KEY`/`OPENAI_BASE_URL` and `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` in `.env`; check `docker compose logs trading-engine`.
- **Analyst failing closed** — if the LLM endpoint is unreachable, the analyst
  returns a conservative `GENERAL_MARKET` / non-pullback assessment, so trades
  are *not* generated. This is intentional (fail-safe).
- **LIVE mode** — the executor raises `RuntimeError` if `TRADING_MODE=LIVE`;
  broker routing is not implemented.

---

## Security Notes

- Never commit `.env`; only `.env.example` is tracked.
- The system runs as a non-root user inside Docker.
- All risk math is deterministic and auditable; the LLM cannot override it.
