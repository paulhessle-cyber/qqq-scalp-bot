"""
QQQ Morning Alert Bot
---------------------
Strategy:
  1. 9:00–9:30 AM ET  — record the 30-min opening candle BODY (no wicks)
                         body_high = max(open, close)
                         body_low  = min(open, close)
  2. 9:30 AM onwards  — watch 1-min candles
                         if a candle BODY breaks above body_high → send LONG alert
                         if a candle BODY breaks below body_low  → send SHORT alert
  3. One alert max, stop at 10:00 AM ET
"""

import time
import logging
import sys
from datetime import datetime, time as dtime
import pytz
import httpx
import yfinance as yf

# ── Load .env if present ─────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")
TICKER             = os.getenv("TICKER", "QQQ")

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

ET = pytz.timezone("America/New_York")


def now_et():
    return datetime.now(ET)


def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = httpx.post(url, json={
            "chat_id":    TELEGRAM_CHAT_ID,
            "text":       message,
            "parse_mode": "Markdown",
        }, timeout=10)
        r.raise_for_status()
        log.info("Telegram message sent.")
    except Exception as e:
        log.error(f"Telegram failed: {e}")


def get_30min_body():
    """
    Fetch the 9:00–9:30 ET candle body for QQQ.
    Returns (body_high, body_low) using open/close only (no wicks).
    """
    log.info("Fetching 30-min opening candle (9:00–9:30 ET)...")
    ticker = yf.Ticker(TICKER)

    # Fetch today's 1-min data and build the 9:00–9:30 window manually
    df = ticker.history(period="1d", interval="1m")

    if df.empty:
        log.error("No data returned from Yahoo Finance.")
        return None, None

    # Convert index to ET
    df.index = df.index.tz_convert(ET)

    # Filter to 9:00–9:30 AM ET (pre-market opens at 9:00 for some data)
    window = df.between_time("09:00", "09:29")

    if window.empty:
        log.warning("No candles found in 9:00–9:30 window.")
        return None, None

    # Body = max/min of open and close across all 1-min candles in window
    body_high = max(window["Open"].max(), window["Close"].max())
    body_low  = min(window["Open"].min(), window["Close"].min())

    log.info(f"30-min body — High: ${body_high:.2f} | Low: ${body_low:.2f}")
    return body_high, body_low


def get_latest_1min_candle():
    """Returns the most recent completed 1-min candle as (open, close)."""
    ticker = yf.Ticker(TICKER)
    df = ticker.history(period="1d", interval="1m")

    if df.empty:
        return None, None

    df.index = df.index.tz_convert(ET)

    # Get the last completed candle (second to last row, last may be forming)
    if len(df) < 2:
        return None, None

    candle = df.iloc[-2]
    return candle["Open"], candle["Close"]


def run():
    log.info(f"QQQ Alert Bot started — {now_et().strftime('%Y-%m-%d %H:%M ET')}")

    # ── Validation ────────────────────────────────────────────────────────────
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env")
        sys.exit(1)

    # ── Weekend check ─────────────────────────────────────────────────────────
    if now_et().weekday() >= 5:
        log.info("Weekend — exiting.")
        send_telegram("⏸ QQQ Bot: Weekend, no alert today.")
        return

    # ── Wait until 9:30 AM ET ─────────────────────────────────────────────────
    target = now_et().replace(hour=9, minute=30, second=5, microsecond=0)
    wait = (target - now_et()).total_seconds()
    if wait > 0:
        log.info(f"Waiting {wait:.0f}s until 9:30 AM ET...")
        time.sleep(wait)

    # ── Get the 30-min opening body ───────────────────────────────────────────
    body_high, body_low = get_30min_body()

    if body_high is None or body_low is None:
        send_telegram("❌ QQQ Bot: Could not fetch opening candle data today.")
        return

    log.info(f"Watching for breakout — Body High: ${body_high:.2f} | Body Low: ${body_low:.2f}")
    send_telegram(
        f"👀 *QQQ Bot Active*\n\n"
        f"Opening body range set:\n"
        f"Upper: `${body_high:.2f}`\n"
        f"Lower: `${body_low:.2f}`\n\n"
        f"_Watching 1-min candles for a body breakout..._"
    )

    # ── Watch 1-min candles until 10:00 AM ───────────────────────────────────
    alert_sent = False
    stop_time  = dtime(10, 0)

    while not alert_sent:
        current = now_et()

        if current.time() >= stop_time:
            log.info("10:00 AM reached — no breakout today.")
            send_telegram("⏹ *QQQ Bot*: No body breakout before 10:00 AM. No trade today.")
            break

        candle_open, candle_close = get_latest_1min_candle()

        if candle_open is None:
            log.warning("Could not fetch 1-min candle, retrying...")
            time.sleep(15)
            continue

        candle_body_high = max(candle_open, candle_close)
        candle_body_low  = min(candle_open, candle_close)

        log.info(
            f"{current.strftime('%H:%M')} — "
            f"Candle body: ${candle_body_low:.2f}–${candle_body_high:.2f} | "
            f"Watching: ${body_low:.2f}–${body_high:.2f}"
        )

        # ── LONG breakout ────────────────────────────────────────────────────
        if candle_body_high > body_high:
            msg = (
                f"🟢 *QQQ LONG Signal!*\n\n"
                f"A 1-min candle body has broken *above* the opening range.\n\n"
                f"Opening body high: `${body_high:.2f}`\n"
                f"Current candle body high: `${candle_body_high:.2f}`\n\n"
                f"⚡ *Look at QQQ now — consider a LONG entry*\n"
                f"_Check your chart and manage your own entry/exit_"
            )
            send_telegram(msg)
            log.info("LONG alert sent.")
            alert_sent = True

        # ── SHORT breakout ───────────────────────────────────────────────────
        elif candle_body_low < body_low:
            msg = (
                f"🔴 *QQQ SHORT Signal!*\n\n"
                f"A 1-min candle body has broken *below* the opening range.\n\n"
                f"Opening body low: `${body_low:.2f}`\n"
                f"Current candle body low: `${candle_body_low:.2f}`\n\n"
                f"⚡ *Look at QQQ now — consider a SHORT entry*\n"
                f"_Check your chart and manage your own entry/exit_"
            )
            send_telegram(msg)
            log.info("SHORT alert sent.")
            alert_sent = True

        else:
            # No breakout yet — check again in 30 seconds
            time.sleep(30)

    log.info("Bot finished.")


if __name__ == "__main__":
    run()
