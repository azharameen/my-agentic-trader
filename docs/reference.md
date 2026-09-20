# References

This is the source-of-truth catalog for external data, APIs, credentials, and
research tooling. Every adapter must document its access method, freshness,
limits, fallback, and validation behavior here before implementation.

## Current Sources

| Source | Data | Access | Key | Cost | Trust and use |
| --- | --- | --- | --- | --- | --- |
| NSE Indices | NIFTY 100 constituents, industry, ISIN | Public CSV | No | Free | Primary universe source |
| Yahoo Finance via `yfinance` | Daily OHLCV & Macro Indices (`^NSEI`, `^INDIAVIX`) | Python library/public endpoint | No | Free | Price baseline and macro regime context; validate and cache |
| Economic Times RSS | Market headlines | RSS | No | Free | Candidate news evidence |
| Moneycontrol RSS | Business headlines | RSS | No | Free | Candidate news evidence |
| Business Standard RSS | Market headlines | RSS | No | Free | Candidate news evidence |
| Multi-Provider LLM (OpenAI, Gemini, Anthropic, Groq, Gateway) | Qualitative research analysis (Bear, Bull, Synthesizer) | HTTP APIs via native LangChain adapters | Provider-specific API key | Depends on provider | Qualitative analysis only; never source of numeric facts (ADR-003, ADR-022) |
| Telegram Bot API | Human review and notifications | Bot API | `TELEGRAM_BOT_TOKEN` | Free | Control plane only |
| PostgreSQL 16 (`trader_db`) | Audit log, checkpoints, store, outbox, cache | PostgreSQL connection pool | `DATABASE_URL` | Free (sidecar) | Unified system record (ADR-023) |
| Evidence snapshot store | Normalized evidence and provenance | PostgreSQL | `DATABASE_URL` | Free | Immutable per-run research record |

## Candidate Symbol-Master Sources

These are discussion candidates for the eventual full-symbol-list / security-
master task. They are not all enabled today.

The next release does not use these candidates. It remains NIFTY 100-only.

| Source | Data | Access | Notes |
| --- | --- | --- | --- |
| NSE Indices | NIFTY universe lists and index constituents | Public CSV | Current primary universe source |
| NSE equities master | All NSE listed symbols and metadata | Public CSV / session-backed pages | Needs terms review and reliability validation |
| BSE security master | All BSE listed symbols and metadata | Public pages / downloads | More fragile; likely needs session/cookie handling |
| Paid market-data vendors | Full equities master and enrichment fields | API key / contract | Candidate if official sources are unstable or incomplete |
| Screener.in and similar aggregators | Discovery and enrichment | Site/API-like access | Secondary discovery only; not authoritative |

Corporate-event collection is intentionally not enabled until concrete NSE/BSE
access methods and terms are reviewed. The normalized contract currently accepts
earnings, board meetings, dividends, splits, bonuses, rights, pledges, and
announcements with symbol/ISIN identity and provenance.

The current adapter is disabled by default. Set `CORPORATE_EVENTS_ENABLED=true`
and provide `CORPORATE_EVENTS_SOURCE_URL` only for a reviewed source returning
normalized JSON event rows. It falls back to
`CORPORATE_EVENTS_CACHE_PATH` when the source is disabled, empty, malformed, or
unavailable.

LLM runtime defaults are `LLM_TIMEOUT_SECONDS=20` and `LLM_MAX_RETRIES=1`.
Interactive deployments can reduce these values further; missing or timed-out
LLM analysis remains a conservative rejection.

### LLM providers (implemented)

Current implementation: `LLM_PROVIDER` selects one native LangChain adapter for
OpenAI (`langchain-openai`), Gemini
(`langchain-google-genai`), Anthropic (`langchain-anthropic`), and Groq
(`langchain-groq`). The current endpoint remains an explicit
`openai_compatible` gateway adapter for Siemens and compatible services.

Direct adapters are preferred over OpenAI URL emulation: they preserve native
authentication, provider-specific structured output and tool-calling behavior.
Each supported adapter must pass the application contract tests before use.
Unknown or unconfigured provider fails closed (analyst rejection, chat agent
disabled). Provider/model names are recorded as non-secret attribution metadata;
all provider keys remain in `.env`/secret storage and are never logged or
persisted.

## Caching and Reuse (planned T-018)

- Cache derived technical snapshots, RSS headline sets, and LLM catalyst
  assessments when inputs and provider/model versions are unchanged.
- Technical and evidence reuse are explicit and recorded in audit rows through
  cache-hit namespaces. RSS/catalyst cache-hit attribution remains follow-up
  work.
