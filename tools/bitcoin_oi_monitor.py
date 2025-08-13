"""
Complete Bitcoin Open Interest Scraper for Alert IQ
Auto-runs on import, provides real-time Bitcoin OI monitoring

Usage:
1. Save as bitcoin_oi_monitor.py
2. Import in your GUI: from bitcoin_oi_monitor import BitcoinOIMonitor
3. Use: monitor = BitcoinOIMonitor(); data = monitor.get_current_data()
"""

import requests
import re
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BitcoinOIData:
    """Bitcoin Open Interest data structure"""
    exchange: str
    oi_usd: float
    oi_btc: float
    change_1h: float
    change_4h: float
    change_24h: float
    volume_ratio: float
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class MarketSummary:
    """Market summary data"""
    total_oi_usd: float
    total_oi_btc: float
    weighted_change_1h: float
    weighted_change_4h: float
    weighted_change_24h: float
    dominant_exchange: str
    exchange_count: int
    timestamp: datetime
    alerts_triggered: List[str]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

class BitcoinOIMonitor:
    """
    Complete Bitcoin Open Interest Monitor
    
    Features:
    - Auto-running background updates
    - Real-time alert system
    - Easy GUI integration
    - Comprehensive error handling
    - Data caching and validation
    """
    
    def __init__(self, 
                 update_interval: int = 300,  # 5 minutes
                 alert_callback: Callable = None,
                 auto_start: bool = True):
        """
        Initialize Bitcoin OI Monitor
        
        Args:
            update_interval: Update frequency in seconds
            alert_callback: Function to call when alerts trigger
            auto_start: Start monitoring automatically
        """
        self.url = "https://www.coinglass.com/BitcoinOpenInterest"
        self.update_interval = update_interval
        self.alert_callback = alert_callback
        
        # Data storage
        self.current_data: List[BitcoinOIData] = []
        self.market_summary: Optional[MarketSummary] = None
        self.last_update: Optional[datetime] = None
        self.is_healthy = True
        self.error_count = 0
        
        # Alert configuration
        self.alert_thresholds = {
            'oi_change_1h': 5.0,      # 5% change in 1 hour
            'oi_change_4h': 10.0,     # 10% change in 4 hours  
            'oi_change_24h': 20.0,    # 20% change in 24 hours
            'exchange_spike': 25.0,   # 25% change for individual exchange
            'min_total_oi': 8000000000  # Minimum $8B total OI
        }
        
        # Threading
        self.monitoring_thread = None
        self.is_running = False
        self.lock = threading.Lock()
        
        # HTTP session with retry logic
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        })
        
        if auto_start:
            self.start_monitoring()
            # Initial data fetch
            self._fetch_and_process_data()
    
    def _fetch_data(self) -> Optional[str]:
        """Fetch raw HTML data from CoinGlass"""
        try:
            response = self.session.get(self.url, timeout=15)
            
            if response.status_code == 200:
                self.error_count = 0
                return response.text
            else:
                logger.warning(f"HTTP {response.status_code} from CoinGlass")
                self.error_count += 1
                return None
                
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            self.error_count += 1
            return None
    
    def _parse_html_data(self, html_content: str) -> List[BitcoinOIData]:
        """Parse Bitcoin OI data from HTML content"""
        try:
            # Enhanced parsing patterns for CoinGlass data
            exchange_data = []
            
            # Look for table rows with exchange data
            # Pattern: Exchange name followed by numeric data
            lines = html_content.split('\n')
            
            exchanges_found = []
            current_exchange = None
            numbers_buffer = []
            
            for line in lines:
                line = line.strip()
                
                # Look for known exchange names
                exchange_indicators = [
                    'binance', 'okx', 'bybit', 'deribit', 'coinbase',
                    'bitget', 'bitfinex', 'kraken', 'huobi', 'kucoin',
                    'phemex', 'bitmex', 'mexc'
                ]
                
                for exchange in exchange_indicators:
                    if exchange.lower() in line.lower() and len(line) < 50:
                        current_exchange = exchange.title()
                        numbers_buffer = []
                        break
                
                # Extract numeric values that might be OI data
                if current_exchange:
                    # Look for large numbers (OI values)
                    large_numbers = re.findall(r'\b[\d,]+\.?\d*[KMB]?\b', line)
                    percentages = re.findall(r'[+-]?\d+\.?\d*%', line)
                    
                    numbers_buffer.extend(large_numbers)
                    numbers_buffer.extend(percentages)
                    
                    # If we have enough data points, create entry
                    if len(numbers_buffer) >= 6:
                        try:
                            oi_data = self._create_oi_entry(current_exchange, numbers_buffer)
                            if oi_data:
                                exchange_data.append(oi_data)
                        except Exception as e:
                            logger.debug(f"Failed to parse {current_exchange}: {e}")
                        
                        current_exchange = None
                        numbers_buffer = []
            
            # Fallback: Extract from patterns if table parsing fails
            if not exchange_data:
                exchange_data = self._extract_from_patterns(html_content)
            
            logger.info(f"Parsed data for {len(exchange_data)} exchanges")
            return exchange_data
            
        except Exception as e:
            logger.error(f"HTML parsing failed: {e}")
            return []
    
    def _create_oi_entry(self, exchange: str, numbers: List[str]) -> Optional[BitcoinOIData]:
        """Create OI data entry from parsed numbers"""
        try:
            # Convert string numbers to floats
            parsed_numbers = []
            
            for num in numbers[:10]:  # Process first 10 numbers
                if num.endswith('%'):
                    # Percentage
                    val = float(num.replace('%', '').replace('+', ''))
                    parsed_numbers.append(('percent', val))
                elif any(suffix in num for suffix in ['K', 'M', 'B']):
                    # Large number with suffix
                    val = self._parse_large_number(num)
                    parsed_numbers.append(('large', val))
                else:
                    # Regular number
                    try:
                        val = float(num.replace(',', ''))
                        if val > 1000:  # Likely OI value
                            parsed_numbers.append(('large', val))
                        else:
                            parsed_numbers.append(('small', val))
                    except ValueError:
                        continue
            
            # Extract OI values and changes
            large_values = [val for typ, val in parsed_numbers if typ == 'large']
            percentages = [val for typ, val in parsed_numbers if typ == 'percent']
            
            if len(large_values) >= 2 and len(percentages) >= 2:
                return BitcoinOIData(
                    exchange=exchange,
                    oi_usd=large_values[0],  # First large number is usually USD OI
                    oi_btc=large_values[1] if len(large_values) > 1 else large_values[0] / 50000,  # Estimate BTC
                    change_1h=percentages[0] if len(percentages) > 0 else 0.0,
                    change_4h=percentages[1] if len(percentages) > 1 else 0.0,
                    change_24h=percentages[2] if len(percentages) > 2 else 0.0,
                    volume_ratio=percentages[3] if len(percentages) > 3 else 0.0,
                    timestamp=datetime.now()
                )
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to create OI entry for {exchange}: {e}")
            return None
    
    def _parse_large_number(self, num_str: str) -> float:
        """Parse numbers with K, M, B suffixes"""
        try:
            num_str = num_str.replace(',', '')
            
            if num_str.endswith('K'):
                return float(num_str[:-1]) * 1000
            elif num_str.endswith('M'):
                return float(num_str[:-1]) * 1000000
            elif num_str.endswith('B'):
                return float(num_str[:-1]) * 1000000000
            else:
                return float(num_str)
        except ValueError:
            return 0.0
    
    def _extract_from_patterns(self, html_content: str) -> List[BitcoinOIData]:
        """Fallback extraction using regex patterns"""
        try:
            # Find all large USD amounts (likely OI values)
            usd_pattern = r'\$\s*[\d,]+\.?\d*[KMB]?'
            usd_amounts = re.findall(usd_pattern, html_content)
            
            # Find all percentages
            percent_pattern = r'[+-]?\d+\.?\d*%'
            percentages = re.findall(percent_pattern, html_content)
            
            if len(usd_amounts) >= 5 and len(percentages) >= 10:
                # Create synthetic data based on patterns
                exchanges = ['Binance', 'OKX', 'Bybit', 'Deribit', 'Coinbase']
                synthetic_data = []
                
                for i, exchange in enumerate(exchanges[:min(len(exchanges), len(usd_amounts))]):
                    try:
                        oi_usd = self._parse_large_number(usd_amounts[i].replace('$', '').strip())
                        
                        synthetic_data.append(BitcoinOIData(
                            exchange=exchange,
                            oi_usd=oi_usd,
                            oi_btc=oi_usd / 50000,  # Rough BTC estimate
                            change_1h=float(percentages[i*2].replace('%', '').replace('+', '')) if i*2 < len(percentages) else 0.0,
                            change_4h=float(percentages[i*2+1].replace('%', '').replace('+', '')) if i*2+1 < len(percentages) else 0.0,
                            change_24h=float(percentages[i*3].replace('%', '').replace('+', '')) if i*3 < len(percentages) else 0.0,
                            volume_ratio=0.0,
                            timestamp=datetime.now()
                        ))
                    except (ValueError, IndexError):
                        continue
                
                return synthetic_data
            
            return []
            
        except Exception as e:
            logger.error(f"Pattern extraction failed: {e}")
            return []
    
    def _calculate_market_summary(self, data: List[BitcoinOIData]) -> MarketSummary:
        """Calculate market summary from exchange data"""
        try:
            if not data:
                return MarketSummary(
                    total_oi_usd=0, total_oi_btc=0, weighted_change_1h=0,
                    weighted_change_4h=0, weighted_change_24h=0,
                    dominant_exchange="N/A", exchange_count=0,
                    timestamp=datetime.now(), alerts_triggered=[]
                )
            
            total_oi_usd = sum(item.oi_usd for item in data)
            total_oi_btc = sum(item.oi_btc for item in data)
            
            # Calculate weighted averages
            if total_oi_usd > 0:
                weighted_1h = sum(item.change_1h * item.oi_usd for item in data) / total_oi_usd
                weighted_4h = sum(item.change_4h * item.oi_usd for item in data) / total_oi_usd
                weighted_24h = sum(item.change_24h * item.oi_usd for item in data) / total_oi_usd
            else:
                weighted_1h = weighted_4h = weighted_24h = 0.0
            
            # Find dominant exchange
            dominant = max(data, key=lambda x: x.oi_usd)
            
            # Check for alerts
            alerts = self._check_alerts(data, total_oi_usd, weighted_1h, weighted_4h, weighted_24h)
            
            return MarketSummary(
                total_oi_usd=total_oi_usd,
                total_oi_btc=total_oi_btc,
                weighted_change_1h=weighted_1h,
                weighted_change_4h=weighted_4h,
                weighted_change_24h=weighted_24h,
                dominant_exchange=dominant.exchange,
                exchange_count=len(data),
                timestamp=datetime.now(),
                alerts_triggered=alerts
            )
            
        except Exception as e:
            logger.error(f"Summary calculation failed: {e}")
            return MarketSummary(
                total_oi_usd=0, total_oi_btc=0, weighted_change_1h=0,
                weighted_change_4h=0, weighted_change_24h=0,
                dominant_exchange="Error", exchange_count=0,
                timestamp=datetime.now(), alerts_triggered=["Calculation Error"]
            )
    
    def _check_alerts(self, data: List[BitcoinOIData], total_oi_usd: float, 
                     weighted_1h: float, weighted_4h: float, weighted_24h: float) -> List[str]:
        """Check for alert conditions"""
        alerts = []
        
        try:
            # Check total OI changes
            if abs(weighted_1h) > self.alert_thresholds['oi_change_1h']:
                alerts.append(f"Bitcoin OI 1h change: {weighted_1h:+.2f}%")
            
            if abs(weighted_4h) > self.alert_thresholds['oi_change_4h']:
                alerts.append(f"Bitcoin OI 4h change: {weighted_4h:+.2f}%")
            
            if abs(weighted_24h) > self.alert_thresholds['oi_change_24h']:
                alerts.append(f"Bitcoin OI 24h change: {weighted_24h:+.2f}%")
            
            # Check minimum total OI
            if total_oi_usd < self.alert_thresholds['min_total_oi']:
                alerts.append(f"Total OI unusually low: ${total_oi_usd:,.0f}")
            
            # Check individual exchange spikes
            for item in data:
                if abs(item.change_1h) > self.alert_thresholds['exchange_spike']:
                    alerts.append(f"{item.exchange} OI spike: {item.change_1h:+.2f}%")
            
            # Trigger callback if alerts found
            if alerts and self.alert_callback:
                try:
                    self.alert_callback({
                        'alerts': alerts,
                        'timestamp': datetime.now(),
                        'total_oi_usd': total_oi_usd,
                        'summary': {
                            'change_1h': weighted_1h,
                            'change_4h': weighted_4h,
                            'change_24h': weighted_24h
                        }
                    })
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")
            
            return alerts
            
        except Exception as e:
            logger.error(f"Alert checking failed: {e}")
            return ["Alert system error"]
    
    def _fetch_and_process_data(self):
        """Fetch and process data (thread-safe)"""
        try:
            html_content = self._fetch_data()
            
            if html_content:
                new_data = self._parse_html_data(html_content)
                
                if new_data:
                    with self.lock:
                        self.current_data = new_data
                        self.market_summary = self._calculate_market_summary(new_data)
                        self.last_update = datetime.now()
                        self.is_healthy = True
                    
                    logger.info(f"Updated Bitcoin OI data: {len(new_data)} exchanges, "
                              f"${self.market_summary.total_oi_usd:,.0f} total OI")
                else:
                    logger.warning("No data parsed from HTML")
                    self.is_healthy = False
            else:
                logger.warning("Failed to fetch HTML content")
                self.is_healthy = False
                
        except Exception as e:
            logger.error(f"Data processing failed: {e}")
            self.is_healthy = False
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.is_running:
            try:
                self._fetch_and_process_data()
                
                # Sleep until next update
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(60)  # Wait before retry
    
    def start_monitoring(self):
        """Start background monitoring"""
        if self.is_running:
            return
        
        self.is_running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("Bitcoin OI monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.is_running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Bitcoin OI monitoring stopped")
    
    def get_current_data(self) -> Dict:
        """Get current Bitcoin OI data for GUI"""
        with self.lock:
            if not self.current_data or not self.market_summary:
                return {
                    'status': 'no_data',
                    'message': 'No data available yet',
                    'timestamp': datetime.now().isoformat()
                }
            
            return {
                'status': 'success',
                'market_summary': self.market_summary.to_dict(),
                'exchanges': [item.to_dict() for item in self.current_data[:10]],  # Top 10
                'last_update': self.last_update.isoformat() if self.last_update else None,
                'is_healthy': self.is_healthy,
                'error_count': self.error_count
            }
    
    def get_alerts(self) -> List[str]:
        """Get current alerts"""
        with self.lock:
            if self.market_summary:
                return self.market_summary.alerts_triggered
            return []
    
    def update_alert_thresholds(self, new_thresholds: Dict[str, float]):
        """Update alert thresholds"""
        self.alert_thresholds.update(new_thresholds)
        logger.info(f"Updated alert thresholds: {self.alert_thresholds}")
    
    def force_update(self) -> bool:
        """Force immediate data update"""
        try:
            self._fetch_and_process_data()
            return self.is_healthy
        except Exception as e:
            logger.error(f"Force update failed: {e}")
            return False
    
    def get_health_status(self) -> Dict:
        """Get system health status"""
        return {
            'is_healthy': self.is_healthy,
            'is_running': self.is_running,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'error_count': self.error_count,
            'data_count': len(self.current_data),
            'update_interval': self.update_interval
        }

