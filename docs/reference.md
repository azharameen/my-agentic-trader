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

## Planned Sources

| Source type | Preferred starting point | Key | Notes |
| --- | --- | --- | --- |
| Corporate announcements | NSE/BSE public pages and feeds | Usually no | Highest-priority missing catalyst source |
| Results and filings | NSE/BSE and company investor-relations pages | Usually no | Store document URL, date, and extracted text hash |
| Corporate actions | NSE/BSE public data | Usually no | Dividends, splits, bonuses, rights, pledges |
| Fundamentals | Official filings first; public data fallback | Usually no | Mark estimates and scraped values clearly |
| Earnings calendar | Exchange/company IR calendars | Usually no | Event-risk gate |
| Sector/index data | NSE indices public data | Usually no | Regime, breadth, relative strength |
| Alternate OHLCV | Alpha Vantage or Twelve Data free tier | Provider-specific | Optional fallback; confirm current limits before use |
| Portfolio context | Groww supported read-only endpoints | Groww credentials | No order endpoints exposed to agents |
| Document extraction | Local PDF/text tooling | No | Prefer local parsing before paid extraction |

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