- Invalidate caches on source freshness changes, model/provider changes, or
  strategy/configuration changes. Cache entries use configurable TTLs and live
  in the PostgreSQL database (`research_cache` table).

PostgreSQL database operations (ADR-023):

- PostgreSQL runs as a sidecar container via `docker-compose.yml` (`postgres:16-alpine`).
- Checkpoints and durable interrupts are persisted via `langgraph-checkpoint-postgres` (`PostgresSaver`).
- Long-term memory is persisted via `langgraph.store.postgres` (`PostgresStore`).
- Standard PostgreSQL connection string configured via `DATABASE_URL` in `.env`.

Market macro indicators (ADR-011):

- Sourced automatically from Yahoo Finance (`^NSEI` and `^INDIAVIX`).
- India VIX > 24.0: Blocks new paper trade entries (`allow_new_entries = False`, `risk_multiplier = 0.0`).
- India VIX in [19.0, 24.0]: Halves trade risk budget (`allow_new_entries = True`, `risk_multiplier = 0.5`).
- NIFTY 50 close < 50-day EMA: Blocks long pullback entries (`allow_new_entries = False`).

Multi-strategy screening (ADR-024):

- Supported strategies: `pullback_in_uptrend`, `breakout_momentum`, `bollinger_mean_reversion`.
- Priority hierarchy for candidates matching multiple setups: `BREAKOUT` > `PULLBACK` > `MEAN_REVERSION`.
- Exactly one clean proposal card is pushed to Telegram per ticker per day.

Paper evaluation & benchmark:

- `python -m app.main evaluate` and Telegram `/performance` report closed/open counts,
  gross and net P&L, transaction costs, win rate, expectancy, max drawdown,
  Profit Factor (Gross Wins / Gross Losses), and Realized R-Multiple.
- Benchmark comparator: Net alpha compared against the NIFTY 100 Buy-and-Hold
  return across the identical active paper trading duration.
- Statistical validity rule: A minimum of 30 closed trades is required before
  interpreting Sharpe ratios or win-rate confidence intervals.
- Evaluation is read-only. It does not tune strategies, thresholds, or risk.

Operational status & position tracking (ADR-026):

- Telegram `/status` reports trading mode, provider/model configuration status,
  scan schedule, pending approvals, open paper trades, cache size, outbox
  backlog, database connection status, and bot heartbeat.
- Telegram `/positions` renders a real-time markdown table of open paper trades
  with entry price, current market price, unrealized P&L (₹ and %), stop/target
  distance, and total portfolio capital heat %.
- Proposal cards feature an inline `[🔬 Agent Debate]` button that displays the
  Bear Risk Critic's objections and Bull Momentum thesis on demand.
- Daily Scan Digest: Automatic summary banner sent after the 15:45 IST scan with
  macro regime status, count screened, technical qualifiers, veto breakdown, and
  proposals generated.
- Commands are read-only and do not alter approvals, execution, or settings.

Incremental Market Data Caching (ADR-026):

- Stored in PostgreSQL `ohlcv_daily_bars` table.
- Stores historical daily OHLCV bars; daily scans perform an incremental fetch
  for only the latest daily bar rather than downloading months of history.
- Cuts Yahoo Finance API calls by ~95%, eliminating 401 Crumb and delisting rate-limit errors.

Scan measurement:

- `pipeline.process_symbol` records per-symbol duration in returned state/logging
  context.
- Universe scans log total symbols, qualifiers, proposals, and total duration.
- These measurements precede any LangGraph fan-out change.

LangSmith tracing setup (optional, ADR-021):

1. Create a free account at <https://smith.langchain.com> and generate an API
   key under Settings > API Keys.
2. In `.env`, set:
   ```
   LANGSMITH_TRACING_ENABLED=true
   LANGSMITH_API_KEY=your-langsmith-key
   LANGSMITH_PROJECT=traid-nifty100
   ```
   `LANGSMITH_PROJECT` can be any name — it groups traces in the LangSmith UI.
   Leave `LANGSMITH_ENDPOINT` empty unless using a self-hosted instance.
3. Restart the process (`serve`, `scan`, or `run`). `app.observability.configure()`
   runs once at startup and sets the standard `LANGSMITH_TRACING`/
   `LANGSMITH_API_KEY`/`LANGSMITH_PROJECT` environment variables that the
   already-installed `langsmith` SDK reads automatically — no code changes
   are needed per run.
4. Every LangGraph/LangChain call in that process (catalyst analyst calls,
   chat-agent runs, `graph.run_symbol`/`resume_symbol`) is then traced to the
   configured LangSmith project. View traces at
   <https://smith.langchain.com>.
