"""
CSPX Morning Alert Bot
---------------------
Strategy:
  1. 8:00-8:30 AM London time - record the 30-min opening candle BODY (no wicks)
  2. 8:30 AM onwards          - watch 1-min candles
                                 body breaks above body_high -> LONG alert
                                 body breaks below body_low  -> SHORT alert
  3. One alert max, stop at 9:00 AM London time
"""

import time
import logging
import sys
from datetime import datetime, time as dtime
import pytz
import httpx

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")
TWELVE_DATA_KEY    = os.getenv("TWELVE_DATA_KEY", "")
TICKER             = os.getenv("TICKER", "CSPX.L")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)
LONDON = pytz.timezone("Europe/London")


def now_london():
    return datetime.now(LONDON)


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


def fetch_1min_candles():
    """Fetch today's 1-min candles from Twelve Data."""
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol":      TICKER,
        "interval":    "1min",
        "outputsize":  "90",
        "timezone":    "Europe/London",
        "apikey":      TWELVE_DATA_KEY,
    }
    try:
        r = httpx.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()

        if data.get("status") == "error":
            log.error(f"Twelve Data error: {data.get('message')}")
            return None

        values = data.get("values", [])
        if not values:
            log.error("No values returned from Twelve Data.")
            return None

        today = now_london().strftime("%Y-%m-%d")
        candles = []
        for v in values:
            if v["datetime"].startswith(today):
                dt = LONDON.localize(datetime.strptime(v["datetime"], "%Y-%m-%d %H:%M:%S"))
                candles.append({
                    "dt":    dt,
                    "open":  float(v["open"]),
                    "close": float(v["close"]),
                })

        candles.sort(key=lambda x: x["dt"])
        log.info(f"Fetched {len(candles)} candles from Twelve Data.")
        return candles

    except Exception as e:
        log.error(f"Twelve Data fetch failed: {e}")
        return None


def get_30min_body(candles):
    window = [
        c for c in candles
        if dtime(8, 0) <= c["dt"].time() < dtime(8, 30)
    ]
    if not window:
        log.warning("No candles in 8:00-8:30 window.")
        return None, None

    body_high = max(max(c["open"], c["close"]) for c in window)
    body_low  = min(min(c["open"], c["close"]) for c in window)
    log.info(f"30-min body - High: ${body_high:.2f} | Low: ${body_low:.2f}")
    return body_high, body_low


def run():
    log.info(f"CSPX Alert Bot started - {now_london().strftime('%Y-%m-%d %H:%M London')}")

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env")
        sys.exit(1)

    if not TWELVE_DATA_KEY:
        log.error("Missing TWELVE_DATA_KEY in .env")
        sys.exit(1)

    if now_london().weekday() >= 5:
        log.info("Weekend - exiting.")
        send_telegram("CSPX Bot: Weekend, no alert today.")
        return

    # Wait until 8:30 AM London time
    target = now_london().replace(hour=8, minute=30, second=5, microsecond=0)
    wait = (target - now_london()).total_seconds()
    if wait > 0:
        log.info(f"Waiting {wait:.0f}s until 8:30 AM London time...")
        time.sleep(wait)

    # Fetch candles and get opening body
    candles = fetch_1min_candles()
    if not candles:
        send_telegram("CSPX Bot: Could not fetch market data today.")
        return

    body_high, body_low = get_30min_body(candles)
    if body_high is None:
        send_telegram("CSPX Bot: No data in 8:00-8:30 window today.")
        return

    log.info(f"Watching - Body High: {body_high:.2f} | Body Low: {body_low:.2f}")
    send_telegram(
        f"*CSPX Bot Active*\n\n"
        f"Opening body range:\n"
        f"Upper: `{body_high:.2f}`\n"
        f"Lower: `{body_low:.2f}`\n\n"
        f"_Watching 1-min candles for a body breakout..._"
    )

    alert_sent = False
    stop_time  = dtime(9, 0)

    while not alert_sent:
        current = now_london()

        if current.time() >= stop_time:
            log.info("9:00 AM - no breakout today.")
            send_telegram("*CSPX Bot*: No breakout before 9:00 AM. No trade today.")
            break

        time.sleep(60)

        candles = fetch_1min_candles()
        if not candles:
            log.warning("Could not fetch candles, retrying...")
            continue

        latest = candles[-1]
        candle_body_high = max(latest["open"], latest["close"])
        candle_body_low  = min(latest["open"], latest["close"])

        log.info(
            f"{current.strftime('%H:%M')} - "
            f"Body: {candle_body_low:.2f}-{candle_body_high:.2f} | "
            f"Range: {body_low:.2f}-{body_high:.2f}"
        )

        if candle_body_high > body_high:
            send_telegram(
                f"*CSPX LONG Signal!*\n\n"
                f"1-min candle body broke *above* the opening range\n\n"
                f"Opening body high: `{body_high:.2f}`\n"
                f"Candle body high: `{candle_body_high:.2f}`\n\n"
                f"*Look at CSPX now - consider a LONG entry*"
            )
            log.info("LONG alert sent.")
            alert_sent = True

        elif candle_body_low < body_low:
            send_telegram(
                f"*CSPX SHORT Signal!*\n\n"
                f"1-min candle body broke *below* the opening range\n\n"
                f"Opening body low: `{body_low:.2f}`\n"
                f"Candle body low: `{candle_body_low:.2f}`\n\n"
                f"*Look at CSPX now - consider a SHORT entry*"
            )
            log.info("SHORT alert sent.")
            alert_sent = True

    log.info("Bot finished.")


if __name__ == "__main__":
    run()
