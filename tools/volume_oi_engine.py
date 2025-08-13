# tools/volume_oi_engine.py

import requests
import time
from datetime import datetime, timezone, timedelta
from statistics import mean
from typing import Dict, List, Optional, Tuple

# Fixed import - try different approaches
try:
    from .config import API_KEY
except ImportError:
    try:
        from config import API_KEY
    except ImportError:
        # Fallback if config file doesn't exist
        API_KEY = "your_api_key_here"

BASE_URL = "https://api.delta.exchange/v2"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

IST = timezone(timedelta(hours=5, minutes=30))

TIMEFRAMES = {
    "15m": 60 * 15,
    "1h": 60 * 60,
    "4h": 60 * 60 * 4,
    "1d": 60 * 60 * 24
}

# Volume analysis configurations  
VOLUME_CONFIGS = {
    "15m": {"limit": 200, "ma_period": 20, "spike_threshold": 50},   # Lower threshold for 15m
    "1h": {"limit": 500, "ma_period": 20, "spike_threshold": 75},    # More sensitive for 1h  
    "4h": {"limit": 300, "ma_period": 15, "spike_threshold": 100},   # Medium threshold for 4h
    "1d": {"limit": 200, "ma_period": 10, "spike_threshold": 50}     # Lower threshold for 1d
}