5. Leaving `LANGSMITH_TRACING_ENABLED=false` (the default) keeps the process
   fully local; no network call to LangSmith is made.
6. `LANGSMITH_API_KEY` is never logged. If tracing is enabled without a key,
   the process logs a warning and stays disabled instead of failing.

Evidence validation:

- `EVIDENCE_MAX_AGE_SECONDS=0` disables the global age gate by default.
- A positive value makes `validate_snapshot` reject evidence older than that
  age, in addition to rejecting `MISSING` and `CONFLICT` statuses.
- `yfinance` frames must contain numeric Open/High/Low/Close/Volume columns and
  non-negative volume before the screener uses them.

Telegram polling network errors are retryable transport failures. The bot logs
them as warnings and lets the polling loop recover; non-network update failures
are logged with their traceback.

Telegram authorization is single-operator: once `TELEGRAM_CHAT_ID` is set,
commands, free-text messages, and approval callbacks from other chats are
rejected. `/start` can bootstrap the first direct chat only while the setting is
empty.

## Planned Sources

| Source type | Preferred starting point | Key | Notes |
| --- | --- | --- | --- |
| NSE corporate filings | NSE corporate-filings pages and session-backed JSON | Usually no | Primary authority; public access is operationally fragile and automated access may require exchange permission |
| BSE corporate filings | BSE corporate pages | Usually no | Primary fallback; JavaScript-heavy and less stable for unattended collection |
| Results and filings | NSE/BSE and company investor-relations pages | Usually no | Store document URL, date, and extracted text hash |
| Corporate actions | NSE/BSE public data | Usually no | Dividends, splits, bonuses, rights, pledges |
| Fundamentals | Official filings first; public data fallback | Usually no | Mark estimates and scraped values clearly |
| Earnings calendar | Exchange/company IR calendars | Usually no | Event-risk gate |
| Sector/index data | NSE Indices historical data and factsheets | Usually no | Regime, breadth, relative strength; public endpoints are not a stable API contract |
| Regulator evidence | SEBI, MCA, and company IR pages | Usually no | Supplemental verification for governance, insider, and filing evidence |
| Alternate OHLCV | Alpha Vantage | `ALPHA_VANTAGE_KEY` | Candidate licensed fallback; free tier is reportedly about 25 requests/day and must be revalidated before scheduled use |
| Alternate OHLCV | EODHD | `EODHD_KEY` | Candidate low-cost EOD fallback; confirm current NSE coverage and quota before adoption |
| Alternate OHLCV | Twelve Data | `TWELVE_DATA_KEY` | Do not plan on the free tier for NSE until coverage is verified; likely paid for this use case |
| Fundamentals aggregator | Screener.in | No official API | Secondary discovery only; scraping and redistribution constraints apply |
| Portfolio context | Groww supported read-only endpoints | Groww credentials | No order endpoints exposed to agents |
| Document extraction | Local PDF/text tooling | No | Prefer local parsing before paid extraction |

## Modernization Dependencies

| Capability | Package or infrastructure | Current status |
| --- | --- | --- |
| Dynamic graph fan-out | Installed LangGraph `Send` API | Planned; requires reducer and orchestration tests |
| LangSmith tracing | `langsmith` SDK (already installed, transitive dependency of `langchain-core`); `LANGSMITH_API_KEY` | Implemented, off by default — see ADR-021 and "LangSmith Tracing Setup" below |
| Long-term memory store | `langgraph.store.postgres.PostgresStore` (via `langgraph-checkpoint-postgres`) | Implemented; backs `app.profile` via `app.store` |
| Time-travel history | `get_state_history()` (built into `langgraph`) | Implemented; `graph.symbol_history`, `history` CLI, `get_symbol_history` chat tool |
| Durability tuning | `durability="sync"` graph invocation argument (built into `langgraph`) | Implemented for `run_symbol`/`resume_symbol` |
| Event-streaming scan progress | `graph.stream_events` / `stream_mode="updates"` | Evaluate as a follow-up; not yet implemented |
| Subgraph specialist analysts | Per-invocation subgraphs (no new checkpointer) | Planned for T-005; not yet implemented |
| Agent Server deploy / Studio | LangGraph CLI, hosted or self-hosted Agent Server | Deferred; requires a new ADR and external service |
| Agent middleware (PII, tool-call limit, summarization) | `langchain.agents.create_agent` + `langchain.agents.middleware` (already installed, `langchain>=1.0.0`) | Implemented in `app.chat_agent` — see ADR-020 |
| Model-fallback / human-in-the-loop / context-editing middleware | Same `langchain.agents.middleware` package | Evaluated, not adopted — conflicts with ADR-016 (fallback), no gated tool exists (HITL), overlaps with summarization (context editing) |
| Web-search/document-loader tools, text splitters | `langchain` tool/loader/splitter integrations | Deferred; require either a new external source (ADR-010 gate) or a new dependency |

