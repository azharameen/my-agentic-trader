"""
Telegram Human-in-the-Loop interface.

Uses `python-telegram-bot` with **long polling** (`Application.builder().build()`),
so no public IP, webhook or SSL certificate is required — ideal for a local
Docker deployment.

Responsibilities:
  * Format a Markdown trade-proposal card from the interrupt payload.
  * Attach inline approval buttons:
      - [ ✅ Approve Trade ]  -> resume the LangGraph thread with "APPROVED"
      - [ ❌ Reject ]          -> resume with "REJECTED"
  * Wire button callbacks back into `graph.resume_symbol(...)`.
  * Commands: /scan, /run SYMBOL, /trades.
  * Free-text messages are routed to the conversational research agent
    (app/chat_agent.py), which is read/trigger-only.

The bot is a thin transport layer: it never computes prices or sizes. It only
forwards the human's decision into the graph.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config.settings import get_settings
from app import chat_agent, executor, universe

logger = logging.getLogger(__name__)

# Callback data prefixes. The symbol is appended after the colon so a single
# callback handler can dispatch on the action.
APPROVE = "approve"
REJECT = "reject"


def _format_proposal_card(payload: dict) -> str:
    """Render the interrupt payload as a Markdown proposal card."""
    return (
        "📊 *Trade Proposal*\n"
        f"Symbol: *{payload.get('symbol', '?')}*\n"
        f"Entry: ₹{payload.get('entry_price', 0):.2f}\n"
        f"Soft Stop: ₹{payload.get('soft_stop', 0):.2f}\n"
        f"Hard Stop: ₹{payload.get('hard_stop', 0):.2f}\n"
        f"Target: ₹{payload.get('target_price', 0):.2f}\n"
        f"Quantity: {payload.get('quantity', 0)}\n"
        f"Risk: ₹{payload.get('risk_amount', 0):.2f}\n"
        f"R:R: {payload.get('risk_to_reward', 0):.2f}\n"
        f"Catalyst: {payload.get('catalyst_type', 'UNKNOWN')}\n"
        f"_Thesis: {payload.get('thesis', '')}_"
    )


def _build_keyboard(symbol: str) -> InlineKeyboardMarkup:
    """Build the inline approval keyboard for a given symbol."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve Trade", callback_data=f"{APPROVE}:{symbol}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"{REJECT}:{symbol}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def _auto_configure_chat_id(chat_id: int) -> bool:
    """Persist the operator's chat id to `.env` if it differs from config.

    A bot cannot discover the operator's chat id until the operator messages
    it, so the first `/start` is used to self-configure. Writes via a
    temp-file-then-rename so a crash mid-write never corrupts `.env`, and
    clears the cached `Settings` so this same process picks up the new value
    immediately (no restart needed).
    """
    settings = get_settings()
    if settings.TELEGRAM_CHAT_ID and str(chat_id) != settings.TELEGRAM_CHAT_ID:
        logger.warning(
            "TELEGRAM_CHAT_ID is already configured; refusing to overwrite it from chat %s.",
            chat_id,
        )
        return False
    if str(chat_id) == settings.TELEGRAM_CHAT_ID:
        return False
    try:
        env_path = Path(".env")
        lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
        replaced = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#") or "=" not in stripped:
                continue
            key = stripped.split("=", 1)[0].strip()
            if key == "TELEGRAM_CHAT_ID":
                lines[i] = f"TELEGRAM_CHAT_ID={chat_id}"
                replaced = True
                break
        if not replaced:
            lines.append(f"TELEGRAM_CHAT_ID={chat_id}")

        tmp_path = env_path.with_suffix(".env.tmp")
        tmp_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        tmp_path.replace(env_path)

        get_settings.cache_clear()
        logger.info("Auto-configured TELEGRAM_CHAT_ID=%s in .env", chat_id)
        return True
    except Exception as exc:  # noqa: BLE001 - never break /start over config
        logger.exception("Could not auto-configure TELEGRAM_CHAT_ID: %s", exc)
        return False


