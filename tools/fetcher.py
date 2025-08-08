# tools/fetcher.py

import requests
from tools.config import API_KEY


BASE_URL = "https://api.delta.exchange/v2"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def get_btc_price(symbol="BTCUSDT"):
    try:
        response = requests.get(f"{BASE_URL}/tickers", headers=HEADERS)
        data = response.json()
        for ticker in data["result"]:
            if ticker["symbol"] == symbol:
                return float(ticker["mark_price"])
        print(f"⚠️ Symbol {symbol} not found in tickers.")
        return None
    except Exception as e:
        print(f"❌ Failed to fetch BTC price: {e}")
        return None
