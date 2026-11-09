# POCKET SIGNAL M1

Educational Telegram signal bot using Twelve Data 1-minute Forex candles.

## Important
- This is an educational indicator, not financial advice or a profit guarantee.
- It does not connect to or place trades on Pocket Option.
- Twelve Data prices may differ from Pocket Option, especially OTC instruments.
- Test on a demo account. Binary options are high risk.
- The default list is three liquid Forex pairs, not every pair on the platform.
- API plans have request limits. Check your Twelve Data plan before increasing PAIRS.

## Deploy on Render
Create a **Background Worker** from this GitHub repository. Runtime: Python.
Build command: `pip install -r requirements.txt`
Start command: `python bot.py`

Add these Environment Variables in Render:
- `TELEGRAM_BOT_TOKEN` — token from BotFather (keep private)
- `TWELVE_DATA_API_KEY` — API key from Twelve Data (keep private)
- `PAIRS` — optional, e.g. `EUR/USD,GBP/USD,USD/JPY`
- `POLL_SECONDS` — optional, default `60`

After deployment, open your Telegram bot and send `/start`.
Commands: `/signals`, `/pairs`, `/stop`.

The worker must remain running. Free hosting availability and sleep policies can change; check Render's current plan details.
