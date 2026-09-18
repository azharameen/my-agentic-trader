# References

This is the source-of-truth catalog for external data, APIs, credentials, and
research tooling. Every adapter must document its access method, freshness,
limits, fallback, and validation behavior here before implementation.

## Current Sources

| Source | Data | Access | Key | Cost | Trust and use |
| --- | --- | --- | --- | --- | --- |
| NSE Indices | NIFTY 100 constituents, industry, ISIN | Public CSV | No | Free | Primary universe source |
| Yahoo Finance via `yfinance` | Daily OHLCV | Python library/public endpoint | No | Free | Current price baseline; validate and cache |
| Economic Times RSS | Market headlines | RSS | No | Free | Candidate news evidence |
| Moneycontrol RSS | Business headlines | RSS | No | Free | Candidate news evidence |
| Business Standard RSS | Market headlines | RSS | No | Free | Candidate news evidence |
| OpenAI-compatible endpoint | Structured qualitative analysis | HTTP API | `OPENAI_API_KEY` | Depends on provider | Optional; never source of numeric facts |
| Telegram Bot API | Human review and notifications | Bot API | `TELEGRAM_BOT_TOKEN` | Free | Control plane only |
| SQLite | Audit, checkpoints, outbox | Local database | No | Free | System record |
| Evidence snapshot store | Normalized evidence and provenance | SQLite | No | Free | Immutable per-run research record |

Corporate-event collection is intentionally not enabled until concrete NSE/BSE
access methods and terms are reviewed. The normalized contract currently accepts
earnings, board meetings, dividends, splits, bonuses, rights, pledges, and
announcements with symbol/ISIN identity and provenance.

The current adapter is disabled by default. Set `CORPORATE_EVENTS_ENABLED=true`
and provide `CORPORATE_EVENTS_SOURCE_URL` only for a reviewed source returning
normalized JSON event rows. It falls back to
`CORPORATE_EVENTS_CACHE_PATH` when the source is disabled, empty, malformed, or
unavailable.

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
| LangSmith tracing | LangSmith credentials and runtime configuration | Optional; must not log secrets or full sensitive prompts |

## Credentials

- Required today: Telegram bot token/chat id if Telegram control is used.
- Required for hosted LLM analysis: `OPENAI_API_KEY` and optional base URL.
- Optional later: provider-specific market-data keys.
- Optional later: Groww credentials for read-only synchronization only.
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
