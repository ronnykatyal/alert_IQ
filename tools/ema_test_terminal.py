# tools/ema_engine.py

import requests
import time
from datetime import datetime
from statistics import mean
from config import API_KEY

BASE_URL = "https://api.delta.exchange/v2"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

TIMEFRAMES = {
    "15m": 60 * 15,
    "1h": 60 * 60,
    "4h": 60 * 60 * 4,
    "1d": 60 * 60 * 24
}

CANDLE_LIMIT = 210  # 200 EMA + 9 SMA smoothing + 1 buffer


def fetch_candles(symbol, resolution):
    end = int(time.time())
    start = end - (CANDLE_LIMIT * TIMEFRAMES[resolution])

    url = f"{BASE_URL}/history/candles"
    params = {
        "symbol": symbol,
        "resolution": resolution,
        "start": start,
        "end": end
    }
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    candles = response.json()["result"]
    return [candle["close"] for candle in candles]


def sma(data, window):
    return [mean(data[i:i + window]) for i in range(len(data) - window + 1)]


def ema(data, period):
    multiplier = 2 / (period + 1)
    ema_values = [mean(data[:period])]  # Start with SMA as seed
    for price in data[period:]:
        ema_today = (price - ema_values[-1]) * multiplier + ema_values[-1]
        ema_values.append(ema_today)
    return ema_values[-1]  # Latest EMA


def calculate_ema_with_sma_smoothing(close_prices):
    smoothed = sma(close_prices, 9)  # Apply SMA(9)
    latest_ema = ema(smoothed, 200)
    return latest_ema


def analyze_ema(symbol="BTCUSDT"):
    print("\n🔍 BTC EMA Analysis\n" + "=" * 40)
    for tf in TIMEFRAMES:
        try:
            prices = fetch_candles(symbol, tf)
            current_price = prices[-1]
            ema_val = calculate_ema_with_sma_smoothing(prices)
            pct_diff = ((current_price - ema_val) / ema_val) * 100
            direction = "📈 ABOVE EMA" if pct_diff > 0 else "📉 BELOW EMA"

            print(f"\n🕒 Timeframe: {tf.upper()}\n"
                  f"   Current Price: ${current_price:,.2f}\n"
                  f"   200 EMA:       ${ema_val:,.2f}\n"
                  f"   Distance:      {pct_diff:.2f}% => {direction}")
        except Exception as e:
            print(f"\n❌ Error in {tf}: {e}")


if __name__ == "__main__":
    analyze_ema()
