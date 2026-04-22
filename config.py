"""
Configuration — all secrets loaded from environment variables.
Never hardcode credentials here. Set them in .env (local) or
DigitalOcean environment variables (production).
"""

import os
from dataclasses import dataclass


@dataclass
class Settings:
    # ── Telegram ────────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str  = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID:   str  = os.getenv("TELEGRAM_CHAT_ID", "")

    # ── Interactive Brokers ─────────────────────────────────────────────────
    # Use port 7497 for paper trading, 7496 for live
    IB_HOST:      str = os.getenv("IB_HOST", "127.0.0.1")
    IB_PORT:      int = int(os.getenv("IB_PORT", "7497"))   # 7497 = paper
    IB_CLIENT_ID: int = int(os.getenv("IB_CLIENT_ID", "10"))

    # ── Strategy ────────────────────────────────────────────────────────────
    TICKER:                  str   = os.getenv("TICKER", "QQQ")
    POSITION_SIZE_SHARES:    int   = int(os.getenv("POSITION_SIZE_SHARES", "10"))
    MAX_RISK_PER_TRADE_USD:  float = float(os.getenv("MAX_RISK_PER_TRADE_USD", "100"))


settings = Settings()

# ── Validation ───────────────────────────────────────────────────────────────
def validate():
    missing = []
    if not settings.TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not settings.TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in your values."
        )

validate()
