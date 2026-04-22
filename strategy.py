"""
Strategy: First 5-minute candle breakout
  - Bullish candle → Long entry above the high, stop below the low
  - Bearish candle → Short entry below the low, stop above the high
  - Take profit at 2:1 reward-to-risk
  - Minimum candle body size filter to avoid inside/doji candles
"""

import logging
from config import settings

log = logging.getLogger(__name__)

RISK_REWARD_RATIO = 2.0          # Target = 2× the risk
MIN_CANDLE_RANGE_PCT = 0.001     # Ignore tiny candles < 0.1% range (avoids dojis)
BUFFER_TICKS = 0.05              # Cents above/below candle for limit order


def evaluate_signal(candle: dict) -> dict | None:
    """
    Evaluate the opening 5-min candle and return a trade signal or None.

    Returns:
        {
            "direction": "long" | "short",
            "entry": float,
            "stop": float,
            "target": float,
            "risk_reward": float,
        }
        or None if no trade.
    """
    o = candle["open"]
    h = candle["high"]
    l = candle["low"]
    c = candle["close"]

    candle_range = h - l
    mid = (h + l) / 2

    # Filter: candle too small (doji / inside bar) — skip
    if candle_range / mid < MIN_CANDLE_RANGE_PCT:
        log.info(f"Candle range too small ({candle_range:.2f}) — no signal.")
        return None

    # Filter: candle range larger than max allowed risk in dollars
    max_risk = settings.MAX_RISK_PER_TRADE_USD / settings.POSITION_SIZE_SHARES
    if candle_range > max_risk:
        log.info(
            f"Candle range ${candle_range:.2f} exceeds max risk per share "
            f"${max_risk:.2f} — skipping."
        )
        return None

    is_bullish = c > o

    if is_bullish:
        direction = "long"
        entry  = round(h + BUFFER_TICKS, 2)   # Buy stop just above high
        stop   = round(l - BUFFER_TICKS, 2)   # Stop just below low
        risk   = entry - stop
        target = round(entry + risk * RISK_REWARD_RATIO, 2)
    else:
        direction = "short"
        entry  = round(l - BUFFER_TICKS, 2)   # Sell stop just below low
        stop   = round(h + BUFFER_TICKS, 2)   # Stop just above high
        risk   = stop - entry
        target = round(entry - risk * RISK_REWARD_RATIO, 2)

    if risk <= 0:
        log.warning("Calculated risk is zero or negative — skipping.")
        return None

    log.info(
        f"Signal generated: {direction.upper()} | "
        f"Entry={entry} Stop={stop} Target={target} Risk=${risk:.2f}/share"
    )

    return {
        "direction":   direction,
        "entry":       entry,
        "stop":        stop,
        "target":      target,
        "risk_reward": RISK_REWARD_RATIO,
    }
