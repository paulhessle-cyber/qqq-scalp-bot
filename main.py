"""
QQQ Morning Scalp Bot
Strategy: First 5-min candle breakout after market open
Active window: 9:30–10:00 AM ET only
Broker: Interactive Brokers (paper or live)
"""

import asyncio
import logging
import sys
from datetime import datetime, time
import pytz

from market_data import get_first_5min_candle
from strategy import evaluate_signal
from trade import place_bracket_order, cancel_all_open_orders
from notifier import send_telegram

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

ET = pytz.timezone("America/New_York")

MAX_TRADES_PER_DAY = 1


async def run_bot():
    now_et = datetime.now(ET)
    log.info(f"Bot started at {now_et.strftime('%Y-%m-%d %H:%M:%S ET')}")

    # Safety: only run on weekdays
    if now_et.weekday() >= 5:
        log.info("Weekend — bot exiting.")
        await send_telegram("⏸ QQQ Bot: Weekend detected, no trades today.")
        return

    # Safety: only run in the 9:30–10:00 AM window
    window_start = time(9, 28)   # start slightly early to catch the open
    window_end   = time(10, 0)
    current_time = now_et.time()

    if not (window_start <= current_time <= window_end):
        log.warning(f"Outside trading window ({current_time}). Exiting.")
        return

    trades_placed = 0

    log.info("Waiting for the 9:30–9:35 candle to close...")
    candle = await get_first_5min_candle()

    if candle is None:
        msg = "❌ QQQ Bot: Could not retrieve opening candle. No trade today."
        log.error(msg)
        await send_telegram(msg)
        return

    log.info(
        f"Opening candle — O:{candle['open']:.2f} H:{candle['high']:.2f} "
        f"L:{candle['low']:.2f} C:{candle['close']:.2f}"
    )

    signal = evaluate_signal(candle)

    if signal is None:
        msg = "⚠️ QQQ Bot: No clear signal from opening candle. Sitting out today."
        log.info(msg)
        await send_telegram(msg)
        return

    if trades_placed >= MAX_TRADES_PER_DAY:
        log.info("Daily trade limit reached.")
        return

    direction   = signal["direction"]
    entry       = signal["entry"]
    stop        = signal["stop"]
    target      = signal["target"]
    risk_reward = signal["risk_reward"]

    log.info(f"Signal: {direction.upper()} | Entry:{entry:.2f} Stop:{stop:.2f} Target:{target:.2f} R:R {risk_reward:.1f}")

    order_result = await place_bracket_order(
        direction=direction,
        entry=entry,
        stop=stop,
        target=target,
    )

    if order_result["success"]:
        trades_placed += 1
        msg = (
            f"{'🟢' if direction == 'long' else '🔴'} *QQQ Scalp Trade Placed*\n\n"
            f"Direction: *{direction.upper()}*\n"
            f"Entry:  `${entry:.2f}`\n"
            f"Stop:   `${stop:.2f}`\n"
            f"Target: `${target:.2f}`\n"
            f"R:R     `1:{risk_reward:.1f}`\n"
            f"Order ID: `{order_result['order_id']}`\n\n"
            f"_Orders will auto-cancel if unfilled by 10:00 AM ET_"
        )
        await send_telegram(msg, parse_mode="Markdown")
        log.info("Trade placed and Telegram alert sent.")
    else:
        msg = f"❌ QQQ Bot: Order failed — {order_result['error']}"
        log.error(msg)
        await send_telegram(msg)
        return

    # ── Hold until 10:00 AM then cancel any unfilled orders ──
    while True:
        now_et = datetime.now(ET)
        if now_et.time() >= window_end:
            log.info("10:00 AM reached — cancelling any unfilled orders.")
            await cancel_all_open_orders()
            await send_telegram("🔔 QQQ Bot: Trading window closed. Any unfilled orders cancelled.")
            break
        await asyncio.sleep(15)


if __name__ == "__main__":
    asyncio.run(run_bot())
