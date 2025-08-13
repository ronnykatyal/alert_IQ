"""
Enhanced Telegram Alert Pusher - Auto-Start + Market Analysis
A comprehensive application that monitors AlertIQ's JSON files and pushes
notifications for alerts, confluence signals, and market summaries.

Features:
- Auto-start monitoring with saved settings
- Multiple file monitoring (alerts + confluence)
- Market summary notifications
- Reversal detection and confluence alerts

Author: AlertIQ Team
Version: 2.0 (Enhanced Auto-Start)
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import json
import time
import threading
from datetime import datetime
import os
import sys
from pathlib import Path
import requests
from typing import Dict, List, Optional
import glob

class EnhancedTelegramConfig:
    """Enhanced Telegram configuration with auto-start settings"""
    
    def __init__(self):
        self.config_file = "telegram_config.json"
        self.bot_token = ""
        self.chat_id = ""
        self.alerts_file = ""
        self.confluence_file = ""
        self.auto_start = False
        self.monitor_confluence = True
        self.send_market_summaries = True
        self.summary_interval = 30  # minutes
        self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.bot_token = config.get('bot_token', '')
                    self.chat_id = config.get('chat_id', '')
                    self.alerts_file = config.get('alerts_file', '')
                    self.confluence_file = config.get('confluence_file', '')
                    self.auto_start = config.get('auto_start', False)
                    self.monitor_confluence = config.get('monitor_confluence', True)
                    self.send_market_summaries = config.get('send_market_summaries', True)
                    self.summary_interval = config.get('summary_interval', 30)
                    print(f"✅ Enhanced config loaded")
        except Exception as e:
            print(f"⚠️ Could not load config: {e}")
    
    def save_config(self):
        """Save configuration to file"""
        try:
            config = {
                'bot_token': self.bot_token,
                'chat_id': self.chat_id,
                'alerts_file': self.alerts_file,
                'confluence_file': self.confluence_file,
                'auto_start': self.auto_start,
                'monitor_confluence': self.monitor_confluence,
                'send_market_summaries': self.send_market_summaries,
                'summary_interval': self.summary_interval
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"✅ Enhanced config saved")
            return True
        except Exception as e:
            print(f"❌ Could not save config: {e}")
            return False
    
    def is_configured(self):
        """Check if basic Telegram is configured"""
        return bool(self.bot_token and self.chat_id)
    
    def can_auto_start(self):
        """Check if can auto-start monitoring"""
        return (self.is_configured() and 
                self.auto_start and 
                (self.alerts_file or self.confluence_file))

class EnhancedTelegramNotifier:
    """Enhanced notifier with market analysis capabilities"""
    
    def __init__(self, config: EnhancedTelegramConfig):
        self.config = config
        self.last_sent = {}
        self.last_summary_time = 0
        
    def send_message(self, message: str, alert_key: str = None, force_send: bool = False) -> bool:
        """Send message with enhanced rate limiting"""
        try:
            if not self.config.is_configured():
                print("❌ Telegram not configured")
                return False
            
            # Rate limiting - but allow forced sends (like summaries)
            current_time = time.time()
            if not force_send and alert_key and alert_key in self.last_sent:
                time_since_last = current_time - self.last_sent[alert_key]
                if time_since_last < 300:  # 5 minutes
                    print(f"⏳ Rate limited: {alert_key} (sent {time_since_last:.1f}s ago)")
                    return False
            
            # Send to Telegram
            url = f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"
            data = {
                'chat_id': self.config.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                if alert_key:
                    self.last_sent[alert_key] = current_time
                print(f"✅ Message sent to Telegram")
                return True
            else:
                print(f"❌ Telegram API error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to send Telegram message: {e}")
            return False
    
    def send_market_summary(self, market_data: Dict) -> bool:
        """Send market summary notification"""
        try:
            current_time = time.time()
            
            # Check if enough time has passed since last summary
            time_since_last = current_time - self.last_summary_time
            min_interval = self.config.summary_interval * 60  # Convert to seconds
            
            if time_since_last < min_interval:
                return False
            
            message = self.format_market_summary(market_data)
            success = self.send_message(message, "market_summary", force_send=True)
            
            if success:
                self.last_summary_time = current_time
                
            return success
            
        except Exception as e:
            print(f"❌ Error sending market summary: {e}")
            return False
    
    def format_market_summary(self, data: Dict) -> str:
        """Format market summary for Telegram"""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            message = f"📊 <b>MARKET SUMMARY</b>\n\n"
            message += f"🕒 {timestamp}\n\n"
            
            # Price info
            if 'current_price' in data:
                message += f"💰 BTC: <code>${data['current_price']:,.2f}</code>\n"
            
            # EMA analysis
            if 'ema_analysis' in data:
                ema = data['ema_analysis']
                above = ema.get('above_ema_count', 0)
                total = ema.get('total_timeframes', 4)
                message += f"📈 EMA Position: {above}/{total} timeframes bullish\n"
            
            # Market sentiment
            if 'sentiment' in data:
                message += f"📊 Sentiment: {data['sentiment']}\n"
            
            # Confluence signals
            if 'confluence' in data:
                conf = data['confluence']
                alerts = conf.get('total_alerts', 0)
                if alerts > 0:
                    message += f"🚨 Active Signals: {alerts}\n"
                    
                    critical = conf.get('critical_alerts', 0)
                    if critical > 0:
                        message += f"🔴 Critical: {critical}\n"
            
            message += f"\n📱 <i>Auto-summary from AlertIQ</i>"
            
            return message
            
        except Exception as e:
            print(f"❌ Error formatting market summary: {e}")
            return f"📊 <b>MARKET SUMMARY ERROR</b>\n\n{str(e)}"

class EnhancedAlertMonitor:
    """Enhanced monitor for multiple file types"""
    
    def __init__(self, notifier: EnhancedTelegramNotifier, config: EnhancedTelegramConfig):
        self.notifier = notifier
        self.config = config
        self.monitoring = False
        self.monitor_thread = None
        self.known_alerts = set()
        self.known_confluence = set()
        self.last_check_times = {}
        
    def auto_discover_files(self):
        """Auto-discover AlertIQ files in common locations"""
        discovered = {}
        
        # Common file patterns
        search_patterns = [
            "**/data/btc.json",
            "**/alerts.json", 
            "**/confluence*.json",
            "**/market*.json",
            "**/*alert*.json"
        ]
        
        # Search in current directory and subdirectories
        for pattern in search_patterns:
            for file_path in glob.glob(pattern, recursive=True):
                if os.path.isfile(file_path):
                    # Categorize files
                    filename = os.path.basename(file_path).lower()
                    if 'alert' in filename and 'confluence' not in filename:
                        discovered['alerts'] = file_path
                    elif 'confluence' in filename or 'market' in filename:
                        discovered['confluence'] = file_path
                    elif 'btc.json' in filename:
                        discovered['alerts'] = file_path
        
        return discovered
    
    def start_monitoring(self):
        """Start enhanced monitoring"""
        if self.monitoring:
            return False
            
        # Check if we have files to monitor
        if not self.config.alerts_file and not self.config.confluence_file:
            print("❌ No files configured for monitoring")
            return False
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._enhanced_monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        print(f"🚀 Enhanced monitoring started")
        if self.config.alerts_file:
            print(f"   📂 Alerts: {os.path.basename(self.config.alerts_file)}")
        if self.config.confluence_file:
            print(f"   📊 Confluence: {os.path.basename(self.config.confluence_file)}")
        
        return True
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("🛑 Enhanced monitoring stopped")
    
    def _enhanced_monitor_loop(self):
        """Enhanced monitoring loop for multiple files"""
        while self.monitoring:
            try:
                # Monitor alerts file
                if self.config.alerts_file and os.path.exists(self.config.alerts_file):
                    self._check_alerts_file()
                
                # Monitor confluence file
                if (self.config.monitor_confluence and 
                    self.config.confluence_file and 
                    os.path.exists(self.config.confluence_file)):
                    self._check_confluence_file()
                
                # Send market summaries if enabled
                if self.config.send_market_summaries:
                    self._check_market_summary()
                
                time.sleep(3)  # Check every 3 seconds
                
            except Exception as e:
                print(f"❌ Enhanced monitor error: {e}")
                time.sleep(5)
    
    def _check_alerts_file(self):
        """Check alerts file for changes"""
        try:
            file_path = self.config.alerts_file
            current_modified = os.path.getmtime(file_path)
            last_modified = self.last_check_times.get('alerts', 0)
            
            if current_modified <= last_modified:
                return
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Extract alerts
            alerts = data.get('alerts', []) if isinstance(data, dict) else data
            
            # Check for new alerts
            for alert in alerts:
                if isinstance(alert, dict):
                    alert_key = self._generate_alert_key(alert)
                    if alert_key not in self.known_alerts:
                        self._send_alert_notification(alert)
                        self.known_alerts.add(alert_key)
            
            self.last_check_times['alerts'] = current_modified
            
        except Exception as e:
            print(f"❌ Error checking alerts file: {e}")
    
    def _check_confluence_file(self):
        """Check confluence file for market signals"""
        try:
            file_path = self.config.confluence_file
            current_modified = os.path.getmtime(file_path)
            last_modified = self.last_check_times.get('confluence', 0)
            
            if current_modified <= last_modified:
                return
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Check for confluence signals
            self._process_confluence_data(data)
            
            self.last_check_times['confluence'] = current_modified
            
        except Exception as e:
            print(f"❌ Error checking confluence file: {e}")
    
    def _process_confluence_data(self, data: Dict):
        """Process confluence data for signals"""
        try:
            # Look for alerts/signals in confluence data
            alerts = data.get('alerts', [])
            
            for alert in alerts:
                if isinstance(alert, dict):
                    alert_key = f"confluence_{alert.get('type', 'signal')}_{alert.get('timeframe', '')}"
                    
                    if alert_key not in self.known_confluence:
                        self._send_confluence_notification(alert)
                        self.known_confluence.add(alert_key)
            
            # Check for reversal signals
            if 'reversal_signals' in data:
                for signal in data['reversal_signals']:
                    signal_key = f"reversal_{signal.get('timeframe', '')}_{signal.get('type', '')}"
                    if signal_key not in self.known_confluence:
                        self._send_reversal_notification(signal)
                        self.known_confluence.add(signal_key)
            
        except Exception as e:
            print(f"❌ Error processing confluence data: {e}")
    
    def _check_market_summary(self):
        """Check if it's time to send market summary"""
        try:
            # Collect market data from available files
            market_data = {}
            
            # Get current price and basic info
            if self.config.alerts_file and os.path.exists(self.config.alerts_file):
                with open(self.config.alerts_file, 'r') as f:
                    data = json.load(f)
                    if 'current_price' in data:
                        market_data['current_price'] = data['current_price']
            
            # Get confluence data
            if self.config.confluence_file and os.path.exists(self.config.confluence_file):
                with open(self.config.confluence_file, 'r') as f:
                    conf_data = json.load(f)
                    market_data['confluence'] = {
                        'total_alerts': len(conf_data.get('alerts', [])),
                        'critical_alerts': len([a for a in conf_data.get('alerts', []) 
                                               if a.get('priority') == 'critical'])
                    }
            
            # Send summary if we have data
            if market_data:
                self.notifier.send_market_summary(market_data)
                
        except Exception as e:
            print(f"❌ Error checking market summary: {e}")
    
    def _generate_alert_key(self, alert: Dict) -> str:
        """Generate unique key for alert"""
        try:
            if 'price' in alert:
                label = alert.get('label', '').encode('utf-8').decode('unicode_escape') if alert.get('label') else ''
                price = alert.get('price', 0)
                created = alert.get('created', '')
                return f"price_{label}_{price}_{created}"
            else:
                label = alert.get('label', 'unknown')
                timestamp = alert.get('created', int(time.time()))
                return f"alert_{label}_{timestamp}"
        except:
            return f"alert_error_{int(time.time())}"
    
    def _send_alert_notification(self, alert: Dict):
        """Send alert notification"""
        try:
            def clean_text(text):
                if isinstance(text, str):
                    try:
                        return text.encode('utf-8').decode('unicode_escape')
                    except:
                        return text
                return str(text) if text else ""
            
            if 'price' in alert:
                label = clean_text(alert.get('label', 'Price Alert'))
                importance = clean_text(alert.get('importance', ''))
                price = alert.get('price', 0)
                notes = clean_text(alert.get('notes', ''))
                
                message = f"🚨 <b>PRICE ALERT</b>\n\n"
                message += f"📊 <b>{label}</b>\n"
                if importance:
                    message += f"⚠️ {importance}\n"
                message += f"💰 Target: <code>${price:,.2f}</code>\n"
                if notes:
                    message += f"📝 {notes}\n"
                message += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                
                alert_key = self._generate_alert_key(alert)
                success = self.notifier.send_message(message, alert_key)
                
                if success:
                    print(f"📱 Sent price alert: {label}")
                    
        except Exception as e:
            print(f"❌ Error sending alert notification: {e}")
    
    def _send_confluence_notification(self, alert: Dict):
        """Send confluence signal notification"""
        try:
            message = f"🎯 <b>CONFLUENCE SIGNAL</b>\n\n"
            message += f"📊 Type: <b>{alert.get('type', 'Unknown')}</b>\n"
            
            if 'timeframe' in alert:
                message += f"⏱️ Timeframe: <code>{alert['timeframe'].upper()}</code>\n"
            
            if 'priority' in alert:
                priority_icons = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '⚪'}
                icon = priority_icons.get(alert.get('priority'), '🔵')
                message += f"📈 Priority: {icon} {alert['priority'].upper()}\n"
            
            if 'details' in alert:
                message += f"📝 {alert['details']}\n"
            
            message += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            
            alert_key = f"confluence_{alert.get('type')}_{alert.get('timeframe')}"
            success = self.notifier.send_message(message, alert_key)
            
            if success:
                print(f"📱 Sent confluence signal: {alert.get('type')}")
                
        except Exception as e:
            print(f"❌ Error sending confluence notification: {e}")
    
    def _send_reversal_notification(self, signal: Dict):
        """Send reversal signal notification"""
        try:
            message = f"🔄 <b>REVERSAL SIGNAL</b>\n\n"
            message += f"⏱️ Timeframe: <code>{signal.get('timeframe', 'Unknown').upper()}</code>\n"
            message += f"📊 Type: <b>{signal.get('type', 'Unknown reversal')}</b>\n"
            
            if 'strength' in signal:
                message += f"💪 Strength: {signal['strength']}\n"
            
            if 'confidence' in signal:
                message += f"🎯 Confidence: {signal['confidence']}%\n"
            
            message += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            
            signal_key = f"reversal_{signal.get('timeframe')}_{signal.get('type')}"
            success = self.notifier.send_message(message, signal_key, force_send=True)
            
            if success:
                print(f"📱 Sent reversal signal: {signal.get('timeframe')} {signal.get('type')}")
                
        except Exception as e:
            print(f"❌ Error sending reversal notification: {e}")

