# NIFTY 100 Cash Equity Swing Trading & Research Assistant

A **local-first, containerized** algorithmic research and decision-support system
for NIFTY 100 cash-equity (CNC) swing trading. It screens the universe daily,
uses an LLM (Gemini Flash) *only* as a qualitative catalyst filter, enforces
**deterministic** risk gates (1% max account risk, ATR two-tier stops, R:R ≥ 2.0),
requires **manual human approval via Telegram** before paper execution, and logs
every decision to SQLite for post-mortem analysis.

> ⚠️ **Not financial advice.** Paper trading is the default and the only
> supported mode. Live order routing is intentionally blocked until a broker
> adapter is proven.

---

## Features

- **Deterministic risk engine** — pure Python math, zero LLM influence on prices/sizes.
- **Two-tier ATR stops** — soft inspection stop (1.5×ATR) + hard disaster stop (2.5×ATR).
- **1% position sizing** — `Quantity = floor((Capital × 0.01) / (Entry − HardStop))`.
- **LLM catalyst filter** — any OpenAI-compatible model classifies the *nature*
  of a drop (earnings noise vs. structural damage) via structured output. Fails closed.
- **Human-in-the-Loop** — LangGraph `interrupt()` pauses at trade generation;
  Telegram inline buttons resume with `APPROVED` / `REJECTED` / `KILLED`.
- **Durable checkpoints** — `SqliteSaver` persists state per trade thread; survives restarts.
- **Full audit trail** — every decision state logged to SQLite; review via `/trades` in Telegram.
- **Telegram is the whole UI** — no web port; `/scan`, `/run`, `/trades` + approval buttons.
- **Zero cloud cost** — runs entirely in local Docker.

---

## Directory Structure

```
trading_agent/
├── data/                  # SQLite audit DB + LangGraph checkpoints (persistent volume)
├── logs/                  # Application logs
├── config/
│   ├── settings.py        # Pydantic BaseSettings from .env
│   └── mcp_servers.json   # Dynamic MCP server definitions
├── app/
│   ├── state.py           # TypedDict state + Pydantic models
│   ├── screener.py        # yfinance + pandas_ta technical screening
│   ├── analyst.py         # LLM catalyst node (OpenAI-compatible endpoint)
│   ├── risk.py            # Deterministic ATR stops & 1% sizing
│   ├── telegram_bot.py    # Long-polling bot: HITL buttons + /scan /run /trades + chat
│   ├── executor.py        # Paper fills + SQLite audit recorder
│   ├── graph.py           # LangGraph compilation, checkpoints, interrupts
│   ├── pipeline.py        # Shared scan/run orchestration (CLI + bot)
│   ├── chat_agent.py      # Conversational research agent (ReAct, read/trigger-only)
│   └── main.py            # Entry point, CLI, scheduler
├── legacy/
│   └── dashboard/         # (archived) former Streamlit UI — Telegram replaced it
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── ARCHITECTURE.md
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

# 2. Build and run the single service
docker compose up --build
```

The `trading-engine` service runs the LangGraph pipeline and the Telegram
long-polling bot. **Telegram is the complete UI** — message the bot `/start`,
then use `/scan`, `/run SYMBOL`, and `/trades` (see below). No ports are
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
```

---

## CLI Reference

| Command | Description |
| --------- | ------------- |
| `python -m app.main scan` | Scan the NIFTY 100 universe, run each qualifier through the graph, push proposals to Telegram. |
| `python -m app.main run <SYMBOL>` | Run a single symbol through the graph (testing / manual review). |
| `python -m app.main serve` | Start the daily scheduler and the Telegram long-polling bot. |

## Telegram Commands (the complete UI)

| Command | Description |
| --------- | ------------- |
| `/start` | Greet + auto-save your chat id to `.env` on first use. |
| `/scan` | Screen the NIFTY 100 universe; push every qualifying proposal with approval buttons. |
| `/run SYMBOL` | Run one symbol through the pipeline (e.g. `/run RELIANCE`). |
| `/trades` | Show the audit log: open/closed paper trades, fills, P&L. |
| ✅ / ❌ buttons | Approve / Reject a paused proposal (resumes the LangGraph thread). |
| Free text | Ask the research agent anything: "why did TITAN qualify?", "what are my open trades?", "run RELIANCE". Read/trigger-only — it can never approve a trade. |

---

## Human-in-the-Loop Workflow

1. The graph runs a symbol through `screener → analyst → risk`.
2. At `human_approval`, LangGraph `interrupt()` **pauses** and returns the proposal.
3. `app/pipeline.py` pushes a Markdown proposal card to Telegram with inline buttons:
   - **✅ Approve Trade** → resumes with `APPROVED` → paper fill recorded.
   - **❌ Reject** → resumes with `REJECTED` → no order.
4. The resumed thread completes and the audit row is written to SQLite.

Because the pause is checkpointed, the approval can arrive after a container
restart without losing state.

---

## Configuration Reference

See `.env.example` for the full list. Key values:

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `TRADING_MODE` | `PAPER_TRADING` | `PAPER_TRADING` (safe) or `LIVE` (blocked). |
| `PORTFOLIO_CAPITAL` | `100000.0` | Total equity in INR. |
| `RISK_PER_TRADE_PCT` | `0.01` | 1% of equity risked per trade. |
| `ATR_SOFT_MULT` | `1.5` | Soft stop = entry − 1.5×ATR. |
| `ATR_HARD_MULT` | `2.5` | Hard stop = entry − 2.5×ATR. |
| `MIN_RISK_TO_REWARD` | `2.0` | Minimum R:R to accept a setup. |
| `RSI_OVERSOLD_MAX` | `42.0` | RSI_14 must be below this. |
| `VOLUME_RATIO_MIN` | `0.5` | Volume must exceed 0.5× the 20-day average. |

---

## Testing

The deterministic risk engine is a pure function and is trivially unit-testable:

```python
from app.risk import calculate_risk

# A healthy setup: entry 100, ATR 2.0, capital 100k
p = calculate_risk("RELIANCE", entry_price=100.0, atr=2.0, portfolio_capital=100_000)
assert p is not None
assert p.hard_stop == 95.0          # 100 - 2.5*2
assert p.soft_stop == 97.0          # 100 - 1.5*2
assert p.target_price == 110.0      # 100 + 2*(100-95)
assert p.quantity == 20             # floor(1000 / 5)
assert p.risk_to_reward == 2.0

# A degenerate setup (ATR too large) should be rejected.
assert calculate_risk("X", entry_price=10.0, atr=5.0) is None
```

---

## Operational Runbook

**Daily EOD:**

1. Ensure `.env` is configured and the container is up (`docker compose ps`).
2. Send `/scan` to the bot (the scheduler is a no-op stub — trigger manually).
3. Review proposal cards in Telegram; approve/reject via the inline buttons.
4. Check `/trades` for the audit trail.

**Post-mortem:**

1. Send `/trades` to the bot for the open/closed trade summary (fills, P&L).
2. Full per-trade detail (RSI, EMA_200, ATR, LLM thesis, mistake category) is in
   the `trade_audit_log` table of `data/trading_audit.db`.

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
- The broker MCP server (`groww`) is **disabled by default** in paper mode.
- The system runs as a non-root user inside Docker.
- All risk math is deterministic and auditable; the LLM cannot override it.