async def _on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Greet the operator on /start and self-configure the chat id."""
    chat_id = update.effective_chat.id
    updated = _auto_configure_chat_id(chat_id)
    note = (
        "\n\n✅ Chat id auto-saved to .env — proposals will now be delivered here."
        if updated
        else ""
    )
    await update.message.reply_text(
        "\U0001F916 NIFTY 100 Swing Trading Assistant online.\n"
        "Commands:\n"
        "/scan — screen the NIFTY 100 universe & push proposals\n"
        "/run SYMBOL — run one symbol through the pipeline\n"
        "/trades — show the audit log (open & closed paper trades)\n"
        "/pending — list proposals awaiting your approval\n"
        "Approve / reject proposals via the inline buttons.\n"
        "Or just ask me anything in plain text — e.g. 'why did TITAN qualify?',\n"
        "'what are my open trades?', 'status of JSWSTEEL'." + note
    )


def _format_trades() -> str:
    """Render the audit log as a compact Telegram message."""
    trades = executor.fetch_all_trades()
    if not trades:
        return "📭 No trades in the audit log yet. Run /scan to generate proposals."

    open_trades = [t for t in trades if t["status"] == "OPEN_PAPER"]
    closed = [t for t in trades if t["status"] == "CLOSED"]
    realized = sum(t.get("realized_pnl") or 0 for t in closed)

    lines = [
        f"📒 *Audit Log* — {len(trades)} trade(s)",
        f"Open: {len(open_trades)} | Closed: {len(closed)} | Realized P&L: ₹{realized:,.2f}",
        "",
    ]
    for t in trades[:20]:  # cap message length
        pnl = f" | P&L ₹{t['realized_pnl']:+,.2f}" if t["status"] == "CLOSED" else ""
        lines.append(
            f"• *{t['symbol']}* [{t['status']}]\n"
            f"  fill ₹{t['fill_price']:,.2f} × {t['quantity']} | "
            f"stop ₹{t['hard_stop']:,.2f} | target ₹{t['target_price']:,.2f}{pnl}"
        )
    if len(trades) > 20:
        lines.append(f"…and {len(trades) - 20} more.")
    return "\n".join(lines)


def _run_pipeline_in_thread(update: Update, symbol: Optional[str]) -> None:
    """Run the (blocking) pipeline off the event loop, then report back.

    The pipeline does yfinance downloads + LLM calls, which can take minutes.
    Running it on the bot's event loop would stall polling, so it goes on a
    worker thread. Proposals are pushed to Telegram by the pipeline itself.
    """
    import threading

    def _work() -> None:
        from app import pipeline

        try:
            if symbol:
                pipeline.process_symbol(symbol)
                summary = f"✅ Finished processing *{symbol}*."
            else:
                proposed = pipeline.run_universe_scan(universe.get_universe())
                summary = (
                    f"✅ Scan complete. {len(proposed)} proposal(s) sent: "
                    + (", ".join(proposed) if proposed else "none qualified.")
                )
        except pipeline.ScanInProgressError:
            summary = "⏳ A scan is already running. Try again once it finishes."
        except Exception as exc:  # noqa: BLE001
            summary = f"⚠️ Pipeline error: {exc}"
        # Deliver the summary on the bot's loop (thread-safe).
        if _bot_loop is not None:
            import asyncio

            asyncio.run_coroutine_threadsafe(
                update.message.reply_text(summary, parse_mode="Markdown"), _bot_loop
            )

    threading.Thread(target=_work, name="pipeline-worker", daemon=True).start()


async def _on_scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /scan — screen the universe and push proposals."""
    await update.message.reply_text("🔍 Scanning the NIFTY 100 universe… this takes a few minutes.")
    _run_pipeline_in_thread(update, symbol=None)


async def _on_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /run SYMBOL — run a single symbol through the pipeline."""
    args = (context.args or [])
    if not args:
        await update.message.reply_text("Usage: /run SYMBOL  (e.g. /run RELIANCE)")
        return
    symbol = args[0].upper()
    await update.message.reply_text(f"🔍 Running *{symbol}* through the pipeline…", parse_mode="Markdown")
    _run_pipeline_in_thread(update, symbol=symbol)


async def _on_trades(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /trades — show the audit log."""
    await update.message.reply_text(_format_trades(), parse_mode="Markdown")