class EnhancedTelegramPusherGUI:
    """Enhanced GUI with auto-start and multi-file monitoring"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("📱 AlertIQ Enhanced Telegram Pusher v2.0")
        self.root.geometry("900x800")
        self.root.configure(bg="#1e1e1e")
        
        # Initialize components
        self.config = EnhancedTelegramConfig()
        self.notifier = EnhancedTelegramNotifier(self.config)
        self.monitor = EnhancedAlertMonitor(self.notifier, self.config)
        
        # GUI state
        self.monitoring_var = tk.BooleanVar()
        self.auto_start_var = tk.BooleanVar(value=self.config.auto_start)
        self.monitor_confluence_var = tk.BooleanVar(value=self.config.monitor_confluence)
        self.send_summaries_var = tk.BooleanVar(value=self.config.send_market_summaries)
        
        # Colors
        self.colors = {
            "bg_dark": "#1e1e1e",
            "bg_medium": "#2d2d2d", 
            "bg_light": "#3d3d3d",
            "text_primary": "#ffffff",
            "text_secondary": "#cccccc",
            "accent": "#00d4aa",
            "success": "#4caf50",
            "warning": "#ff9800",
            "error": "#f44336"
        }
        
        self.setup_gui()
        
        # Auto-start if configured
        if self.config.can_auto_start():
            self.root.after(1000, self.auto_start_monitoring)
    
    def setup_gui(self):
        """Setup enhanced GUI"""
        # Main container with scrollbar
        canvas = tk.Canvas(self.root, bg=self.colors["bg_dark"])
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors["bg_dark"])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        main_frame = scrollable_frame
        
        # Header
        self.create_header(main_frame)
        
        # Telegram config
        self.create_telegram_config(main_frame)
        
        # File monitoring config
        self.create_file_config(main_frame)
        
        # Advanced settings
        self.create_advanced_settings(main_frame)
        
        # Control panel
        self.create_control_panel(main_frame)
        
        # Status and logs
        self.create_status_section(main_frame)
        
        # Update display
        self.update_status_display()
    
    def create_header(self, parent):
        """Create header section"""
        header_frame = tk.Frame(parent, bg=self.colors["bg_medium"], relief="ridge", bd=2)
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        title_label = tk.Label(
            header_frame,
            text="📱 AlertIQ Enhanced Telegram Pusher v2.0",
            font=("Arial", 16, "bold"),
            bg=self.colors["bg_medium"],
            fg=self.colors["accent"]
        )
        title_label.pack(pady=8)
        
        subtitle_label = tk.Label(
            header_frame,
            text="Auto-start monitoring • Multiple files • Market summaries • Confluence signals",
            font=("Arial", 9),
            bg=self.colors["bg_medium"],
            fg=self.colors["text_secondary"]
        )
        subtitle_label.pack(pady=(0, 8))
    
    def create_telegram_config(self, parent):
        """Create Telegram configuration section"""
        config_frame = tk.LabelFrame(
            parent,
            text=" 🔧 Telegram Configuration ",
            font=("Arial", 11, "bold"),
            bg=self.colors["bg_medium"],
            fg=self.colors["text_primary"],
            relief="ridge",
            bd=2
        )
        config_frame.pack(fill="x", padx=10, pady=5)
        
        # Bot Token
        tk.Label(config_frame, text="Bot Token:", bg=self.colors["bg_medium"], 
                fg=self.colors["text_primary"], font=("Arial", 9)).grid(row=0, column=0, sticky="w", padx=10, pady=3)
        
        self.token_entry = tk.Entry(config_frame, font=("Arial", 9), width=60, show="*")
        self.token_entry.grid(row=0, column=1, padx=10, pady=3, sticky="ew")
        self.token_entry.insert(0, self.config.bot_token)
        
        # Chat ID
        tk.Label(config_frame, text="Chat ID:", bg=self.colors["bg_medium"], 
                fg=self.colors["text_primary"], font=("Arial", 9)).grid(row=1, column=0, sticky="w", padx=10, pady=3)
        
        self.chat_id_entry = tk.Entry(config_frame, font=("Arial", 9), width=60)
        self.chat_id_entry.grid(row=1, column=1, padx=10, pady=3, sticky="ew")
        self.chat_id_entry.insert(0, self.config.chat_id)
        
        # Buttons
        button_frame = tk.Frame(config_frame, bg=self.colors["bg_medium"])
        button_frame.grid(row=2, column=0, columnspan=2, pady=8)
        
        save_btn = tk.Button(
            button_frame, text="💾 Save", command=self.save_config,
            bg=self.colors["accent"], fg="white", font=("Arial", 9), relief="flat", padx=12
        )
        save_btn.pack(side="left", padx=3)
        
        test_btn = tk.Button(
            button_frame, text="🧪 Test", command=self.test_telegram,
            bg=self.colors["warning"], fg="white", font=("Arial", 9), relief="flat", padx=12
        )
        test_btn.pack(side="left", padx=3)
        
        config_frame.columnconfigure(1, weight=1)
    
    def create_file_config(self, parent):
        """Create file monitoring configuration"""
        file_frame = tk.LabelFrame(
            parent,
            text=" 📂 File Monitoring ",
            font=("Arial", 11, "bold"),
            bg=self.colors["bg_medium"],
            fg=self.colors["text_primary"],
            relief="ridge",
            bd=2
        )
        file_frame.pack(fill="x", padx=10, pady=5)
        
        # Auto-discover button
        discover_btn = tk.Button(
            file_frame, text="🔍 Auto-Discover Files", command=self.auto_discover_files,
            bg=self.colors["accent"], fg="white", font=("Arial", 9), relief="flat"
        )
        discover_btn.pack(pady=5)
        
        # Alerts file
        alerts_frame = tk.Frame(file_frame, bg=self.colors["bg_medium"])
        alerts_frame.pack(fill="x", padx=10, pady=3)
        
        tk.Label(alerts_frame, text="Alerts File:", bg=self.colors["bg_medium"], 
                fg=self.colors["text_primary"], font=("Arial", 9), width=12, anchor="w").pack(side="left")
        
        self.alerts_file_var = tk.StringVar(value=self.config.alerts_file)
        alerts_entry = tk.Entry(alerts_frame, textvariable=self.alerts_file_var, font=("Arial", 9), state="readonly")
        alerts_entry.pack(side="left", fill="x", expand=True, padx=(5, 3))
        
        alerts_browse_btn = tk.Button(
            alerts_frame, text="📁", command=lambda: self.browse_file('alerts'),
            bg=self.colors["accent"], fg="white", font=("Arial", 8), relief="flat"
        )
        alerts_browse_btn.pack(side="right")
        
        # Confluence file
        confluence_frame = tk.Frame(file_frame, bg=self.colors["bg_medium"])
        confluence_frame.pack(fill="x", padx=10, pady=3)
        
        tk.Label(confluence_frame, text="Confluence File:", bg=self.colors["bg_medium"], 
                fg=self.colors["text_primary"], font=("Arial", 9), width=12, anchor="w").pack(side="left")
        
        self.confluence_file_var = tk.StringVar(value=self.config.confluence_file)
        confluence_entry = tk.Entry(confluence_frame, textvariable=self.confluence_file_var, font=("Arial", 9), state="readonly")
        confluence_entry.pack(side="left", fill="x", expand=True, padx=(5, 3))
        
        confluence_browse_btn = tk.Button(
            confluence_frame, text="📁", command=lambda: self.browse_file('confluence'),
            bg=self.colors["accent"], fg="white", font=("Arial", 8), relief="flat"
        )
        confluence_browse_btn.pack(side="right")
    
    def create_advanced_settings(self, parent):
        """Create advanced settings section"""
        settings_frame = tk.LabelFrame(
            parent,
            text=" ⚙️ Advanced Settings ",
            font=("Arial", 11, "bold"),
            bg=self.colors["bg_medium"],
            fg=self.colors["text_primary"],
            relief="ridge",
            bd=2
        )
        settings_frame.pack(fill="x", padx=10, pady=5)
        
        # Auto-start checkbox
        auto_start_check = tk.Checkbutton(
            settings_frame,
            text="🚀 Auto-start monitoring on app launch",
            variable=self.auto_start_var,
            bg=self.colors["bg_medium"],
            fg=self.colors["text_primary"],
            selectcolor=self.colors["bg_dark"],
            font=("Arial", 9),
            command=self.update_auto_start
        )
        auto_start_check.pack(anchor="w", padx=10, pady=3)
        
        # Monitor confluence checkbox
        confluence_check = tk.Checkbutton(
            settings_frame,
            text="📊 Monitor confluence signals and reversals",
            variable=self.monitor_confluence_var,
            bg=self.colors["bg_medium"],
            fg=self.colors["text_primary"],
            selectcolor=self.colors["bg_dark"],
            font=("Arial", 9),
            command=self.update_confluence_monitoring
        )
        confluence_check.pack(anchor="w", padx=10, pady=3)
        
        # Market summaries checkbox
        summaries_check = tk.Checkbutton(
            settings_frame,
            text="📈 Send periodic market summaries",
            variable=self.send_summaries_var,
            bg=self.colors["bg_medium"],
            fg=self.colors["text_primary"],
            selectcolor=self.colors["bg_dark"],
            font=("Arial", 9),
            command=self.update_summaries
        )
        summaries_check.pack(anchor="w", padx=10, pady=3)
        
        # Summary interval
        interval_frame = tk.Frame(settings_frame, bg=self.colors["bg_medium"])
        interval_frame.pack(anchor="w", padx=30, pady=3)
        
        tk.Label(interval_frame, text="Summary interval:", bg=self.colors["bg_medium"], 
                fg=self.colors["text_secondary"], font=("Arial", 9)).pack(side="left")
        
        self.interval_var = tk.StringVar(value=str(self.config.summary_interval))
        interval_entry = tk.Entry(interval_frame, textvariable=self.interval_var, font=("Arial", 9), width=5)
        interval_entry.pack(side="left", padx=5)
        
        tk.Label(interval_frame, text="minutes", bg=self.colors["bg_medium"], 
                fg=self.colors["text_secondary"], font=("Arial", 9)).pack(side="left")
    
    def create_control_panel(self, parent):
        """Create monitoring control panel"""
        control_frame = tk.LabelFrame(
            parent,
            text=" 🎮 Control Panel ",
            font=("Arial", 11, "bold"),
            bg=self.colors["bg_medium"],
            fg=self.colors["text_primary"],
            relief="ridge",
            bd=2
        )
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # Status display
        status_frame = tk.Frame(control_frame, bg=self.colors["bg_medium"])
        status_frame.pack(fill="x", padx=10, pady=5)
        
        self.status_label = tk.Label(
            status_frame,
            text="❌ Not Configured",
            bg=self.colors["bg_medium"],
            fg=self.colors["error"],
            font=("Arial", 12, "bold")
        )
        self.status_label.pack()
        
        # Control buttons
        button_frame = tk.Frame(control_frame, bg=self.colors["bg_medium"])
        button_frame.pack(pady=8)
        
        self.start_btn = tk.Button(
            button_frame,
            text="🚀 Start Enhanced Monitoring",
            command=self.toggle_monitoring,
            bg=self.colors["success"],
            fg="white",
            font=("Arial", 11, "bold"),
            relief="flat",
            padx=20,
            pady=5
        )
        self.start_btn.pack(side="left", padx=5)
        
        summary_btn = tk.Button(
            button_frame,
            text="📊 Send Summary Now",
            command=self.send_summary_now,
            bg=self.colors["warning"],
            fg="white",
            font=("Arial", 10),
            relief="flat",
            padx=15
        )
        summary_btn.pack(side="left", padx=5)
        
        # Statistics
        stats_frame = tk.Frame(control_frame, bg=self.colors["bg_medium"])
        stats_frame.pack(fill="x", padx=10, pady=5)
        
        self.stats_vars = {
            "alerts_sent": tk.StringVar(value="Alerts: 0"),
            "confluence_sent": tk.StringVar(value="Confluence: 0"),
            "summaries_sent": tk.StringVar(value="Summaries: 0"),
            "last_activity": tk.StringVar(value="Last Activity: Never")
        }
        
        for i, (key, var) in enumerate(self.stats_vars.items()):
            label = tk.Label(stats_frame, textvariable=var, bg=self.colors["bg_medium"], 
                           fg=self.colors["text_secondary"], font=("Arial", 8))
            label.grid(row=i//2, column=i%2, padx=10, sticky="w")
    
    def create_status_section(self, parent):
        """Create status and logs section"""
        status_frame = tk.LabelFrame(
            parent,
            text=" 📊 Activity Logs ",
            font=("Arial", 11, "bold"),
            bg=self.colors["bg_medium"],
            fg=self.colors["text_primary"],
            relief="ridge",
            bd=2
        )
        status_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Log display
        self.log_text = scrolledtext.ScrolledText(
            status_frame,
            height=20,
            bg=self.colors["bg_dark"],
            fg=self.colors["text_primary"],
            font=("Consolas", 8),
            wrap="word"
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(5, 5))
        
        # Log control buttons
        log_btn_frame = tk.Frame(status_frame, bg=self.colors["bg_medium"])
        log_btn_frame.pack(pady=(0, 10))
        
        clear_btn = tk.Button(
            log_btn_frame,
            text="🧹 Clear Logs",
            command=self.clear_logs,
            bg=self.colors["warning"],
            fg="white",
            font=("Arial", 9),
            relief="flat"
        )
        clear_btn.pack(side="left", padx=5)
        
        export_btn = tk.Button(
            log_btn_frame,
            text="💾 Export Logs",
            command=self.export_logs,
            bg=self.colors["accent"],
            fg="white",
            font=("Arial", 9),
            relief="flat"
        )
        export_btn.pack(side="left", padx=5)
    
    def auto_discover_files(self):
        """Auto-discover AlertIQ files"""
        self.log_message("🔍 Auto-discovering AlertIQ files...")
        
        discovered = self.monitor.auto_discover_files()
        
        if discovered:
            self.log_message(f"✅ Found {len(discovered)} file(s):")
            
            if 'alerts' in discovered:
                self.config.alerts_file = discovered['alerts']
                self.alerts_file_var.set(discovered['alerts'])
                self.log_message(f"   📂 Alerts: {os.path.basename(discovered['alerts'])}")
            
            if 'confluence' in discovered:
                self.config.confluence_file = discovered['confluence']
                self.confluence_file_var.set(discovered['confluence'])
                self.log_message(f"   📊 Confluence: {os.path.basename(discovered['confluence'])}")
            
            self.save_config()
            messagebox.showinfo("Discovery Complete", f"Found and configured {len(discovered)} file(s)!")
        else:
            self.log_message("❌ No AlertIQ files found")
            messagebox.showwarning("No Files Found", "Could not find AlertIQ files. Please browse manually.")
    
    def browse_file(self, file_type):
        """Browse for specific file type"""
        title = f"Select AlertIQ {file_type.title()} File"
        file_path = filedialog.askopenfilename(
            title=title,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            if file_type == 'alerts':
                self.config.alerts_file = file_path
                self.alerts_file_var.set(file_path)
            elif file_type == 'confluence':
                self.config.confluence_file = file_path
                self.confluence_file_var.set(file_path)
            
            self.log_message(f"📂 Selected {file_type} file: {os.path.basename(file_path)}")
            self.save_config()
    
    def save_config(self):
        """Save configuration"""
        # Update config from GUI
        self.config.bot_token = self.token_entry.get().strip()
        self.config.chat_id = self.chat_id_entry.get().strip()
        self.config.auto_start = self.auto_start_var.get()
        self.config.monitor_confluence = self.monitor_confluence_var.get()
        self.config.send_market_summaries = self.send_summaries_var.get()
        
        try:
            self.config.summary_interval = int(self.interval_var.get())
        except:
            self.config.summary_interval = 30
        
        if self.config.save_config():
            self.log_message("✅ Configuration saved")
            self.update_status_display()
            messagebox.showinfo("Success", "Configuration saved successfully!")
        else:
            self.log_message("❌ Failed to save configuration")
            messagebox.showerror("Error", "Failed to save configuration")
    
    def test_telegram(self):
        """Test Telegram connection"""
        # Update config from GUI
        self.config.bot_token = self.token_entry.get().strip()
        self.config.chat_id = self.chat_id_entry.get().strip()
        
        if not self.config.is_configured():
            messagebox.showwarning("Configuration", "Please enter Bot Token and Chat ID first")
            return
        
        self.log_message("🧪 Testing Telegram connection...")
        
        test_message = f"🤖 <b>AlertIQ Enhanced Test</b>\n\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n✅ Enhanced pusher ready!"
        
        if self.notifier.send_message(test_message, "test_enhanced"):
            self.log_message("✅ Telegram test successful!")
            messagebox.showinfo("Success", "Telegram connection test successful!")
            self.update_status_display()
        else:
            self.log_message("❌ Telegram test failed")
            messagebox.showerror("Error", "Telegram connection test failed. Check your configuration.")
    
    def toggle_monitoring(self):
        """Toggle enhanced monitoring"""
        if not self.monitoring_var.get():
            # Start monitoring
            if not self.config.is_configured():
                messagebox.showwarning("Configuration", "Please configure Telegram settings first")
                return
            
            if not self.config.alerts_file and not self.config.confluence_file:
                messagebox.showwarning("Files", "Please select at least one file to monitor")
                return
            
            if self.monitor.start_monitoring():
                self.monitoring_var.set(True)
                self.start_btn.config(text="🛑 Stop Monitoring", bg=self.colors["error"])
                self.log_message("🚀 Enhanced monitoring started")
            else:
                messagebox.showerror("Error", "Failed to start monitoring")
        else:
            # Stop monitoring
            self.monitor.stop_monitoring()
            self.monitoring_var.set(False)
            self.start_btn.config(text="🚀 Start Enhanced Monitoring", bg=self.colors["success"])
            self.log_message("🛑 Enhanced monitoring stopped")
        
        self.update_status_display()
    
    def send_summary_now(self):
        """Send market summary immediately"""
        self.log_message("📊 Sending market summary...")
        
        # Force a market summary check
        self.monitor._check_market_summary()
        
    def auto_start_monitoring(self):
        """Auto-start monitoring if configured"""
        if self.config.can_auto_start():
            self.log_message("🚀 Auto-starting monitoring...")
            self.toggle_monitoring()
    
    def update_auto_start(self):
        """Update auto-start setting"""
        self.config.auto_start = self.auto_start_var.get()
        self.save_config()
    
    def update_confluence_monitoring(self):
        """Update confluence monitoring setting"""
        self.config.monitor_confluence = self.monitor_confluence_var.get()
        self.save_config()
    
    def update_summaries(self):
        """Update summaries setting"""
        self.config.send_market_summaries = self.send_summaries_var.get()
        self.save_config()
    
    def update_status_display(self):
        """Update status display"""
        if self.config.is_configured():
            if self.monitoring_var.get():
                self.status_label.config(text="🟢 Enhanced Monitoring Active", fg=self.colors["success"])
            else:
                self.status_label.config(text="🟡 Ready for Enhanced Monitoring", fg=self.colors["warning"])
        else:
            self.status_label.config(text="❌ Not Configured", fg=self.colors["error"])
        
        # Update stats
        if hasattr(self, 'stats_vars'):
            alerts_count = len([k for k in self.notifier.last_sent.keys() if k.startswith('price_')])
            confluence_count = len([k for k in self.notifier.last_sent.keys() if k.startswith('confluence_')])
            summary_count = len([k for k in self.notifier.last_sent.keys() if k.startswith('market_summary')])
            
            self.stats_vars["alerts_sent"].set(f"Alerts: {alerts_count}")
            self.stats_vars["confluence_sent"].set(f"Confluence: {confluence_count}")
            self.stats_vars["summaries_sent"].set(f"Summaries: {summary_count}")
            self.stats_vars["last_activity"].set(f"Last Activity: {datetime.now().strftime('%H:%M:%S')}")
    
    def log_message(self, message: str):
        """Add message to logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}\n"
        
        if hasattr(self, 'log_text'):
            self.log_text.insert(tk.END, formatted_msg)
            self.log_text.see(tk.END)
            
            # Keep only last 200 lines
            lines = self.log_text.get("1.0", tk.END).split('\n')
            if len(lines) > 200:
                self.log_text.delete("1.0", f"{len(lines)-200}.0")
        
        print(formatted_msg.strip())  # Also print to console
    
    def clear_logs(self):
        """Clear logs"""
        if hasattr(self, 'log_text'):
            self.log_text.delete("1.0", tk.END)
        self.log_message("🧹 Logs cleared")
    
    def export_logs(self):
        """Export logs to file"""
        try:
            if hasattr(self, 'log_text'):
                logs = self.log_text.get("1.0", tk.END)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"telegram_pusher_logs_{timestamp}.txt"
                
                with open(filename, 'w') as f:
                    f.write(logs)
                
                self.log_message(f"💾 Logs exported to {filename}")
                messagebox.showinfo("Export Complete", f"Logs exported to {filename}")
        except Exception as e:
            self.log_message(f"❌ Export failed: {e}")
            messagebox.showerror("Export Failed", f"Failed to export logs: {e}")
    
    def on_closing(self):
        """Handle application closing"""
        if self.monitoring_var.get():
            self.monitor.stop_monitoring()
        self.root.destroy()
    
    def run(self):
        """Run the enhanced application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Initial log
        self.log_message("🚀 AlertIQ Enhanced Telegram Pusher v2.0 started")
        
        if self.config.can_auto_start():
            self.log_message("⚡ Auto-start enabled - monitoring will begin automatically")
        else:
            self.log_message("ℹ️ Configure settings and files to enable auto-start")
        
        # Status update loop
        def status_loop():
            self.update_status_display()
            self.root.after(10000, status_loop)  # Update every 10 seconds
        
        status_loop()
        self.root.mainloop()

if __name__ == "__main__":
    app = EnhancedTelegramPusherGUI()
    app.run()