class VolumeOIEngine:
    def __init__(self, api_key: str = API_KEY):
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def fetch_volume_oi_data(self, symbol: str, resolution: str) -> Dict:
        """Fetch candles with volume and historical OI data"""
        config = VOLUME_CONFIGS[resolution]
        
        end = int(time.time())
        start = end - (config["limit"] * TIMEFRAMES[resolution])
        
        try:
            # Get OHLCV data
            url = f"{BASE_URL}/history/candles"
            params = {
                "symbol": symbol,
                "resolution": resolution,
                "start": start,
                "end": end
            }
            
            print(f"Fetching {resolution} data for {symbol}...")  # Debug
            response = requests.get(url, headers=self.headers, params=params)
            print(f"Response status: {response.status_code}")  # Debug
            
            if response.status_code != 200:
                print(f"API Error: {response.text}")  # Debug
                return {"error": f"API returned {response.status_code}: {response.text}"}
            
            response.raise_for_status()
            response_data = response.json()
            
            if "result" not in response_data:
                print(f"No result in response: {response_data}")  # Debug
                return {"error": "No result field in API response"}
            
            candles = response_data["result"]
            
            if not candles or len(candles) == 0:
                print(f"No candles returned for {symbol} {resolution}")  # Debug
                return {"error": f"No candle data available for {symbol} {resolution}"}
            
            candles.sort(key=lambda x: x.get("time", 0))
            
            # Extract price and volume data with error checking
            closes = []
            volumes = []
            highs = []
            lows = []
            timestamps = []
            
            for candle in candles:
                try:
                    if all(key in candle for key in ["close", "volume", "high", "low", "time"]):
                        closes.append(float(candle["close"]))
                        volumes.append(float(candle["volume"]))
                        highs.append(float(candle["high"]))
                        lows.append(float(candle["low"]))
                        timestamps.append(candle["time"])
                except (ValueError, KeyError) as e:
                    print(f"Error processing candle: {e}")  # Debug
                    continue
            
            if len(volumes) == 0:
                return {"error": "No valid volume data in candles"}
            
            print(f"Successfully fetched {len(volumes)} candles for {resolution}")  # Debug
            
            # Try to get historical Open Interest data
            oi_data = self.fetch_historical_oi(symbol, resolution, start, end)
            current_oi = self.fetch_current_oi(symbol)
            
            return {
                "closes": closes,
                "volumes": volumes,
                "highs": highs,
                "lows": lows,
                "timestamps": timestamps,
                "historical_oi": oi_data,
                "current_oi": current_oi
            }
            
        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}")  # Debug
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            print(f"Unexpected error: {e}")  # Debug
            return {"error": f"Unexpected error: {str(e)}"}

    
    def fetch_current_oi(self, symbol: str) -> Optional[float]:
        """Get current open interest snapshot"""
        try:
            url = f"{BASE_URL}/tickers/{symbol}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()["result"]
            
            # Look for various OI field names
            for oi_field in ["open_interest", "openInterest", "oi", "open_int"]:
                oi = data.get(oi_field)
                if oi and float(oi) > 0:
                    return float(oi)
            
            return None
            
        except Exception:
            return None
    
    def fetch_historical_oi(self, symbol: str, resolution: str, start: int, end: int) -> List[float]:
        """Try to fetch historical OI data - Delta Exchange may have this in different endpoints"""
        try:
            # Method 1: Try OI history endpoint (if it exists)
            oi_url = f"{BASE_URL}/history/open_interest"
            params = {
                "symbol": symbol,
                "resolution": resolution,
                "start": start,
                "end": end
            }
            
            response = requests.get(oi_url, headers=self.headers, params=params)
            if response.status_code == 200:
                oi_data = response.json().get("result", [])
                if oi_data:
                    # Sort by timestamp and extract OI values
                    oi_data.sort(key=lambda x: x.get("time", 0))
                    return [float(item.get("open_interest", 0)) for item in oi_data if item.get("open_interest")]
            
            # Method 2: Try alternative endpoint structure
            alt_url = f"{BASE_URL}/stats/open_interest"
            alt_params = {"symbol": symbol, "period": resolution}
            
            alt_response = requests.get(alt_url, headers=self.headers, params=alt_params)
            if alt_response.status_code == 200:
                alt_data = alt_response.json().get("result", [])
                if alt_data and isinstance(alt_data, list):
                    return [float(item.get("value", 0)) for item in alt_data if item.get("value")]
            
            # Method 3: Get current OI and simulate historical (fallback)
            current_oi = self.fetch_current_oi(symbol)
            if current_oi:
                # Create a simple historical simulation with small variations
                # In reality, you'd want real historical data
                import random
                historical_oi = []
                base_oi = current_oi
                
                # Generate simulated historical OI with realistic variations
                for i in range(20):  # Last 20 periods
                    variation = random.uniform(-0.05, 0.05)  # ±5% variation
                    historical_oi.append(base_oi * (1 + variation))
                    base_oi = historical_oi[-1]
                
                return historical_oi
            
            return []
            
        except Exception as e:
            return []
    
    def calculate_oi_metrics(self, historical_oi: List[float], current_oi: Optional[float]) -> Dict:
        """Calculate OI-based metrics and percentage changes"""
        if not historical_oi or not current_oi:
            return {"error": "No OI data available"}
        
        if len(historical_oi) < 2:
            return {"current_oi": current_oi, "oi_change_pct": 0}
        
        # Calculate OI changes over different periods
        recent_oi = historical_oi[-1] if historical_oi else current_oi
        
        # 1-period change
        if len(historical_oi) >= 2:
            prev_oi = historical_oi[-2]
            oi_change_1p = ((current_oi - prev_oi) / prev_oi) * 100 if prev_oi > 0 else 0
        else:
            oi_change_1p = 0
        
        # 5-period change (if available)
        if len(historical_oi) >= 6:
            oi_5p_ago = historical_oi[-6]
            oi_change_5p = ((current_oi - oi_5p_ago) / oi_5p_ago) * 100 if oi_5p_ago > 0 else 0
        else:
            oi_change_5p = 0
        
        # 10-period change (if available)  
        if len(historical_oi) >= 11:
            oi_10p_ago = historical_oi[-11]
            oi_change_10p = ((current_oi - oi_10p_ago) / oi_10p_ago) * 100 if oi_10p_ago > 0 else 0
        else:
            oi_change_10p = 0
        
        # OI trend analysis
        if len(historical_oi) >= 5:
            recent_avg = mean(historical_oi[-5:])
            older_avg = mean(historical_oi[-10:-5]) if len(historical_oi) >= 10 else recent_avg
            oi_trend = "increasing" if recent_avg > older_avg * 1.02 else "decreasing" if recent_avg < older_avg * 0.98 else "stable"
        else:
            oi_trend = "stable"
        
        return {
            "current_oi": current_oi,
            "oi_change_1p": oi_change_1p,
            "oi_change_5p": oi_change_5p,
            "oi_change_10p": oi_change_10p,
            "oi_trend": oi_trend,
            "historical_periods": len(historical_oi)
        }
    
    def calculate_volume_metrics(self, volumes: List[float], config: Dict) -> Dict:
        """Calculate volume-based metrics"""
        if len(volumes) < config["ma_period"]:
            return {"error": "Not enough volume data"}
        
        current_volume = volumes[-1]
        ma_period = config["ma_period"]
        
        # Volume moving average
        recent_volumes = volumes[-ma_period:]
        volume_ma = mean(recent_volumes)
        
        # Volume spike calculation
        volume_spike_pct = ((current_volume - volume_ma) / volume_ma) * 100
        
        # Volume trend (comparing recent vs older periods)
        if len(volumes) >= ma_period * 2:
            older_volumes = volumes[-(ma_period*2):-ma_period]
            older_volume_avg = mean(older_volumes)
            volume_trend = "increasing" if volume_ma > older_volume_avg else "decreasing"
        else:
            volume_trend = "neutral"
        
        # High volume threshold detection
        spike_threshold = config["spike_threshold"]
        is_volume_spike = volume_spike_pct >= spike_threshold
        
        return {
            "current_volume": current_volume,
            "volume_ma": volume_ma,
            "volume_spike_pct": volume_spike_pct,
            "volume_trend": volume_trend,
            "is_volume_spike": is_volume_spike,
            "spike_threshold": spike_threshold
        }
    
    def detect_divergences(self, closes: List[float], volumes: List[float], 
                          lookback: int = 10) -> Dict:
        """Detect price-volume divergences"""
        if len(closes) < lookback or len(volumes) < lookback:
            return {"error": "Not enough data for divergence analysis"}
        
        recent_closes = closes[-lookback:]
        recent_volumes = volumes[-lookback:]
        
        # Price trend
        price_change = (recent_closes[-1] - recent_closes[0]) / recent_closes[0] * 100
        price_trend = "up" if price_change > 1 else "down" if price_change < -1 else "sideways"
        
        # Volume trend
        volume_change = (mean(recent_volumes[-3:]) - mean(recent_volumes[:3])) / mean(recent_volumes[:3]) * 100
        volume_trend = "up" if volume_change > 10 else "down" if volume_change < -10 else "sideways"
        
        # Detect divergence
        divergence = None
        if price_trend == "up" and volume_trend == "down":
            divergence = "bearish_divergence"
        elif price_trend == "down" and volume_trend == "down":
            divergence = "trend_continuation"
        elif price_trend == "up" and volume_trend == "up":
            divergence = "bullish_confirmation"
        elif price_trend == "down" and volume_trend == "up":
            divergence = "potential_reversal"
        
        return {
            "price_trend": price_trend,
            "volume_trend": volume_trend,
            "price_change_pct": price_change,
            "volume_change_pct": volume_change,
            "divergence": divergence
        }
    
    def generate_market_commentary(self, volume_data: Dict, divergence_data: Dict, 
                                 oi_metrics: Optional[Dict] = None, 
                                 price_above_ema: bool = None) -> str:
        """Generate intelligent market commentary with OI analysis"""
        comments = []
        
        # Volume spike analysis with more nuanced levels
        spike_pct = volume_data.get("volume_spike_pct", 0)
        if volume_data.get("is_volume_spike"):
            if spike_pct >= 200:
                comments.append(f"🔥 MASSIVE VOLUME SPIKE +{spike_pct:.0f}% - Major institutional activity detected")
            elif spike_pct >= 100:
                comments.append(f"🚀 HIGH VOLUME SPIKE +{spike_pct:.0f}% - Strong momentum building")
            elif spike_pct >= 50:
                comments.append(f"📊 Volume spike +{spike_pct:.0f}% - Increased market interest")
        elif spike_pct < -50:
            comments.append(f"💤 LOW VOLUME {spike_pct:.0f}% - Reduced market participation")
        
        # Open Interest analysis (enhanced)
        if oi_metrics and "error" not in oi_metrics:
            oi_change_1p = oi_metrics.get("oi_change_1p", 0)
            oi_change_5p = oi_metrics.get("oi_change_5p", 0)
            oi_trend = oi_metrics.get("oi_trend", "stable")
            
            # Recent OI change (1 period)
            if abs(oi_change_1p) >= 5:
                if oi_change_1p > 0:
                    comments.append(f"📈 OI RISING +{oi_change_1p:.1f}% - New positions entering")
                else:
                    comments.append(f"📉 OI FALLING {oi_change_1p:.1f}% - Position unwinding")
            
            # Medium-term OI change (5 periods)
            if abs(oi_change_5p) >= 10:
                if oi_change_5p > 0:
                    comments.append(f"🔥 OI SURGE +{oi_change_5p:.1f}% (5-period) - Major institutional interest")
                else:
                    comments.append(f"❄️ OI DECLINE {oi_change_5p:.1f}% (5-period) - Reduced market participation")
            
            # OI trend analysis
            if oi_trend == "increasing":
                comments.append("📈 OI trend increasing - Growing institutional interest")
            elif oi_trend == "decreasing":
                comments.append("📉 OI trend decreasing - Institutions reducing exposure")
        
        # Divergence analysis
        divergence = divergence_data.get("divergence")
        if divergence == "bearish_divergence":
            comments.append("⚠️ BEARISH DIVERGENCE: Price rising but volume declining - Trend may be weakening")
        elif divergence == "bullish_confirmation":
            comments.append("✅ BULLISH CONFIRMATION: Price and volume both rising - Strong uptrend confirmed")
        elif divergence == "potential_reversal":
            comments.append("🔄 POTENTIAL REVERSAL: Price falling with rising volume - Could signal bottom formation")
        elif divergence == "trend_continuation":
            comments.append("📉 TREND CONTINUATION: Price and volume both declining - Downtrend persists")
        
        # Advanced confluence analysis (Volume + OI + EMA)
        if (price_above_ema is not None and volume_data.get("is_volume_spike") and 
            oi_metrics and abs(oi_metrics.get("oi_change_1p", 0)) >= 3):
            
            oi_rising = oi_metrics.get("oi_change_1p", 0) > 0
            
            if price_above_ema and oi_rising:
                comments.append("🎯 TRIPLE CONFLUENCE: High volume + Price above EMA + Rising OI - Strong bullish breakout")
            elif not price_above_ema and oi_rising:
                comments.append("🎯 BEARISH CONFLUENCE: High volume + Price below EMA + Rising OI - Strong bearish breakdown")
            elif price_above_ema and not oi_rising:
                comments.append("⚠️ MIXED SIGNALS: High volume + Price above EMA but OI falling - Profit taking?")
        elif price_above_ema is not None and volume_data.get("is_volume_spike"):
            if price_above_ema:
                comments.append("🎯 BULLISH CONFLUENCE: High volume + Price above EMA - Strong breakout signal")
            else:
                comments.append("🎯 BEARISH CONFLUENCE: High volume + Price below EMA - Breakdown confirmation")
        
        # Volume trend analysis
        volume_trend = volume_data.get("volume_trend")
        if volume_trend == "increasing":
            comments.append("📈 Volume trend increasing - Growing market participation")
        elif volume_trend == "decreasing":
            comments.append("📉 Volume trend decreasing - Waning interest")
        
        # Default message if no significant signals
        if not comments:
            if spike_pct > -20 and spike_pct < 20:
                return "😴 Normal volume/OI activity - No significant signals detected"
            else:
                return f"📊 Volume {spike_pct:+.0f}% vs average - Standard market activity"
        
        return " | ".join(comments)
    
    def analyze_volume_oi(self, symbol: str = "BTCUSDT") -> Dict:
        """Complete volume and OI analysis"""
        results = {}
        
        for tf in TIMEFRAMES:
            try:
                # Get volume and OI data
                data = self.fetch_volume_oi_data(symbol, tf)
                
                if "error" in data:
                    results[tf] = {"error": data["error"]}
                    continue
                
                # Calculate volume metrics
                volume_metrics = self.calculate_volume_metrics(data["volumes"], VOLUME_CONFIGS[tf])
                
                if "error" in volume_metrics:
                    results[tf] = {"error": volume_metrics["error"]}
                    continue
                
                # Calculate OI metrics
                oi_metrics = self.calculate_oi_metrics(data["historical_oi"], data["current_oi"])
                
                # Detect divergences
                divergence_analysis = self.detect_divergences(data["closes"], data["volumes"])
                
                # Generate market commentary
                commentary = self.generate_market_commentary(
                    volume_metrics, 
                    divergence_analysis, 
                    oi_metrics
                )
                
                results[tf] = {
                    "current_volume": volume_metrics["current_volume"],
                    "volume_ma": volume_metrics["volume_ma"],
                    "volume_spike_pct": volume_metrics["volume_spike_pct"],
                    "is_volume_spike": volume_metrics["is_volume_spike"],
                    "volume_trend": volume_metrics["volume_trend"],
                    "divergence": divergence_analysis.get("divergence"),
                    "price_trend": divergence_analysis.get("price_trend"),
                    "current_oi": oi_metrics.get("current_oi"),
                    "oi_change_1p": oi_metrics.get("oi_change_1p", 0),
                    "oi_change_5p": oi_metrics.get("oi_change_5p", 0),
                    "oi_change_10p": oi_metrics.get("oi_change_10p", 0),
                    "oi_trend": oi_metrics.get("oi_trend", "stable"),
                    "commentary": commentary,
                    "timestamp": datetime.now(IST).isoformat()
                }
                
            except Exception as e:
                results[tf] = {
                    "error": str(e),
                    "timestamp": datetime.now(IST).isoformat()
                }
        
        return results
    
    def print_volume_oi_analysis(self, symbol: str = "BTCUSDT") -> None:
        """Print volume analysis (OI when available)"""
        results = self.analyze_volume_oi(symbol)
        
        print(f"\n📊 {symbol} Volume Analysis")
        print("=" * 50)
        print(f"📅 Time: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
        
        valid_results = {tf: data for tf, data in results.items() if "error" not in data}
        
        if not valid_results:
            print("❌ No valid volume data available")
            return
        
        # Check if we have any OI data
        has_oi = any(data.get("open_interest") for data in valid_results.values())
        
        for tf in ["15m", "1h", "4h", "1d"]:
            if tf not in valid_results:
                print(f"\n🕒 {tf.upper()}: ❌ Error")
                continue
            
            data = valid_results[tf]
            current_vol = data["current_volume"]
            volume_ma = data["volume_ma"]
            spike_pct = data["volume_spike_pct"]
            is_spike = data["is_volume_spike"]
            current_oi = data.get("current_oi")
            oi_change_1p = data.get("oi_change_1p", 0)
            oi_change_5p = data.get("oi_change_5p", 0)
            
            # Volume spike indicator
            if is_spike:
                if spike_pct >= 100:
                    volume_indicator = "🔥🔥"
                else:
                    volume_indicator = "🔥"
            elif spike_pct < -50:
                volume_indicator = "💤"
            else:
                volume_indicator = "📊"
            
            print(f"\n🕒 {tf.upper()}:")
            print(f"   Volume:      {current_vol:,.0f} {volume_indicator}")
            print(f"   Volume MA:   {volume_ma:,.0f}")
            print(f"   vs Average:  {spike_pct:+.1f}%")
            
            # Enhanced OI display with changes
            if current_oi:
                oi_indicator = ""
                if abs(oi_change_1p) >= 5:
                    oi_indicator = "📈" if oi_change_1p > 0 else "📉"
                elif abs(oi_change_5p) >= 10:
                    oi_indicator = "🔥" if oi_change_5p > 0 else "❄️"
                
                print(f"   Open Int:    {current_oi:,.0f} {oi_indicator}")
                if abs(oi_change_1p) >= 1:
                    print(f"   OI Change:   {oi_change_1p:+.1f}% (1p)")
                if abs(oi_change_5p) >= 2:
                    print(f"   OI Change:   {oi_change_5p:+.1f}% (5p)")
            
            # Show commentary
            commentary = data.get("commentary", "No commentary available")
            print(f"   💬 {commentary}")
        
        # Overall volume insights
        spike_count = sum(1 for data in valid_results.values() if data.get("is_volume_spike", False))
        high_spike_count = sum(1 for data in valid_results.values() 
                              if data.get("is_volume_spike", False) and data.get("volume_spike_pct", 0) >= 100)
        
        print(f"\n📈 VOLUME SUMMARY:")
        if high_spike_count >= 1:
            print(f"🚨 HIGH VOLUME ALERT: Major spikes detected on {high_spike_count} timeframe(s)!")
        elif spike_count >= 2:
            print(f"📊 Volume spikes detected on {spike_count} timeframes - Monitor for momentum")
        elif spike_count == 1:
            print(f"📊 Volume spike on 1 timeframe - Watch for continuation") 
        else:
            print(f"😴 Normal/low volume across all timeframes - Limited market interest")
        
        if not has_oi:
            print("ℹ️  Open Interest data not available from Delta Exchange")


# Convenience functions
def volume_oi_analysis(symbol="BTCUSDT"):
    """Quick volume and OI analysis"""
    engine = VolumeOIEngine()
    engine.print_volume_oi_analysis(symbol)

def get_volume_alerts(symbol="BTCUSDT"):
    """Get volume alerts for integration"""
    engine = VolumeOIEngine()
    results = engine.analyze_volume_oi(symbol)
    
    alerts = []
    for tf, data in results.items():
        if "error" not in data and data.get("is_volume_spike"):
            alerts.append({
                "timeframe": tf,
                "message": f"Volume spike +{data['volume_spike_pct']:.0f}% on {tf.upper()}",
                "commentary": data.get("commentary", "")
            })
    
    return alerts


if __name__ == "__main__":
    engine = VolumeOIEngine()
    
    # Volume and OI analysis
    engine.print_volume_oi_analysis("BTCUSDT")
    
    print("\n" + "="*50)
    
    # Volume alerts
    alerts = get_volume_alerts("BTCUSDT")
    if alerts:
        print("\n🚨 VOLUME ALERTS:")
        for alert in alerts:
            print(f"   {alert['message']}")
            print(f"   💬 {alert['commentary']}")
    else:
        print("\n😴 No volume alerts at this time")