def _format_pending() -> str:
    """Render every thread currently paused at human_approval."""
    from app import graph

    pending = graph.list_pending_approvals()
    if not pending:
        return "📭 No proposals are currently awaiting approval."
    lines = [f"⏳ *{len(pending)} proposal(s) awaiting approval*", ""]
    for card in pending:
        lines.append(
            f"• *{card.get('symbol', '?')}* entry ₹{card.get('entry_price', 0):.2f} "
            f"target ₹{card.get('target_price', 0):.2f} (proposed {card.get('proposed_at', '?')})"
        )
    return "\n".join(lines)


async def _on_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /pending — list proposals awaiting approval."""
    await update.message.reply_text(_format_pending(), parse_mode="Markdown")


async def _on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button presses and resume the paused graph thread."""
    from app import graph

    query = update.callback_query
    await query.answer()

    try:
        action, symbol = query.data.split(":", 1)
    except ValueError:
        await query.edit_reply_text("⚠️ Malformed callback.")
        return

    if action == APPROVE:
        result = graph.resume_symbol(symbol, "APPROVED")
        await query.edit_reply_text(f"✅ *Approved* {symbol}\n{result.get('execution_details', {})}")
    elif action == REJECT:
        graph.resume_symbol(symbol, "REJECTED")
        await query.edit_reply_text(f"❌ *Rejected* {symbol}. No order placed.")
    else:
        await query.edit_reply_text(f"⚠️ Unknown action: {action}")

