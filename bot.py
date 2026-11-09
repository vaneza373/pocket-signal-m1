import os
import time
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TWELVE_DATA_KEY = os.environ["TWELVE_DATA_API_KEY"]
PAIRS = [p.strip() for p in os.getenv("PAIRS", "EUR/USD,GBP/USD,USD/JPY").split(",") if p.strip()]
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "60"))
EXPIRY_LABEL = "1 минута"

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
last_update_id = 0
subscribers = set()
last_signal = {}

def http_json(url, data=None):
    payload = None if data is None else urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=payload)
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode())

def tg(method, **params):
    return http_json(f"{TELEGRAM_API}/{method}", params)

def send(chat_id, text):
    tg("sendMessage", chat_id=chat_id, text=text)

def candles(symbol):
    query = urllib.parse.urlencode({
        "symbol": symbol, "interval": "1min", "outputsize": "80",
        "apikey": TWELVE_DATA_KEY, "format": "JSON"
    })
    result = http_json(f"https://api.twelvedata.com/time_series?{query}")
    if "values" not in result:
        raise RuntimeError(result.get("message", result.get("code", "No candle data")))
    # API returns newest first; use chronological order.
    return [float(row["close"]) for row in reversed(result["values"])]

def ema(values, period):
    alpha = 2 / (period + 1)
    current = values[0]
    out = [current]
    for value in values[1:]:
        current = alpha * value + (1 - alpha) * current
        out.append(current)
    return out

def rsi(values, period=14):
    changes = [values[i] - values[i-1] for i in range(1, len(values))]
    gains = [max(x, 0) for x in changes]
    losses = [max(-x, 0) for x in changes]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def signal_for(symbol):
    prices = candles(symbol)
    if len(prices) < 35:
        return "WAIT", "Недостаточно свечей"
    fast = ema(prices, 9)[-1]
    slow = ema(prices, 21)[-1]
    r = rsi(prices)
    # Lightweight MACD confirmation: EMA12 - EMA26 vs signal EMA9.
    e12, e26 = ema(prices, 12), ema(prices, 26)
    macd_line = [a-b for a, b in zip(e12, e26)]
    macd_signal = ema(macd_line, 9)[-1]
    macd_now = macd_line[-1]
    if fast > slow and macd_now > macd_signal and 50 < r < 70:
        return "CALL", f"EMA9 выше EMA21; RSI {r:.1f}; MACD подтверждает"
    if fast < slow and macd_now < macd_signal and 30 < r < 50:
        return "PUT", f"EMA9 ниже EMA21; RSI {r:.1f}; MACD подтверждает"
    return "WAIT", f"Нет полного совпадения условий (RSI {r:.1f})"

def handle_updates():
    global last_update_id
    try:
        data = tg("getUpdates", offset=last_update_id + 1, timeout=5)
        for update in data.get("result", []):
            last_update_id = update["update_id"]
            msg = update.get("message", {})
            chat = msg.get("chat", {})
            chat_id = chat.get("id")
            command = (msg.get("text") or "").strip().split()[0].lower()
            if not chat_id:
                continue
            if command in ("/start", "/subscribe"):
                subscribers.add(chat_id)
                send(chat_id, "Привет! POCKET SIGNAL M1 подключён.\\n"
                     "Команды: /signals — проверить пары, /pairs — список пар, /stop — отключить уведомления.\\n"
                     "Сигналы учебные и не гарантируют результат.")
            elif command == "/pairs":
                send(chat_id, "Пары: " + ", ".join(PAIRS))
            elif command == "/signals":
                send(chat_id, format_signals())
            elif command == "/stop":
                subscribers.discard(chat_id)
                send(chat_id, "Уведомления отключены. Для возврата отправь /start.")
            else:
                send(chat_id, "Команды: /start, /signals, /pairs, /stop")
    except Exception as exc:
        print("Telegram polling error:", exc, flush=True)

def format_signals():
    lines = ["POCKET SIGNAL M1 — обзор закрытых минутных свечей"]
    for pair in PAIRS:
        try:
            direction, reason = signal_for(pair)
            lines.append(f"{pair}: {direction}\\n{reason}")
        except Exception as exc:
            lines.append(f"{pair}: WAIT\\nДанные временно недоступны: {exc}")
        time.sleep(1)  # reduce API burst
    lines.append("\\nЭкспирация 1 минута — только ориентир, не рекомендация.")
    return "\\n\\n".join(lines)

def main():
    print("Bot started. Pairs:", PAIRS, flush=True)
    last_cycle = 0
    while True:
        handle_updates()
        now = time.time()
        if subscribers and now - last_cycle >= POLL_SECONDS:
            message = format_signals()
            for chat_id in list(subscribers):
                try:
                    send(chat_id, message)
                except Exception as exc:
                    print("Send error:", exc, flush=True)
            last_cycle = now
        time.sleep(2)

if __name__ == "__main__":
    main()
