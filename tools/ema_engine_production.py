# tools/ema_engine_production.py

import requests
import time
from datetime import datetime, timezone, timedelta
from statistics import mean
from typing import Dict, List, Optional

# Fixed import - try different approaches
try:
    from .config import API_KEY
except ImportError:
    try:
        from config import API_KEY
    except ImportError:
        # Fallback if config file doesn't exist
        API_KEY = "your_api_key_here"  # Replace with your actual API key

BASE_URL = "https://api.delta.exchange/v2"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

IST = timezone(timedelta(hours=5, minutes=30))

TIMEFRAMES = {
    "15m": 60 * 15,
    "1h": 60 * 60,
    "4h": 60 * 60 * 4,
    "1d": 60 * 60 * 24
}

# Production-ready configurations
PRODUCTION_CONFIGS = {
    "15m": {"limit": 200, "sma_period": 5, "ema_period": 195},
    "1h": {"limit": 500, "sma_period": 10, "ema_period": 200},
    "4h": {"limit": 500, "sma_period": 5, "ema_period": 200},
    "1d": {"limit": 300, "sma_period": 12, "ema_period": 200}
}


class ProductionEMAEngine:
    def __init__(self, api_key: str = API_KEY):
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def fetch_candles(self, symbol: str, resolution: str) -> List[float]:
        """Fetch candles with production configuration"""
        config = PRODUCTION_CONFIGS[resolution]
        
        end = int(time.time())
        start = end - (config["limit"] * TIMEFRAMES[resolution])
        
        url = f"{BASE_URL}/history/candles"
        params = {
            "symbol": symbol,
            "resolution": resolution,
            "start": start,
            "end": end
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        candles = response.json()["result"]
        
        candles.sort(key=lambda x: x["time"])
        return [candle["close"] for candle in candles]
    
    def calculate_ema(self, close_prices: List[float], resolution: str) -> float:
        """Calculate EMA with production configuration"""
        config = PRODUCTION_CONFIGS[resolution]
        sma_period = config["sma_period"]
        ema_period = config["ema_period"]
        
        if len(close_prices) < sma_period + ema_period:
            raise ValueError(f"Not enough data. Need {sma_period + ema_period}, got {len(close_prices)}")
        
        # Apply SMA smoothing
        smoothed = []
        for i in range(len(close_prices) - sma_period + 1):
            smoothed.append(mean(close_prices[i:i + sma_period]))
        
        # Calculate EMA on smoothed data
        multiplier = 2 / (ema_period + 1)
        ema = mean(smoothed[:ema_period])
        
        for price in smoothed[ema_period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def get_current_price(self, symbol: str) -> float:
        """Get current price with fallback options"""
        try:
            url = f"{BASE_URL}/tickers/{symbol}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()["result"]
            
            # Prefer spot_price, fallback to mark_price, then close
            for price_key in ["spot_price", "mark_price", "close"]:
                if price_key in data and data[price_key]:
                    price = float(data[price_key])
                    if price > 0:
                        return price
            
            return float(data["close"])
                
        except Exception:
            return None
    
    def analyze_ema(self, symbol: str = "BTCUSDT") -> Dict:
        """Production EMA analysis"""
        results = {}
        
        # Get current price
        current_price = self.get_current_price(symbol)
        
        for tf in TIMEFRAMES:
            try:
                prices = self.fetch_candles(symbol, tf)
                
                # Use fetched price if current price not available
                if current_price is None:
                    current_price = prices[-1]
                
                ema_val = self.calculate_ema(prices, tf)
                pct_diff = ((current_price - ema_val) / ema_val) * 100
                
                results[tf] = {
                    "current_price": current_price,
                    "ema_200": ema_val,
                    "percentage_diff": pct_diff,
                    "above_ema": pct_diff > 0,
                    "data_points": len(prices),
                    "timestamp": datetime.now(IST).isoformat()
                }
                
            except Exception as e:
                results[tf] = {
                    "error": str(e),
                    "timestamp": datetime.now(IST).isoformat()
                }
        
        return results
    
    def print_analysis(self, symbol: str = "BTCUSDT") -> None:
        """Print EMA analysis"""
        results = self.analyze_ema(symbol)
        
        print(f"\n🚀 {symbol} EMA Analysis")
        print("=" * 40)
        print(f"📅 Time: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
        
        valid_results = {tf: data for tf, data in results.items() if "error" not in data}
        
        if not valid_results:
            print("❌ No valid data available")
            return
        
        # Get current price from first valid result
        current_price = next(iter(valid_results.values()))["current_price"]
        print(f"💰 Current Price: ${current_price:,.2f}")
        
        print(f"\n📊 EMA Analysis:")
        
        for tf in ["15m", "1h", "4h", "1d"]:
            if tf not in valid_results:
                print(f"\n🕒 {tf.upper()}: ❌ Error")
                continue
            
            data = valid_results[tf]
            ema_val = data["ema_200"]
            pct_diff = data["percentage_diff"]
            above_ema = data["above_ema"]
            
            direction = "📈 ABOVE EMA" if above_ema else "📉 BELOW EMA"
            
            print(f"\n🕒 {tf.upper()}:")
            print(f"   200 EMA:    ${ema_val:,.2f}")
            print(f"   Distance:   {pct_diff:+.2f}% => {direction}")
        
        # Summary
        above_count = sum(1 for data in valid_results.values() if data["above_ema"])
        total_count = len(valid_results)
        
        print(f"\n📊 Summary: {above_count}/{total_count} timeframes above EMA")
        print(f"   Bullish Ratio: {above_count/total_count:.1%}")
    
    def get_compact_summary(self, symbol: str = "BTCUSDT") -> str:
        """Get compact summary for production use"""
        results = self.analyze_ema(symbol)
        valid_results = {tf: data for tf, data in results.items() if "error" not in data}
        
        if not valid_results:
            return f"{symbol}: No data available"
        
        current_price = next(iter(valid_results.values()))["current_price"]
        
        summary_parts = [f"{symbol}: ${current_price:,.0f}"]
        
        for tf in ["15m", "1h", "4h", "1d"]:
            if tf in valid_results:
                pct = valid_results[tf]["percentage_diff"]
                summary_parts.append(f"{tf}: {pct:+.2f}%")
        
        return " | ".join(summary_parts)


# Production-ready convenience functions
def ema_analysis(symbol="BTCUSDT"):
    """Production EMA analysis"""
    engine = ProductionEMAEngine()
    engine.print_analysis(symbol)

def get_ema_status(symbol="BTCUSDT"):
    """Get EMA status for trading decisions"""
    engine = ProductionEMAEngine()
    results = engine.analyze_ema(symbol)
    
    valid_results = {tf: data for tf, data in results.items() if "error" not in data}
    above_count = sum(1 for data in valid_results.values() if data["above_ema"])
    total_count = len(valid_results)
    
    bullish_ratio = above_count / total_count if total_count > 0 else 0
    
    if bullish_ratio >= 0.75:
        return "BULLISH"
    elif bullish_ratio >= 0.5:
        return "NEUTRAL"
    else:
        return "BEARISH"

def get_summary(symbol="BTCUSDT"):
    """Get production summary"""
    engine = ProductionEMAEngine()
    return engine.get_compact_summary(symbol)


if __name__ == "__main__":
    engine = ProductionEMAEngine()
    
    # EMA analysis
    engine.print_analysis("BTCUSDT")
    
    print("\n" + "="*40)
    
    # Trading summary
    print(f"\n📝 Summary: {get_summary('BTCUSDT')}")
    print(f"📈 Market Status: {get_ema_status('BTCUSDT')}")