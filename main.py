import requests, asyncio, os, time, schedule, threading
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
TELEGRAM_TOKEN = "8075741745:AAE2vGnNe04Aprs4DA7Ty-G2t6XT1SYWjHo"
WATCHLIST = ['btc','eth','sol','xrp','doge','ada','avax','link','dot','matic','shib','pepe','wif','bonk','sui','ton','brett','maga','popcat','mew','floki','ondo','ena']
# ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←

bot = Bot(token=TELEGRAM_TOKEN)
CHAT_ID = None

def twitter_surge(symbol):
    try:
        url = f"https://api.allorigins.win/raw?url=https://syndication.twitter.com/srv/timeline-profile/screen-name/{symbol.upper()}USD"
        html = requests.get(url, timeout=8).text
        return html.lower().count("tweet") + html.count("Tweet") > 40
    except:
        return False

def make_chart(coin_id, symbol):
    try:
        ohlc = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc?vs_currency=usd&days=7").json()
        df = pd.DataFrame(ohlc, columns=['time','open','high','low','close'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        plt.figure(figsize=(10,5), facecolor='black')
        plt.plot(df['time'], df['close'], color='#00ff88', linewidth=2.5)
        plt.fill_between(df['time'], df['close'], alpha=0.25, color='#00ff88')
        plt.title(f"{symbol.upper()} – 7 days", color='white', fontsize=14)
        plt.xticks(color='white'); plt.yticks(color='white')
        plt.grid(alpha=0.3); plt.tight_layout()
        path = f"/tmp/{symbol}.png"
        plt.savefig(path, facecolor='black', dpi=200)
        plt.close()
        return path
    except:
        return None

def scan():
    print(f"{datetime.now().strftime('%H:%M')} → Scanning...")
    data = requests.get("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=200&page=1&price_change_percentage=24h").json()
    for coin in data:
        s = coin['symbol'].lower()
        if s not in WATCHLIST and coin['market_cap_rank'] > 120: continue
        vol = coin.get('total_volume', 0)
        cap = coin.get('market_cap', 1)
        ratio = vol / cap
        if ratio < 0.25 or vol < 50_000_000: continue

        hist = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin['id']}/market_chart?vs_currency=usd&days=30").json()
        closes = pd.Series([x[1] for x in hist['prices'][-60:]])
        delta = closes.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = -delta.clip(upper=0).rolling(14).mean()
        rs = gain / loss.replace(0, 0.0001)
        rsi = 100 - (100 / (1 + rs.iloc[-1]))
        macd_hist = (delta.ewm(span=12).mean() - delta.ewm(span=26).mean()).ewm(span=9).mean().diff().iloc[-1]

        social_surge = twitter_surge(s)
        score = 2
        if ratio > 0.5: score += 4
        elif ratio > 0.3: score += 2
        if rsi > 62: score += 2
        if macd_hist > 0: score += 1
        if social_surge: score += 3

        if score >= 6:
            chart = make_chart(coin['id'], s)
            msg = f"""STRENGTH {score}/10
{s.upper()} · {coin['name']}
Volume ${vol:,.0f} ({ratio:.1%} of cap!)
Price ${coin['current_price']:,}
24h {coin['price_change_percentage_24h']:+.2f}%
RSI {rsi:.1f} | MACD {'bullish' if macd_hist>0 else 'bearish'}
Twitter: {'ON FIRE' if social_surge else 'normal'}"""
            asyncio.run(send(msg, chart))
            print(f"ALERT → {s.upper()} | Score {score}")

async def send(text, photo=None):
    global CHAT_ID
    if not CHAT_ID: return
    await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")
    if photo and os.path.exists(photo):
        with open(photo, "rb") as f:
            await bot.send_photo(chat_id=CHAT_ID, photo=f)
        os.remove(photo)

async def start(update, context):
    global CHAT_ID
    CHAT_ID = update.message.chat_id
    await update.message.reply_text("24/7 BOT IS LIVE FOREVER\nCharts + RSI + Twitter surge + watchlist\nNever miss another move")

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))

# 24/7 background scanner
def runner():
    schedule.every(11).minutes.do(lambda: asyncio.create_task(asyncio.to_thread(scan)))
    while True: schedule.run_pending(); time.sleep(1)
threading.Thread(target=runner, daemon=True).start()

print("24/7 CRYPTO BOT STARTING ON RENDER...")
app.run_polling()
