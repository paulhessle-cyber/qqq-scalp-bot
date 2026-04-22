"""
Sends Telegram messages via the Bot API.
"""

import logging
import httpx
from config import settings

log = logging.getLogger(__name__)


async def send_telegram(message: str, parse_mode: str = "Markdown") -> bool:
    """
    Sends a message to your Telegram chat.
    Returns True on success, False on failure.
    """
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":    settings.TELEGRAM_CHAT_ID,
        "text":       message,
        "parse_mode": parse_mode,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            log.info("Telegram message sent.")
            return True
    except Exception as e:
        log.error(f"Failed to send Telegram message: {e}")
        return False
