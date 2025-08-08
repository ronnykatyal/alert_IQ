# tools/confluence_alert_engine.py

import json
import time
import sys
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from plyer import notification

# Add the tools directory to Python path
sys.path.append(os.path.dirname(__file__))

# Import your existing engines with proper error handling
try:
    from ema_engine_production import ProductionEMAEngine
    print("✅ EMA Engine imported successfully")
except ImportError as e:
    print(f"❌ Could not import ProductionEMAEngine: {e}")
    sys.exit(1)

try:
    from volume_oi_engine import VolumeOIEngine
    print("✅ Volume Engine imported successfully")
except ImportError as e:
    print(f"❌ Could not import VolumeOIEngine: {e}")
    sys.exit(1)

try:
    import sys
    import os
    # Add parent directory to path to access fetcher
    parent_dir = os.path.dirname(os.path.dirname(__file__))
    sys.path.append(parent_dir)
    
    from tools.fetcher import get_btc_price
    print("✅ Fetcher imported successfully")
except ImportError:
    try:
        # Alternative import method
        from fetcher import get_btc_price
        print("✅ Fetcher imported successfully (alternative method)")
    except ImportError as e:
        print(f"❌ Could not import get_btc_price: {e}")
        print("Creating fallback price function...")
        
        # Fallback function if fetcher fails
        def get_btc_price():
            import requests
            try:
                response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
                if response.status_code == 200:
                    return float(response.json()["price"])
                return 67000.0  # Fallback price
            except:
                return 67000.0  # Fallback price

IST = timezone(timedelta(hours=5, minutes=30))

