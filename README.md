# QQQ Morning Scalp Bot 🤖📈

A morning-only automated trading bot for QQQ using the **first 5-minute candle breakout** strategy.
Sends a Telegram alert when a trade is placed, and auto-cancels any unfilled orders at 10:00 AM ET.

---

## Strategy Overview

| Step | What happens |
|------|-------------|
| 1 | Market opens at 9:30 AM ET |
| 2 | Bot waits for the 9:30–9:35 candle to close |
| 3 | **Bullish candle** → Buy stop above the high |
| 4 | **Bearish candle** → Sell stop below the low |
| 5 | Stop loss = opposite side of the candle |
| 6 | Take profit = 2× the risk (2:1 R:R) |
| 7 | All orders GTD until 10:00 AM — auto-cancelled if unfilled |
| 8 | Telegram message sent with all trade details |

---

## Architecture

```
GitHub (code) → DigitalOcean Droplet (cron) → IB Gateway (trades) → Telegram (alerts)
```

---

## Prerequisites

- Python 3.11+
- Interactive Brokers account (paper or live)
- IB Gateway or TWS installed and running on your droplet or a VPS
- Telegram Bot Token (from @BotFather)
- DigitalOcean droplet (Ubuntu 22.04 recommended, $6/mo basic)

---

## Setup (Step by Step)

### 1. Create a Telegram Bot

1. Open Telegram and message **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy your **Bot Token**
4. Message **@userinfobot** to get your **Chat ID**

---

### 2. Set Up IB Paper Trading

1. Go to [interactivebrokers.com](https://www.interactivebrokers.com) → create account
2. Enable **paper trading** in account settings
3. Download **IB Gateway** (lighter than TWS)
4. In IB Gateway settings → API → Enable Socket Client
5. Set port to `7497` (paper) or `7496` (live)
6. Set "Trusted IP" to `127.0.0.1`

---

### 3. Set Up DigitalOcean Droplet

```bash
# 1. Create Ubuntu 22.04 droplet (Basic, $6/mo is enough)
# 2. SSH in:
ssh root@your_droplet_ip

# 3. Install Python & pip
apt update && apt install -y python3.11 python3.11-venv python3-pip git

# 4. Clone your GitHub repo
git clone https://github.com/YOUR_USERNAME/qqq-scalp-bot.git
cd qqq-scalp-bot

# 5. Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 6. Set up environment variables
cp .env.example .env
nano .env   # Fill in your Telegram and IB credentials

# 7. Make run script executable
chmod +x run_bot.sh
```

---

### 4. Set the Cron Job (runs Mon–Fri at 9:28 AM ET)

```bash
# Open crontab
crontab -e

# Add this line (adjust path to match your droplet):
28 9 * * 1-5 TZ="America/New_York" /root/qqq-scalp-bot/run_bot.sh
```

---

### 5. Install IB Gateway on the Droplet

IB Gateway needs to run on the same machine as the bot (or be accessible via network).

**Option A — Same droplet (recommended for simplicity):**
```bash
# Install IB Gateway via headless setup
# See: https://github.com/IbcAlpha/IBC for automated IB Gateway startup
# IBC lets IB Gateway run headlessly and auto-login
```

**Option B — Run IB Gateway on your home PC, bot on DigitalOcean:**
```bash
# In your .env, set:
IB_HOST=your_home_ip
# Make sure your router port-forwards 7497 to your PC
# Less reliable — home IP may change
```

**IBC (recommended for headless):**
```bash
# IBC automates IB Gateway login — essential for unattended servers
# https://github.com/IbcAlpha/IBC
# Follow their README to set up auto-login with your IB credentials
```

---

### 6. GitHub Setup (for mobile editing)

```bash
# On your local machine / GitHub.com:
# 1. Create a new PRIVATE repo called qqq-scalp-bot
# 2. Push code:
git init
git remote add origin https://github.com/YOUR_USERNAME/qqq-scalp-bot.git
git add .
git commit -m "Initial bot setup"
git push -u origin main

# 3. On your droplet, pull updates:
cd /root/qqq-scalp-bot && git pull
```

To update settings from mobile: edit `.env.example` or `bot/config.py` on GitHub → pull on droplet.

---

## Configuration Reference

Edit `.env` to tune the bot without touching code:

| Variable | Default | Description |
|---|---|---|
| `TICKER` | `QQQ` | Instrument to trade |
| `POSITION_SIZE_SHARES` | `10` | Shares per trade |
| `MAX_RISK_PER_TRADE_USD` | `100` | Max $ risk — skips trade if candle is too wide |
| `IB_PORT` | `7497` | 7497 = paper, 7496 = live |

---

## Telegram Alerts

You'll receive messages like:

```
🟢 QQQ Scalp Trade Placed

Direction: LONG
Entry:  $478.45
Stop:   $477.80
Target: $479.75
R:R     1:2.0
Order ID: 123456

Orders will auto-cancel if unfilled by 10:00 AM ET
```

---

## Safety Features

- ✅ Weekday check — won't run on weekends
- ✅ Time window check — only active 9:28–10:00 AM ET
- ✅ Minimum candle size filter — skips doji/inside bar opens
- ✅ Max risk guard — skips if candle range exceeds your max risk
- ✅ One trade per day maximum
- ✅ GTD orders auto-expire at 10:00 AM
- ✅ Explicit cancel sweep at 10:00 AM as backup
- ✅ Paper trading port by default (7497)

---

## Switching to Live Trading

1. Change `IB_PORT=7496` in your `.env`
2. Make sure you've paper traded for at least 2 weeks
3. Start with a small `POSITION_SIZE_SHARES` (e.g. 1–5)

---

## Log Files

Logs are saved to `logs/bot_YYYY-MM-DD.log` on the droplet.

```bash
tail -f logs/bot_$(date +%Y-%m-%d).log
```

---

## Disclaimer

This bot is for educational purposes. Trading involves risk. Always paper trade first and never risk money you can't afford to lose.
