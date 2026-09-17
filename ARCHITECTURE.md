# Architecture — NIFTY 100 Cash Equity Swing Trading & Research Assistant

A local-first, containerized **algorithmic research and decision-support** system.
It performs daily end-of-day technical screening on the NIFTY 100 universe, uses an
LLM (any OpenAI-compatible endpoint) *only* as a qualitative news/catalyst filter, enforces strict
**deterministic** risk gates, requires **manual human approval via Telegram** before
any (paper) execution, and logs every decision state to SQLite for post-mortems.

---

## 1. Design Philosophy

| Principle | How it is enforced |
| ----------- | -------------------- |
| **No autonomous black-box execution** | The LLM (`analyst.py`) only classifies the *nature* of a price drop via structured output. It never emits prices, sizes, or orders. |
| **Deterministic risk invariants** | `risk.py` is pure Python math (zero LLM calls). Risk %, ATR multipliers, and R:R floor are hardcoded config constants. |
| **Cash equity (CNC) only** | No MIS, no F&O. Holding period 2–15 days. The executor only models delivery fills. |
| **NIFTY 100 liquid universe** | `screener.py` scans a fixed NIFTY 100 list; no penny/illiquid small-caps. |
| **Zero-cost local-first** | Everything runs in local Docker. Paper trading is the default; broker execution is mocked until proven. |
| **Human-in-the-Loop** | LangGraph `interrupt()` pauses the graph at trade generation; a Telegram button resumes it. |

---

## 2. High-Level Data Flow

```mermaid
flowchart TD
    A[Daily EOD Trigger<br/>main.py scheduler] --> B[math_screener<br/>screener.py]
    B -->|qualifying setups| C[analyze_catalyst<br/>analyst.py + LLM]
    C -->|temporary pullback?| D{Structural<br/>damage?}
    D -->|yes| R[rejected<br/>terminal]
    D -->|no| E[calculate_risk<br/>risk.py deterministic]
    E -->|R:R >= 2.0 & qty > 0| F[human_approval<br/>interrupt()]
    E -->|rejected| R
    F -->|Command resume APPROVED| G[paper_execute<br/>executor.py]
    F -->|Command resume REJECTED| R
    G --> H[(SQLite<br/>trade_audit_log)]
    F -.proposal card.-> T[Telegram Bot<br/>long polling]
    T -.inline buttons.-> F
    T -.commands /scan /run /trades.-> B
    H -.read by /trades.-> T
```

---

## 3. Component Responsibilities

| Module | Responsibility | LLM? |
| -------- | ---------------- | ------ |
| `config/settings.py` | Typed, validated config from `.env` (pydantic-settings). | No |
| `config/mcp_servers.json` | Dynamic MCP tool definitions (groww, search, filesystem). | No |
| `app/state.py` | `CatalystAssessment`, `TradeProposal` (Pydantic) + `TradingState` (TypedDict). | No |
| `app/screener.py` | yfinance OHLCV + pandas_ta (EMA_200, RSI_14, ATR_14) + setup filter. | No |
| `app/analyst.py` | LLM structured-output catalyst classification (OpenAI-compatible endpoint). | **Yes** |
| `app/risk.py` | 1% position sizing, two-tier ATR stops, R:R gate. | No |
| `app/graph.py` | LangGraph `StateGraph`, SqliteSaver checkpoints, `interrupt()` HITL. | No |
| `app/executor.py` | SQLite schema init, paper fills (0.05% slippage), audit logging. | No |
| `app/pipeline.py` | Shared scan/run orchestration used by both the CLI and the bot. | No |
| `app/telegram_bot.py` | Long-polling bot: proposal cards, approval buttons, `/scan` `/run` `/trades`. | No |
| `app/main.py` | CLI triggers, scheduler, bot bootstrap. | No |

---

## 4. LangGraph: Checkpoints, State Recovery & HITL Interrupts

### 4.1 State

`TradingState` (a `TypedDict`, `total=False`) is the single shared, checkpointed
state. Each node returns a *partial* dict of the keys it owns; LangGraph merges
them into the full state after every **super-step**. Because the state is plain
serializable data (scalars, lists, Pydantic models), it round-trips cleanly to
SQLite.