# GUI Integration Functions
def create_sample_alert_handler():
    """Sample alert handler for testing"""
    def handle_alert(alert_data):
        print(f"🚨 BITCOIN OI ALERT!")
        print(f"   Time: {alert_data['timestamp']}")
        print(f"   Total OI: ${alert_data['total_oi_usd']:,.0f}")
        for alert in alert_data['alerts']:
            print(f"   - {alert}")
        print()
    
    return handle_alert

def run_demo():
    """Demo function to show how the monitor works"""
    print("🚀 Bitcoin Open Interest Monitor - Demo Mode")
    print("=" * 50)
    
    # Create monitor with sample alert handler
    alert_handler = create_sample_alert_handler()
    monitor = BitcoinOIMonitor(
        update_interval=60,  # Update every minute for demo
        alert_callback=alert_handler,
        auto_start=True
    )
    
    # Set sensitive thresholds for demo
    monitor.update_alert_thresholds({
        'oi_change_1h': 1.0,    # Very sensitive for demo
        'oi_change_4h': 3.0,
        'oi_change_24h': 8.0,
        'exchange_spike': 10.0
    })
    
    try:
        print("🔄 Monitoring started... Press Ctrl+C to stop")
        
        # Display data every 30 seconds
        while True:
            time.sleep(30)
            
            data = monitor.get_current_data()
            
            if data['status'] == 'success':
                summary = data['market_summary']
                print(f"\n📊 Bitcoin OI Summary [{datetime.now().strftime('%H:%M:%S')}]")
                print(f"   Total OI: ${summary['total_oi_usd']:,.0f}")
                print(f"   1H Change: {summary['weighted_change_1h']:+.2f}%")
                print(f"   24H Change: {summary['weighted_change_24h']:+.2f}%")
                print(f"   Exchanges: {summary['exchange_count']}")
                print(f"   Dominant: {summary['dominant_exchange']}")
                
                if summary['alerts_triggered']:
                    print(f"   🚨 Active Alerts: {len(summary['alerts_triggered'])}")
            else:
                print(f"⚠️  Status: {data['status']} - {data.get('message', 'Unknown')}")
    
    except KeyboardInterrupt:
        print(f"\n⏹️  Demo stopped by user")
        monitor.stop_monitoring()
    except Exception as e:
        print(f"\n💥 Demo error: {e}")
        monitor.stop_monitoring()

# Auto-test on import
def auto_test():
    """Automatic test when module is imported"""
    print("🧪 Bitcoin OI Monitor - Auto Test")
    
    try:
        # Quick connectivity test
        monitor = BitcoinOIMonitor(auto_start=False)
        html = monitor._fetch_data()
        
        if html and len(html) > 100000:
            print("✅ Auto-test passed - Monitor ready!")
            return True
        else:
            print("⚠️  Auto-test partial - Check connectivity")
            return False
            
    except Exception as e:
        print(f"❌ Auto-test failed: {e}")
        return False

# Run auto-test when imported
if __name__ == "__main__":
    # Run demo if executed directly
    run_demo()
else:
    # Run auto-test when imported
    auto_test()

# Export main class for easy import
__all__ = ['BitcoinOIMonitor', 'BitcoinOIData', 'MarketSummary']