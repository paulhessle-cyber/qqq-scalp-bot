"""
Trade execution via Interactive Brokers (ib_insync).
Places bracket orders: entry limit/stop + take-profit + stop-loss.
"""

import logging
from ib_insync import IB, Stock, Order, util

from config import settings

log = logging.getLogger(__name__)


def _build_contract():
    return Stock(settings.TICKER, "SMART", "USD")


async def place_bracket_order(
    direction: str,
    entry: float,
    stop: float,
    target: float,
) -> dict:
    """
    Places a bracket order on IB.
    - Parent: BUY/SELL STOP order at entry price (triggers on breakout)
    - Child 1: Take-profit limit order at target
    - Child 2: Stop-loss order at stop

    Returns {"success": True, "order_id": int} or {"success": False, "error": str}
    """
    ib = IB()

    try:
        await ib.connectAsync(
            host=settings.IB_HOST,
            port=settings.IB_PORT,
            clientId=settings.IB_CLIENT_ID + 1,  # separate clientId for orders
        )
        log.info("Connected to IB for order placement.")

        contract = _build_contract()
        await ib.qualifyContractsAsync(contract)

        qty = settings.POSITION_SIZE_SHARES
        action = "BUY" if direction == "long" else "SELL"
        close_action = "SELL" if direction == "long" else "BUY"

        # ── Parent order: Stop-Limit entry ──────────────────────────────────
        parent = Order()
        parent.orderId = ib.client.getReqId()
        parent.action = action
        parent.orderType = "STP LMT"
        parent.totalQuantity = qty
        parent.auxPrice = entry          # Stop trigger price
        parent.lmtPrice = round(entry + (0.05 if direction == "long" else -0.05), 2)
        parent.transmit = False          # Don't send until children are attached
        parent.tif = "GTD"
        parent.goodTillDate = _today_10am_et()

        # ── Child 1: Take-profit limit ──────────────────────────────────────
        take_profit = Order()
        take_profit.orderId = ib.client.getReqId()
        take_profit.action = close_action
        take_profit.orderType = "LMT"
        take_profit.totalQuantity = qty
        take_profit.lmtPrice = target
        take_profit.parentId = parent.orderId
        take_profit.transmit = False
        take_profit.tif = "GTD"
        take_profit.goodTillDate = _today_10am_et()

        # ── Child 2: Stop-loss ──────────────────────────────────────────────
        stop_loss = Order()
        stop_loss.orderId = ib.client.getReqId()
        stop_loss.action = close_action
        stop_loss.orderType = "STP"
        stop_loss.totalQuantity = qty
        stop_loss.auxPrice = stop
        stop_loss.parentId = parent.orderId
        stop_loss.transmit = True        # Transmit the whole bracket
        stop_loss.tif = "GTD"
        stop_loss.goodTillDate = _today_10am_et()

        bracket = [parent, take_profit, stop_loss]

        for order in bracket:
            trade = ib.placeOrder(contract, order)
            log.info(f"Order submitted: {order.orderId} ({order.orderType} {order.action})")

        await ib.reqAllOpenOrdersAsync()
        log.info(f"Bracket order placed. Parent ID: {parent.orderId}")

        return {"success": True, "order_id": parent.orderId}

    except Exception as e:
        log.exception(f"Order placement failed: {e}")
        return {"success": False, "error": str(e)}

    finally:
        if ib.isConnected():
            ib.disconnect()


async def cancel_all_open_orders() -> None:
    """Cancels all open orders for the account (called at 10:00 AM)."""
    ib = IB()
    try:
        await ib.connectAsync(
            host=settings.IB_HOST,
            port=settings.IB_PORT,
            clientId=settings.IB_CLIENT_ID + 2,
        )
        open_orders = await ib.reqAllOpenOrdersAsync()
        for trade in open_orders:
            ib.cancelOrder(trade.order)
            log.info(f"Cancelled order {trade.order.orderId}")
        log.info(f"Cancelled {len(open_orders)} open order(s).")
    except Exception as e:
        log.exception(f"Failed to cancel orders: {e}")
    finally:
        if ib.isConnected():
            ib.disconnect()


def _today_10am_et() -> str:
    """Returns today's 10:00 AM ET in IB GTD format: YYYYMMDD HH:MM:SS ET"""
    from datetime import date
    return date.today().strftime("%Y%m%d") + " 10:00:00 ET"