## Credentials

- Required today: Telegram bot token/chat id if Telegram control is used.
- Required for hosted LLM analysis: `OPENAI_API_KEY` and optional base URL.
- Optional later: provider-specific market-data keys.
- Optional later: Groww credentials for read-only synchronization only.
- Optional: `LANGSMITH_API_KEY` if LangSmith tracing is explicitly enabled
  (ADR-021); disabled by default.
- Never commit, log, prompt, checkpoint, or export credentials.

## Source Policy

- Prefer official exchange, company, and regulator sources.
- Use aggregators for discovery and redundancy, not as the sole authority for
  material corporate facts.
- Store URL, source name, fetched UTC time, published time, content hash, and
  parser status for every research artifact.
- Do not silently merge conflicting facts. Preserve both values and flag the
  conflict.
- Cache public data and respect provider terms, robots rules, and rate limits.
- Re-check free-tier limits before enabling a new provider in scheduled scans.
- Treat public exchange web pages as source candidates, not guaranteed APIs:
  use low-rate caching, explicit consent/terms review, and a disable switch.
- Do not make a scheduled scan depend on a source whose automated access terms or
  stability are unresolved.

## MCP and Research Tools

- MCP is not a runtime dependency of the application.
- Docs by LangChain MCP may be used while implementing LangGraph integrations.
- Microsoft Docs MCP is relevant only if Azure services are introduced.
- Any future runtime MCP must be explicitly approved in an ADR and must expose
  read-only tools by default.

## External Documentation

- [NSE Indices](https://www.niftyindices.com/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [yfinance](https://ranaroussi.github.io/yfinance/)
- [LangGraph](https://langchain-ai.github.io/langgraph/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)

Links are implementation references, not guarantees of availability or quota.

## Research Findings And Open Verification

- NSE corporate filings are the preferred authority for announcements, results,
  board meetings, and corporate actions, but the public web/session endpoints
  can change and may not authorize unattended scraping. Verify current terms
  before implementation.
- BSE is a useful official fallback, but its pages are more difficult to
  collect reliably and should not be treated as equivalent operationally.
- NSE Indices is the preferred authority for index and sector context, but its
  public historical-data access is not a stable public API contract.
- Alpha Vantage is the first alternate OHLCV candidate to evaluate. Its free
  quota is too small for an unbounded NIFTY 100 fallback, so caching and
  selective use are mandatory.
- Twelve Data should not be selected for NSE on the assumption that its free
  tier covers the required market. Verify coverage first or exclude it.
- Groww must remain a capability check until the operator confirms the actual
  supported read-only endpoints and credential scope. Do not use session-token
  scraping as an implicit integration.

## Open Product Decisions

- Whether v1 stays NIFTY 100-only or allows user-provided custom lists.
- Whether BSE is in scope for v1 or deferred behind the agentic platform.
- Which source will become the authoritative full symbol master once the scope
  expands.

## Phase 2 Source Policy Definitions

### Stale data

Data is stale when its age exceeds the accepted freshness limit for its source
and data class, or when its trading date does not represent the latest required
market session. The exact limits are intentionally not fixed yet. Examples:

- A daily OHLCV snapshot older than the latest required trading session.
- A corporate event feed that has not refreshed within its approved window.
- A cached headline set used beyond its configured TTL.

### Conflicting data

Data conflicts when two independently retrieved records for the same identity,
fact, and event window disagree beyond an accepted tolerance. Examples:

- Different closing prices for the same symbol and trading date.
- Different event dates or event types for the same company disclosure.
- Different ISIN-to-symbol mappings for the same instrument.

The system must preserve both records, mark the evidence `CONFLICT`, and fail
closed for proposal generation until an authority rule is accepted.

### Source authority

Until Phase 2 accepts an authority hierarchy, TrAId must not silently choose one
conflicting source over another. The current safe default is:

1. Preserve both values and provenance.
2. Mark the evidence as conflicting.
3. Do not generate a proposal from the conflict.
4. Allow a research-only explanation of the conflict.

Candidate trusted source classes for corporate events are NSE corporate filings,
BSE corporate filings, company investor-relations disclosures, and SEBI/regulator
records. Public access stability and automation terms must be verified before a
source becomes scheduled input.
