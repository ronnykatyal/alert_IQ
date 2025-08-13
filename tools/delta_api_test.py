# tools/delta_api_test.py

import requests
import time
from datetime import datetime , timezone

from config import API_KEY  # You must have: API_KEY = "your_real_api_key"

BASE_URL = "https://api.delta.exchange/v2"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}  # ✅ Auth required

def measure_latency():
    try:
        start = time.time()
        requests.get(f"{BASE_URL}/tickers")
        return round((time.time() - start) * 1000, 2)
    except Exception as e:
        print(f"❌ Latency check failed: {e}")
        return None

def fetch_live_price(symbol="BTCUSDT"):
    url = f"{BASE_URL}/tickers"
    try:
        response = requests.get(url, headers=HEADERS)
        data = response.json()
        for ticker in data['result']:
            if ticker['symbol'] == symbol:
                return float(ticker['mark_price'])
        print(f"⚠️  Symbol {symbol} not found.")
        return None
    except Exception as e:
        print(f"❌ Price fetch failed: {e}")
        return None

def fetch_history_candles(symbol="BTCUSDT", resolution="4h", limit=5):
    now = int(time.time())
    seconds_per_candle = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400
    }

    if resolution not in seconds_per_candle:
        print(f"❌ Unsupported resolution: {resolution}")
        return []

    end = now
    start = now - (limit * seconds_per_candle[resolution])

    url = f"{BASE_URL}/history/candles"
    params = {
        "symbol": symbol,
        "resolution": resolution,
        "start": start,
        "end": end
    }

    try:
        response = requests.get(url, params=params, headers=HEADERS)
        if response.status_code != 200:
            print("❌ Candle fetch failed:")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.text}")
            return []

        return response.json().get("result", [])
    except Exception as e:
        print(f"❌ Exception fetching candles: {e}")
        return []

def main():
    print("🔍 AlertIQ: BTC History Candle Test")
    print("=" * 50)

    latency = measure_latency()
    if latency:
        print(f"\n⏱️  Testing API Latency...\n   API Response Time: {latency} ms")
        if latency > 1000:
            print("   ⚠️  High latency detected!")

    print("\n💰 Fetching Live BTCUSDT Price...")
    price = fetch_live_price()
    if price:
        print(f"   Current Price: ${price:,.2f}")
    else:
        print("   ❌ Failed to get live price.")

    print("\n🕰️ Fetching 4H Historical Candles for BTCUSDT...")
    candles = fetch_history_candles(symbol="BTCUSDT", resolution="4h", limit=5)

    if not candles:
        print("🚫 No candle data found.")
        return

    for c in candles:
        ts = datetime.fromtimestamp(c['time'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M')  # ✅ One time here
        print(f"   {ts} | Open: {c['open']} | High: {c['high']} | Low: {c['low']} | Close: {c['close']}")
if __name__ == "__main__":
    main()
