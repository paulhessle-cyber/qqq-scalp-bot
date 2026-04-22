"""
Fetches market data from Interactive Brokers via ib_insync.
Waits for the 9:30–9:35 ET candle to close, then returns OHLC.
"""

import asyncio
import logging
from datetime import datetime, time
import pytz
from ib_insync import IB, Stock, util

from config import settings

log = logging.getLogger(__name__)
ET = pytz.timezone("America/New_York")


def _build_contract():
    return Stock(settings.TICKER, "SMART", "USD")


async def get_first_5min_candle() -> dict | None:
    """
    Connects to IB, waits for the 9:35 ET candle close,
    then returns the OHLCV of the first 5-min bar.
    """
    ib = IB()

    try:
        await ib.connectAsync(
            host=settings.IB_HOST,
            port=settings.IB_PORT,
            clientId=settings.IB_CLIENT_ID,
        )
        log.info(f"Connected to IB Gateway at {settings.IB_HOST}:{settings.IB_PORT}")

        contract = _build_contract()
        await ib.qualifyContractsAsync(contract)

        # Wait until 9:35 ET so the first bar is complete
        target_close = datetime.now(ET).replace(hour=9, minute=35, second=5, microsecond=0)
        now = datetime.now(ET)
        wait_secs = max(0, (target_close - now).total_seconds())

        if wait_secs > 0:
            log.info(f"Waiting {wait_secs:.0f}s for the 9:35 candle to close...")
            await asyncio.sleep(wait_secs)

        # Request the last 10 minutes of 5-min bars (catches the first bar reliably)
        bars = await ib.reqHistoricalDataAsync(
            contract,
            endDateTime="",
            durationStr="300 S",    # last 5 minutes
            barSizeSetting="5 mins",
            whatToShow="TRADES",
            useRTH=True,
            formatDate=1,
        )

        if not bars:
            log.error("No historical bars returned from IB.")
            return None

        # Use the most recent completed bar
        bar = bars[-1]
        log.info(f"Candle retrieved: {bar.date} O={bar.open} H={bar.high} L={bar.low} C={bar.close}")

        return {
            "date":   bar.date,
            "open":   bar.open,
            "high":   bar.high,
            "low":    bar.low,
            "close":  bar.close,
            "volume": bar.volume,
        }

    except Exception as e:
        log.exception(f"Error fetching candle from IB: {e}")
        return None

    finally:
        if ib.isConnected():
            ib.disconnect()
            log.info("Disconnected from IB.")