async def _on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route free-text messages to the conversational research agent.

    The agent is blocking (LLM + possibly yfinance), so it runs on a worker
    thread; the reply is delivered back on the bot's event loop.
    """
    question = (update.message.text or "").strip()
    if not question:
        return
    await update.message.reply_text("🤔 Thinking…")

    import threading

    def _work() -> None:
        from app import chat_agent

        thread_id = f"telegram-chat-{update.effective_chat.id}"
        answer = chat_agent.ask(question, thread_id=thread_id)
        if _bot_loop is not None:
            import asyncio

            asyncio.run_coroutine_threadsafe(
                update.message.reply_text(answer[:4000]), _bot_loop
            )

    threading.Thread(target=_work, name="chat-agent-worker", daemon=True).start()


def _send_via_bot_api(token: str, chat_id: str, text: str, markup: InlineKeyboardMarkup) -> bool:
    """Push a proposal directly via the Telegram Bot API over HTTP.

    Used when the long-polling bot is NOT running in this process (e.g.
    `scan`/`run` invoked separately from `serve`). A plain HTTPS POST to
    `sendMessage` needs no event loop and works from any process.
    """
    import json

    import requests

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": json.loads(markup.to_json()),
    }
    resp = _post_telegram_message(url, body)
    if resp.status_code == 400:
        # Markdown parse failure (e.g. special chars in the LLM thesis) —
        # retry as plain text so the proposal is never lost.
        body.pop("parse_mode")
        resp = _post_telegram_message(url, body)
    if resp.status_code != 200:
        logger.error("Telegram push failed: HTTP %s %s", resp.status_code, resp.text)
        return False
    else:
        logger.info("Proposal pushed to Telegram via Bot API.")
        return True


def _post_telegram_message(url: str, body: dict):
    import requests

    return requests.post(url, json=body, timeout=15)


def send_proposal_to_chat(chat_id: str, payload: dict) -> bool:
    """Push a proposal card (with buttons) to the configured chat.

    Called from `main.py` when a thread pauses at `human_approval`.

    If the long-polling bot is running in this process, the message goes
    through its event loop; otherwise it falls back to a direct Bot API
    HTTP call so `scan`/`run` work even when `serve` runs elsewhere.
    """
    settings = get_settings()
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured; cannot push proposal for %s.", payload.get("symbol"))
        return False

    text = _format_proposal_card(payload)
    markup = _build_keyboard(payload.get("symbol", ""))

    if _running_application is None:
        return _send_via_bot_api(settings.TELEGRAM_BOT_TOKEN, chat_id, text, markup)

    # This helper is invoked from a non-async context (pipeline worker thread
    # or CLI process). Schedule the send on the bot's own event loop so the
    # httpx client is always used from the loop it was created on.
    import asyncio

    async def _push() -> None:
        await _running_application.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=markup,
            parse_mode="Markdown",
        )

    if _bot_loop is not None and _bot_loop.is_running():
        asyncio.run_coroutine_threadsafe(_push(), _bot_loop)
        return True
    else:
        # Bot loop not available (e.g. called from a separate CLI process
        # before start_bot ran) — fall back to a direct Bot API HTTP call.
        return _send_via_bot_api(settings.TELEGRAM_BOT_TOKEN, chat_id, text, markup)


def notify_text(chat_id: str, text: str) -> None:
    """Push a plain Markdown text notification (no buttons) to the operator.

    Used for out-of-band notices that aren't tied to a trade proposal, e.g.
    the monthly universe-refresh diff or the position-monitor close summary.
    """
    settings = get_settings()
    if not settings.TELEGRAM_BOT_TOKEN or not chat_id:
        logger.warning("Telegram not configured; cannot send notification.")
        return

    if _bot_loop is not None and _bot_loop.is_running() and _running_application is not None:
        import asyncio

        async def _push() -> None:
            await _running_application.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")

        asyncio.run_coroutine_threadsafe(_push(), _bot_loop)
    else:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = _post_telegram_message(
            url, {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        )
        if resp.status_code == 400:
            resp = _post_telegram_message(url, {"chat_id": chat_id, "text": text})
        if resp.status_code != 200:
            logger.error("Telegram notification failed: HTTP %s %s", resp.status_code, resp.text)


# Backwards-compatible alias for older internal callers.
_send_proposal_to_chat = send_proposal_to_chat

# Set by start_bot() so send_proposal_to_chat can reach the live application.
_running_application: Optional[Application] = None
# The bot's event loop, captured in start_bot() for thread-safe scheduling.
_bot_loop: Optional["asyncio.AbstractEventLoop"] = None


async def _capture_loop(application: Application) -> None:
    """Record the running event loop (PTB post_init hook, runs in the loop)."""
    global _bot_loop
    import asyncio

    _bot_loop = asyncio.get_running_loop()
    await asyncio.sleep(0)


_HEARTBEAT_PATH = Path("data/bot_heartbeat")


async def _write_heartbeat(context: ContextTypes.DEFAULT_TYPE) -> None:
    """JobQueue tick: touch a heartbeat file so the Docker healthcheck can
    detect a hung polling loop, not just a dead process."""
    try:
        _HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
        _HEARTBEAT_PATH.write_text(str(time.time()), encoding="utf-8")
        import asyncio

        await asyncio.sleep(0)
    except OSError as exc:
        logger.warning("Could not write heartbeat file: %s", exc)


def start_bot() -> None:
    """Build and start the long-polling Telegram bot (blocking).

    Long polling means the bot opens outbound HTTPS connections to Telegram,
    so it works from a private Docker network with no inbound ports.
    """
    global _running_application
    settings = get_settings()
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set; HITL bot disabled.")
        return

    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    _running_application = application

    application.add_handler(CommandHandler("start", _on_start))
    application.add_handler(CommandHandler("scan", _on_scan))
    application.add_handler(CommandHandler("run", _on_run))
    application.add_handler(CommandHandler("trades", _on_trades))
    application.add_handler(CommandHandler("pending", _on_pending))
    application.add_handler(CallbackQueryHandler(_on_callback))
    # Free text (non-command) goes to the conversational research agent.
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _on_message))
    # Capture the loop as soon as it starts so other threads can schedule work.
    application.post_init = _capture_loop
    if application.job_queue is not None:
        application.job_queue.run_repeating(_write_heartbeat, interval=30, first=0)

    logger.info("Starting Telegram long-polling bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