### 4.2 Checkpoints (`SqliteSaver`)

`graph.build_graph()` compiles the graph with a `SqliteSaver` backed by
`data/checkpoints.db`. After each super-step LangGraph persists the full state
keyed by `thread_id` (one thread per symbol: `trade-<SYMBOL>`).

**State recovery:** if the process crashes mid-run, the last committed
checkpoint is durable. Re-invoking the same `thread_id` resumes from the last
completed node rather than re-running the whole pipeline. This is what makes the
HITL pause safe across container restarts — the paused state survives.

### 4.3 Human-in-the-Loop via `interrupt()`

The `human_approval` node calls LangGraph's native `interrupt(card)`:

1. `interrupt(card)` **suspends** the graph, persists the current state to the
   checkpoint, and returns `card` (the proposal dict) to the caller.
2. `main.py` detects the `__interrupt__` in the returned state and pushes the
   proposal card to Telegram with inline buttons.
3. When the operator taps a button, `telegram_bot.py` calls
   `graph.resume_symbol(symbol, "APPROVED" | "REJECTED" | "KILLED")`, which
   invokes the graph with `Command(resume=<decision>)`.
4. `interrupt()` returns that decision value, the node writes `human_decision`,
   and conditional routing sends the thread to `paper_execute` (approved) or
   `rejected` (rejected/killed).

This is a *durable* pause: the graph is not blocked on a thread — it is
checkpointed and resumed, so the approval can arrive minutes, hours, or after a
restart.

### 4.4 Conditional Routing

- After `math_screener`: no qualifying setup → `END`.
- After `analyze_catalyst`: structural damage / non-pullback → `rejected` (no
  human prompt for an obvious no-trade).
- After `calculate_risk`: R:R < 2.0 or qty ≤ 0 → `rejected`.
- After `human_approval`: `APPROVED` → `paper_execute`; else → `rejected`.

---

## 5. Deterministic Risk Math (no LLM)

Given `entry_price` and `atr_14`:

```
soft_stop    = entry - 1.5 * atr_14        # inspection only, no auto-sell
hard_stop    = entry - 2.5 * atr_14        # absolute invalidation
risk/share   = entry - hard_stop
target       = entry + 2.0 * risk/share    # enforces R:R >= 1:2
risk_amount  = capital * 0.01              # 1% of portfolio equity
quantity     = floor(risk_amount / risk/share)
```

A setup is **rejected** if `risk_to_reward < 2.0` or `quantity <= 0`.

---

## 6. Persistence

### `data/trading_audit.db` — `trade_audit_log`

| Column | Meaning |
| -------- | --------- |
| `trade_id` | UUID primary key |
| `timestamp` | UTC ISO-8601 creation time |
| `symbol` | NSE symbol |
| `entry_price`, `soft_stop`, `hard_stop`, `target_price` | Deterministic price levels |
| `quantity` | Position size from the 1% rule |
| `rsi`, `ema_200`, `atr` | Technical snapshot at decision time |
| `thesis` | LLM catalyst rationale (for post-mortem) |
| `human_decision` | APPROVED / REJECTED / KILLED |
| `fill_price` | Simulated fill (entry + 0.05% slippage) |
| `status` | `OPEN_PAPER` / `CLOSED` |
| `exit_price`, `realized_pnl` | Populated on close |
| `mistake_category` | Post-mortem classification |

### `data/checkpoints.db`

LangGraph `SqliteSaver` state — one row-set per `thread_id`, enabling durable
HITL pauses and crash recovery.

Both schemas are created automatically on boot (`executor.init_db()` and the
`SqliteSaver` connection in `graph._get_checkpointer()`).

---

## 7. Deployment

`docker-compose.yml` runs a **single service** from one image:

- **trading-engine** — `python -m app.main serve` (LangGraph pipeline +
  Telegram long polling). No inbound ports needed (long polling is outbound
  HTTPS). Telegram is the complete control plane — there is no web UI.

The service mounts `./data` and `./logs` as persistent volumes, runs as a
non-root user, and carries a health check.