class ConfluenceAlertEngine:
    def __init__(self):
        self.ema_engine = ProductionEMAEngine()
        self.volume_engine = VolumeOIEngine()
        
        # Alert state tracking (to prevent spam)
        self.alert_state = {}
        self.last_alerts = {}
        self.alert_cooldown = 300  # 5 minutes between same alerts
        
        # Alert configurations - MUCH MORE STRICT
        self.volume_alert_config = {
            "15m": {"spike_threshold": 100, "low_threshold": -80},  # Increased from 50 to 100
            "1h": {"spike_threshold": 150, "low_threshold": -70},   # Increased from 75 to 150
            "4h": {"spike_threshold": 200, "low_threshold": -85},   # Increased from 100 to 200
            "1d": {"spike_threshold": 100, "low_threshold": -60}    # Increased from 50 to 100
        }
        
        self.oi_alert_config = {
            "change_threshold": 25,     # Increased from 10% to 25% - MAJOR changes only
            "surge_threshold": 50       # Increased from 20% to 50% - MASSIVE surges only
        }
        
        # Price movement context requirements
        self.context_requirements = {
            "min_price_change": 2.0,    # Price must move at least 2% for OI alerts
            "min_volume_for_oi": 75,    # Volume must be at least +75% for OI alerts  
            "ema_confluence_min": 1.5,  # EMA distance must be >1.5% for confluence
            "multi_tf_threshold": 3     # Need 3+ timeframes for multi-TF alerts
        }
    
    def check_price_context(self, current_price: float, ema_data: Dict) -> Dict:
        """Check if price movement is significant enough to warrant alerts"""
        context = {
            "significant_move": False,
            "price_change_1h": 0,
            "trend_strength": "weak",
            "above_ema_count": 0
        }
        
        try:
            # Calculate price change (you'd need to store previous price)
            # For now, use EMA distance as proxy for recent movement
            if "1h" in ema_data and "error" not in ema_data["1h"]:
                ema_pct = abs(ema_data["1h"].get("percentage_diff", 0))
                context["price_change_1h"] = ema_pct
                
                # Significant move if >2% from EMA
                if ema_pct >= self.context_requirements["min_price_change"]:
                    context["significant_move"] = True
                    context["trend_strength"] = "strong" if ema_pct >= 3 else "moderate"
            
            # Count how many timeframes are above EMA
            for tf, data in ema_data.items():
                if "error" not in data and data.get("above_ema", False):
                    context["above_ema_count"] += 1
            
            return context
            
        except Exception as e:
            print(f"Error checking price context: {e}")
            return context
    
    def should_send_alert(self, alert_key: str) -> bool:
        """Check cooldown to prevent notification spam"""
        current_time = time.time()
        
        if alert_key in self.last_alerts:
            time_since_last = current_time - self.last_alerts[alert_key]
            if time_since_last < self.alert_cooldown:
                return False
        
        self.last_alerts[alert_key] = current_time
        return True
    
    def send_notification(self, title: str, message: str, alert_key: str):
        """Send notification if not in cooldown"""
        if self.should_send_alert(alert_key):
            try:
                notification.notify(
                    title=title,
                    message=message,
                    timeout=10
                )
                print(f"🚨 ALERT SENT: {title} - {message}")
                return True
            except Exception as e:
                print(f"Notification error: {e}")
                return False
        return False
    
    def check_volume_alerts(self, volume_data: Dict) -> List[Dict]:
        """Check for volume-based alerts"""
        alerts = []
        
        for tf, data in volume_data.items():
            if "error" in data:
                continue
                
            config = self.volume_alert_config.get(tf, {})
            spike_threshold = config.get("spike_threshold", 75)
            low_threshold = config.get("low_threshold", -60)
            
            volume_spike_pct = data.get("volume_spike_pct", 0)
            current_volume = data.get("current_volume", 0)
            
            # Volume spike alerts
            if volume_spike_pct >= spike_threshold:
                alert = {
                    "type": "volume_spike",
                    "timeframe": tf,
                    "message": f"🔥 MAJOR VOLUME SPIKE: +{volume_spike_pct:.0f}% on {tf.upper()}",
                    "details": f"Volume: {current_volume:,.0f} ({volume_spike_pct:+.1f}% vs average)",
                    "priority": "critical" if volume_spike_pct >= spike_threshold * 2 else "high",
                    "alert_key": f"volume_spike_{tf}_{int(volume_spike_pct/20)*20}"
                }
                alerts.append(alert)
            
            # Low volume alerts (for major drops)
            elif volume_spike_pct <= low_threshold:
                alert = {
                    "type": "volume_low",
                    "timeframe": tf,
                    "message": f"💤 EXTREMELY LOW VOLUME: {volume_spike_pct:.0f}% on {tf.upper()}",
                    "details": f"Volume: {current_volume:,.0f} (significantly below average)",
                    "priority": "medium",
                    "alert_key": f"volume_low_{tf}_{int(abs(volume_spike_pct)/20)*20}"
                }
                alerts.append(alert)
        
        return alerts
    
    def check_oi_alerts(self, volume_data: Dict, price_context: Dict) -> List[Dict]:
        """Check for Open Interest alerts - NOW WITH PRICE CONTEXT"""
        alerts = []
        
        # Only send OI alerts if price movement is significant
        if not price_context.get("significant_move", False):
            return alerts  # No OI alerts for small price moves
        
        for tf, data in volume_data.items():
            if "error" in data:
                continue
                
            oi_change_1p = data.get("oi_change_1p", 0)
            oi_change_5p = data.get("oi_change_5p", 0)
            current_oi = data.get("current_oi", 0)
            volume_spike_pct = data.get("volume_spike_pct", 0)
            
            # Require volume spike for OI alerts (confluence filter)
            volume_threshold = self.context_requirements["min_volume_for_oi"]
            if volume_spike_pct < volume_threshold:
                continue  # Skip OI alerts without volume confirmation
            
            # MUCH stricter OI thresholds
            if abs(oi_change_1p) >= self.oi_alert_config["change_threshold"]:
                direction = "RISING" if oi_change_1p > 0 else "FALLING"
                emoji = "📈" if oi_change_1p > 0 else "📉"
                
                alert = {
                    "type": "oi_change",
                    "timeframe": tf,
                    "message": f"{emoji} MAJOR OI {direction}: {oi_change_1p:+.1f}% on {tf.upper()}",
                    "details": f"OI: {current_oi:,.0f} BTC + Volume: +{volume_spike_pct:.0f}% + Price move: {price_context['trend_strength']}",
                    "priority": "critical",
                    "alert_key": f"oi_change_{tf}_{int(abs(oi_change_1p)/15)*15}"
                }
                alerts.append(alert)
            
            # Only MASSIVE OI surges
            if abs(oi_change_5p) >= self.oi_alert_config["surge_threshold"]:
                direction = "SURGE" if oi_change_5p > 0 else "COLLAPSE"
                emoji = "🔥" if oi_change_5p > 0 else "❄️"
                
                alert = {
                    "type": "oi_surge",
                    "timeframe": tf,
                    "message": f"{emoji} MASSIVE OI {direction}: {oi_change_5p:+.1f}% on {tf.upper()}",
                    "details": f"MAJOR institutional activity + Volume spike +{volume_spike_pct:.0f}%",
                    "priority": "critical",
                    "alert_key": f"oi_surge_{tf}_{int(abs(oi_change_5p)/25)*25}"
                }
                alerts.append(alert)
        
        return alerts
    
    def check_ema_confluence_alerts(self, ema_data: Dict, volume_data: Dict, current_price: float, price_context: Dict) -> List[Dict]:
        """Check for EMA + Volume confluence alerts - WITH CONTEXT FILTERS"""
        alerts = []
        
        # Check each timeframe for EMA+Volume confluence
        for tf in ["15m", "1h", "4h", "1d"]:
            if (tf not in ema_data or tf not in volume_data or 
                "error" in ema_data[tf] or "error" in volume_data[tf]):
                continue
            
            ema_info = ema_data[tf]
            vol_info = volume_data[tf]
            
            above_ema = ema_info.get("above_ema", False)
            ema_pct = ema_info.get("percentage_diff", 0)
            volume_spike = vol_info.get("is_volume_spike", False)
            volume_pct = vol_info.get("volume_spike_pct", 0)
            
            # STRICTER CONFLUENCE REQUIREMENTS
            min_ema_distance = self.context_requirements["ema_confluence_min"]
            
            # Strong bullish confluence: Above EMA + Volume spike + STRONG signals
            if (above_ema and volume_spike and ema_pct > min_ema_distance and 
                volume_pct > 100 and price_context.get("significant_move", False)):
                
                alert = {
                    "type": "bullish_confluence",
                    "timeframe": tf,
                    "message": f"🚀 STRONG BULLISH CONFLUENCE on {tf.upper()}",
                    "details": f"Price +{ema_pct:.1f}% above EMA + Volume spike +{volume_pct:.0f}% + {price_context['trend_strength']} trend",
                    "priority": "critical" if volume_pct > 200 else "high",
                    "alert_key": f"bullish_confluence_{tf}"
                }
                alerts.append(alert)
            
            # Strong bearish confluence: Below EMA + Volume spike + STRONG signals
            elif (not above_ema and volume_spike and abs(ema_pct) > min_ema_distance and 
                  volume_pct > 100 and price_context.get("significant_move", False)):
                
                alert = {
                    "type": "bearish_confluence",
                    "timeframe": tf,
                    "message": f"🐻 STRONG BEARISH CONFLUENCE on {tf.upper()}",
                    "details": f"Price {ema_pct:.1f}% below EMA + Volume spike +{volume_pct:.0f}% + {price_context['trend_strength']} trend",
                    "priority": "critical" if volume_pct > 200 else "high",
                    "alert_key": f"bearish_confluence_{tf}"
                }
                alerts.append(alert)
        
        return alerts
    
    def check_triple_confluence_alerts(self, ema_data: Dict, volume_data: Dict) -> List[Dict]:
        """Check for EMA + Volume + OI triple confluence"""
        alerts = []
        
        for tf in ["1h", "4h", "1d"]:  # Focus on higher timeframes for triple confluence
            if (tf not in ema_data or tf not in volume_data or 
                "error" in ema_data[tf] or "error" in volume_data[tf]):
                continue
            
            ema_info = ema_data[tf]
            vol_info = volume_data[tf]
            
            above_ema = ema_info.get("above_ema", False)
            ema_pct = ema_info.get("percentage_diff", 0)
            volume_spike = vol_info.get("is_volume_spike", False)
            volume_pct = vol_info.get("volume_spike_pct", 0)
            oi_change = vol_info.get("oi_change_1p", 0)
            
            # Triple bullish confluence: Above EMA + Volume spike + Rising OI
            if (above_ema and volume_spike and oi_change > 15 and 
                ema_pct > 2 and volume_pct > 150):
                
                alert = {
                    "type": "triple_bullish_confluence", 
                    "timeframe": tf,
                    "message": f"🎯 TRIPLE BULLISH CONFLUENCE on {tf.upper()}",
                    "details": f"Price +{ema_pct:.1f}% above EMA + Volume +{volume_pct:.0f}% + OI +{oi_change:.1f}%",
                    "priority": "critical",
                    "alert_key": f"triple_bullish_{tf}"
                }
                alerts.append(alert)
            
            # Triple bearish confluence: Below EMA + Volume spike + Rising OI (shorts)
            elif (not above_ema and volume_spike and oi_change > 15 and 
                  abs(ema_pct) > 2 and volume_pct > 150):
                
                alert = {
                    "type": "triple_bearish_confluence",
                    "timeframe": tf, 
                    "message": f"🎯 TRIPLE BEARISH CONFLUENCE on {tf.upper()}",
                    "details": f"Price {ema_pct:.1f}% below EMA + Volume +{volume_pct:.0f}% + OI +{oi_change:.1f}%",
                    "priority": "critical",
                    "alert_key": f"triple_bearish_{tf}"
                }
                alerts.append(alert)
        
        return alerts
    
    def check_divergence_alerts(self, volume_data: Dict) -> List[Dict]:
        """Check for price-volume divergence alerts"""
        alerts = []
        
        for tf, data in volume_data.items():
            if "error" in data:
                continue
                
            divergence = data.get("divergence")
            price_trend = data.get("price_trend", "sideways")
            
            if divergence == "bearish_divergence":
                alert = {
                    "type": "bearish_divergence",
                    "timeframe": tf,
                    "message": f"⚠️ BEARISH DIVERGENCE on {tf.upper()}",
                    "details": "Price rising but volume declining - Trend may weaken",
                    "priority": "medium",
                    "alert_key": f"bearish_div_{tf}"
                }
                alerts.append(alert)
            
            elif divergence == "potential_reversal":
                alert = {
                    "type": "potential_reversal",
                    "timeframe": tf,
                    "message": f"🔄 POTENTIAL REVERSAL on {tf.upper()}",
                    "details": "Price falling with rising volume - Possible bottom formation",
                    "priority": "high",
                    "alert_key": f"reversal_{tf}"
                }
                alerts.append(alert)
        
        return alerts
    
    def check_multi_timeframe_alerts(self, ema_data: Dict, volume_data: Dict) -> List[Dict]:
        """Check for signals across multiple timeframes"""
        alerts = []
        
        # Count bullish/bearish signals across timeframes
        bullish_ema_count = 0
        bearish_ema_count = 0
        volume_spike_count = 0
        
        timeframes = ["15m", "1h", "4h", "1d"]
        valid_timeframes = 0
        
        for tf in timeframes:
            if (tf in ema_data and "error" not in ema_data[tf] and
                tf in volume_data and "error" not in volume_data[tf]):
                
                valid_timeframes += 1
                
                if ema_data[tf].get("above_ema", False):
                    bullish_ema_count += 1
                else:
                    bearish_ema_count += 1
                
                if volume_data[tf].get("is_volume_spike", False):
                    volume_spike_count += 1
        
        if valid_timeframes >= 3:  # Need at least 3 valid timeframes
            # Multi-timeframe bullish alignment
            if bullish_ema_count >= 3 and volume_spike_count >= 2:
                alert = {
                    "type": "multi_tf_bullish",
                    "timeframe": "multi",
                    "message": f"🌟 MULTI-TF BULLISH ALIGNMENT: {bullish_ema_count}/{valid_timeframes} above EMA",
                    "details": f"{volume_spike_count} timeframes showing volume spikes",
                    "priority": "critical",
                    "alert_key": "multi_tf_bullish"
                }
                alerts.append(alert)
            
            # Multi-timeframe bearish alignment
            elif bearish_ema_count >= 3 and volume_spike_count >= 2:
                alert = {
                    "type": "multi_tf_bearish", 
                    "timeframe": "multi",
                    "message": f"🌟 MULTI-TF BEARISH ALIGNMENT: {bearish_ema_count}/{valid_timeframes} below EMA",
                    "details": f"{volume_spike_count} timeframes showing volume spikes",
                    "priority": "critical",
                    "alert_key": "multi_tf_bearish"
                }
                alerts.append(alert)
        
        return alerts
    
    def run_confluence_analysis(self, symbol: str = "BTCUSDT") -> Dict:
        """Run complete confluence analysis and generate alerts"""
        try:
            print(f"\n🔍 Running confluence analysis for {symbol}...")
            
            # Get current price
            current_price = get_btc_price()
            
            # Get EMA data
            print("📈 Fetching EMA data...")
            ema_data = self.ema_engine.analyze_ema(symbol)
            
            # Get Volume/OI data  
            print("📊 Fetching Volume/OI data...")
            volume_data = self.volume_engine.analyze_volume_oi(symbol)
            
            # Check price movement context FIRST
            price_context = self.check_price_context(current_price, ema_data)
            
            print(f"💰 Price Context: {price_context['trend_strength']} move ({price_context['price_change_1h']:.1f}% from EMA)")
            
            # Generate all alert types with context filtering
            all_alerts = []
            
            # Volume alerts (always check - volume is primary signal)
            volume_alerts = self.check_volume_alerts(volume_data)
            all_alerts.extend(volume_alerts)
            
            # OI alerts (only with price context)
            oi_alerts = self.check_oi_alerts(volume_data, price_context)
            all_alerts.extend(oi_alerts)
            
            # EMA confluence alerts (with stricter filters)
            ema_confluence = self.check_ema_confluence_alerts(ema_data, volume_data, current_price, price_context)
            all_alerts.extend(ema_confluence)
            
            # Triple confluence alerts (only for major moves)
            if price_context.get("significant_move", False):
                triple_confluence = self.check_triple_confluence_alerts(ema_data, volume_data)
                all_alerts.extend(triple_confluence)
            
            # Divergence alerts (keep these - important for reversals)
            divergence_alerts = self.check_divergence_alerts(volume_data)
            all_alerts.extend(divergence_alerts)
            
            # Multi-timeframe alerts (only for very strong signals)
            if price_context["above_ema_count"] >= 3:  # Strong trend required
                multi_tf_alerts = self.check_multi_timeframe_alerts(ema_data, volume_data)
                all_alerts.extend(multi_tf_alerts)
            
            # Sort alerts by priority
            priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            all_alerts.sort(key=lambda x: priority_order.get(x["priority"], 3))
            
            # Send notifications for high priority alerts
            notifications_sent = 0
            for alert in all_alerts:
                if alert["priority"] in ["critical", "high"]:
                    title = f"🚨 {symbol} Alert"
                    message = alert["message"]
                    
                    if self.send_notification(title, message, alert["alert_key"]):
                        notifications_sent += 1
            
            return {
                "timestamp": datetime.now(IST).isoformat(),
                "symbol": symbol,
                "current_price": current_price,
                "price_context": price_context,
                "total_alerts": len(all_alerts),
                "notifications_sent": notifications_sent,
                "alerts": all_alerts,
                "ema_data": ema_data,
                "volume_data": volume_data
            }
            
        except Exception as e:
            print(f"❌ Confluence analysis error: {e}")
            return {"error": str(e), "timestamp": datetime.now(IST).isoformat()}
    
    def print_confluence_summary(self, results: Dict):
        """Print a summary of confluence analysis results"""
        if "error" in results:
            print(f"❌ Analysis failed: {results['error']}")
            return
        
        print(f"\n🎯 SMART CONFLUENCE ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"🕒 Time: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
        print(f"💰 {results['symbol']}: ${results['current_price']:,.2f}")
        
        # Show price context
        context = results.get("price_context", {})
        print(f"📊 Market Context: {context.get('trend_strength', 'unknown')} trend")
        print(f"📈 EMA Position: {context.get('above_ema_count', 0)}/4 timeframes above EMA")
        
        print(f"🚨 Total Alerts: {results['total_alerts']}")
        print(f"📢 Notifications Sent: {results['notifications_sent']}")
        
        if results['alerts']:
            print(f"\n🔥 ACTIVE ALERTS:")
            for alert in results['alerts']:
                priority_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}
                icon = priority_icon.get(alert['priority'], "⚪")
                
                print(f"   {icon} {alert['message']}")
                print(f"      └─ {alert['details']}")
        else:
            print(f"\n😴 No significant alerts - Market conditions don't meet strict criteria")
    
    def start_monitoring(self, symbol: str = "BTCUSDT", interval: int = 60):
        """Start continuous monitoring with specified interval"""
        print(f"🚀 Starting SMART confluence monitoring for {symbol} (every {interval}s)")
        print("📊 Using strict filters - Only major market events will trigger alerts")
        print("Press Ctrl+C to stop monitoring...")
        
        try:
            while True:
                results = self.run_confluence_analysis(symbol)
                self.print_confluence_summary(results)
                
                print(f"\n⏳ Next analysis in {interval} seconds...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print(f"\n🛑 Monitoring stopped by user")
        except Exception as e:
            print(f"\n❌ Monitoring error: {e}")


# Convenience functions
def run_single_analysis(symbol="BTCUSDT"):
    """Run a single confluence analysis"""
    engine = ConfluenceAlertEngine()
    results = engine.run_confluence_analysis(symbol)
    engine.print_confluence_summary(results)
    return results

def start_monitoring(symbol="BTCUSDT", interval=60):
    """Start continuous monitoring"""
    engine = ConfluenceAlertEngine()
    engine.start_monitoring(symbol, interval)


if __name__ == "__main__":
    # Run single analysis
    print("🔍 Running single SMART confluence analysis...")
    run_single_analysis("BTCUSDT")
    
    print("\n" + "="*60)
    
    # Ask user if they want continuous monitoring
    try:
        response = input("\n🚀 Start continuous SMART monitoring? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            start_monitoring("BTCUSDT", 60)  # Check every 60 seconds
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")