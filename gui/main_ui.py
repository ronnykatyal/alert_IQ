# gui/main_ui.py - Professional Alert_IQ GUI (Fixed Version)

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import threading
import time
from datetime import datetime, timezone, timedelta
from plyer import notification

# Import all your engines
from tools.fetcher import get_btc_price
from tools.ema_engine_production import ProductionEMAEngine
from tools.volume_oi_engine import VolumeOIEngine
from tools.confluence_alert_engine import ConfluenceAlertEngine

# Data file path
DATA_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "btc.json"))

def load_alerts():
    try:
        if not os.path.exists(DATA_FILE):
            os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
            with open(DATA_FILE, "w") as f:
                json.dump({"alerts": []}, f, indent=2)
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            return data.get("alerts", [])
    except Exception as e:
        print(f"Error loading alerts: {e}")
        return []

def save_alerts(alerts):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump({"alerts": alerts}, f, indent=2)
    except Exception as e:
        print(f"Error saving alerts: {e}")

class ProfessionalAlertIQ:
    def __init__(self, root):
        self.root = root
        self.root.title("📊 Alert_IQ - Professional Crypto Trading Dashboard")
        self.root.geometry("1400x900")
        self.root.configure(bg="#1a1a1a")  # Dark theme
        
        print("🎯 Initializing Alert_IQ...")
        
        # Initialize engines with error handling
        try:
            self.ema_engine = ProductionEMAEngine()
            self.volume_engine = VolumeOIEngine()
            self.confluence_engine = ConfluenceAlertEngine()
            print("✅ All engines initialized successfully")
        except Exception as e:
            print(f"❌ Engine initialization failed: {e}")
            messagebox.showerror("Engine Error", f"Failed to initialize engines:\n{str(e)}")
            raise
        
        # Data storage
        self.alerts = load_alerts()
        self.ema_data = {}
        self.volume_data = {}
        self.confluence_results = {}
        self.current_price = 0
        
        # Alert options
        self.label_options = [
            "🟢 Support", "🔴 Resistance", "🟡 Watch", "🔵 Breakout",
            "🟣 Custom", "⚪ Retest", "🟤 Demand", "⚫ Supply"
        ]
        self.ema_alert_types = [
            "Cross Above EMA", "Cross Below EMA", "Distance Above EMA", "Distance Below EMA"
        ]
        self.timeframe_options = ["15m", "1h", "4h", "1d"]
        
        # Colors for dark theme
        self.colors = {
            "bg_dark": "#1a1a1a",
            "bg_medium": "#2d2d2d", 
            "bg_light": "#3d3d3d",
            "text_primary": "#ffffff",
            "text_secondary": "#b0b0b0",
            "green": "#00ff88",
            "red": "#ff4757",
            "blue": "#3742fa",
            "yellow": "#ffa502",
            "purple": "#9c88ff"
        }
        
        # GUI state
        self.gui_active = True
        
        print("🎨 Creating UI components...")
        self.create_professional_ui()
        
        print("🔄 Starting data updates...")
        self.start_data_updates()
        
        print("✅ Alert_IQ ready!")
    
    def create_professional_ui(self):
        """Create professional trading dashboard UI"""
        try:
            # Main container with padding
            main_container = tk.Frame(self.root, bg=self.colors["bg_dark"])
            main_container.pack(fill="both", expand=True, padx=15, pady=15)
            
            # Top header with price and status
            self.create_header(main_container)
            
            # Main content area with three columns
            content_frame = tk.Frame(main_container, bg=self.colors["bg_dark"])
            content_frame.pack(fill="both", expand=True, pady=(15, 0))
            
            # Left column - Market Analysis
            left_frame = tk.Frame(content_frame, bg=self.colors["bg_dark"])
            left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
            
            # Middle column - Alerts Management  
            middle_frame = tk.Frame(content_frame, bg=self.colors["bg_dark"])
            middle_frame.pack(side="left", fill="both", expand=True, padx=5)
            
            # Right column - Live Alerts & Activity
            right_frame = tk.Frame(content_frame, bg=self.colors["bg_dark"])
            right_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))
            
            # Create sections
            self.create_market_analysis_section(left_frame)
            self.create_alerts_management_section(middle_frame)
            self.create_live_activity_section(right_frame)
            
            print("✅ UI created successfully")
            
        except Exception as e:
            print(f"❌ UI creation error: {e}")
            raise
    
    def create_header(self, parent):
        """Create header with price and overall market status"""
        header_frame = tk.Frame(parent, bg=self.colors["bg_medium"], relief="raised", bd=2)
        header_frame.pack(fill="x", pady=(0, 15))
        
        # Price display
        price_frame = tk.Frame(header_frame, bg=self.colors["bg_medium"])
        price_frame.pack(side="left", padx=20, pady=15)
        
        tk.Label(price_frame, text="BTC/USDT", font=("Segoe UI", 12), 
                bg=self.colors["bg_medium"], fg=self.colors["text_secondary"]).pack()
        
        self.price_label = tk.Label(price_frame, text="$--,---", font=("Segoe UI", 24, "bold"), 
                                   bg=self.colors["bg_medium"], fg=self.colors["green"])
        self.price_label.pack()
        
        # Market sentiment
        sentiment_frame = tk.Frame(header_frame, bg=self.colors["bg_medium"])
        sentiment_frame.pack(side="right", padx=20, pady=15)
        
        tk.Label(sentiment_frame, text="Market Sentiment", font=("Segoe UI", 12), 
                bg=self.colors["bg_medium"], fg=self.colors["text_secondary"]).pack()
        
        self.sentiment_label = tk.Label(sentiment_frame, text="ANALYZING...", font=("Segoe UI", 16, "bold"), 
                                       bg=self.colors["bg_medium"], fg=self.colors["yellow"])
        self.sentiment_label.pack()
        
        # Status indicators
        status_frame = tk.Frame(header_frame, bg=self.colors["bg_medium"])
        status_frame.pack(expand=True, padx=20, pady=15)
        
        self.status_labels = {}
        status_items = ["EMA", "Volume", "OI", "Confluence"]
        
        for i, item in enumerate(status_items):
            item_frame = tk.Frame(status_frame, bg=self.colors["bg_medium"])
            item_frame.grid(row=0, column=i, padx=10)
            
            tk.Label(item_frame, text=item, font=("Segoe UI", 10), 
                    bg=self.colors["bg_medium"], fg=self.colors["text_secondary"]).pack()
            
            status_label = tk.Label(item_frame, text="●", font=("Segoe UI", 14), 
                                   bg=self.colors["bg_medium"], fg=self.colors["yellow"])
            status_label.pack()
            self.status_labels[item.lower()] = status_label
    
    def create_market_analysis_section(self, parent):
        """Create comprehensive market analysis display"""
        
        # EMA Analysis Panel
        ema_panel = self.create_panel(parent, "📈 EMA Analysis", height=200)
        
        # EMA timeframe display
        self.ema_labels = {}
        for i, tf in enumerate(["15m", "1h", "4h", "1d"]):
            row_frame = tk.Frame(ema_panel, bg=self.colors["bg_light"])
            row_frame.pack(fill="x", padx=10, pady=2)
            
            # Timeframe
            tk.Label(row_frame, text=f"{tf.upper()}:", font=("Segoe UI", 11, "bold"), 
                    bg=self.colors["bg_light"], fg=self.colors["text_primary"], width=6, anchor="w").pack(side="left")
            
            # Status
            status_label = tk.Label(row_frame, text="Loading...", font=("Segoe UI", 11), 
                                   bg=self.colors["bg_light"], fg=self.colors["text_secondary"], anchor="w")
            status_label.pack(side="left", fill="x", expand=True)
            
            self.ema_labels[tf] = status_label
        
        # Volume & OI Analysis Panel
        volume_panel = self.create_panel(parent, "📊 Volume & Open Interest", height=250)
        
        # Volume display
        vol_header = tk.Label(volume_panel, text="Volume Analysis", font=("Segoe UI", 12, "bold"), 
                             bg=self.colors["bg_light"], fg=self.colors["blue"])
        vol_header.pack(pady=(5, 10))
        
        self.volume_labels = {}
        for tf in ["15m", "1h", "4h", "1d"]:
            row_frame = tk.Frame(volume_panel, bg=self.colors["bg_light"])
            row_frame.pack(fill="x", padx=10, pady=1)
            
            tf_label = tk.Label(row_frame, text=f"{tf.upper()}:", font=("Segoe UI", 10, "bold"), 
                               bg=self.colors["bg_light"], fg=self.colors["text_primary"], width=6, anchor="w")
            tf_label.pack(side="left")
            
            vol_label = tk.Label(row_frame, text="Loading...", font=("Segoe UI", 10), 
                                bg=self.colors["bg_light"], fg=self.colors["text_secondary"], anchor="w")
            vol_label.pack(side="left", fill="x", expand=True)
            
            self.volume_labels[tf] = vol_label
        
        # OI header
        oi_header = tk.Label(volume_panel, text="Open Interest Analysis", font=("Segoe UI", 12, "bold"), 
                            bg=self.colors["bg_light"], fg=self.colors["purple"])
        oi_header.pack(pady=(15, 5))
        
        self.oi_summary_label = tk.Label(volume_panel, text="Analyzing OI changes...", 
                                        font=("Segoe UI", 10), bg=self.colors["bg_light"], 
                                        fg=self.colors["text_secondary"], wraplength=300, justify="left")
        self.oi_summary_label.pack(padx=10, pady=5)
        
        # Confluence Analysis Panel
        confluence_panel = self.create_panel(parent, "🎯 Smart Confluence Analysis", height=200)
        
        self.confluence_summary = scrolledtext.ScrolledText(
            confluence_panel, height=8, font=("Consolas", 9),
            bg=self.colors["bg_dark"], fg=self.colors["text_primary"],
            insertbackground=self.colors["text_primary"], wrap=tk.WORD
        )
        self.confluence_summary.pack(fill="both", expand=True, padx=10, pady=10)
    
    def create_alerts_management_section(self, parent):
        """Create alerts management interface"""
        
        # Alert Creation Panel
        create_panel = self.create_panel(parent, "🔔 Create New Alert", height=300)
        
        # Tab selection for alert types
        tab_frame = tk.Frame(create_panel, bg=self.colors["bg_light"])
        tab_frame.pack(fill="x", padx=10, pady=5)
        
        self.alert_type = tk.StringVar(value="price")
        
        # Tab buttons
        price_btn = tk.Radiobutton(tab_frame, text="💰 Price Alert", variable=self.alert_type, 
                                  value="price", command=self.switch_alert_type,
                                  font=("Segoe UI", 10, "bold"), bg=self.colors["bg_medium"], 
                                  fg=self.colors["text_primary"], selectcolor=self.colors["bg_dark"],
                                  activebackground=self.colors["bg_medium"])
        price_btn.pack(side="left", padx=5)
        
        ema_btn = tk.Radiobutton(tab_frame, text="📈 EMA Alert", variable=self.alert_type, 
                                value="ema", command=self.switch_alert_type,
                                font=("Segoe UI", 10, "bold"), bg=self.colors["bg_medium"], 
                                fg=self.colors["text_primary"], selectcolor=self.colors["bg_dark"],
                                activebackground=self.colors["bg_medium"])
        ema_btn.pack(side="left", padx=5)
        
        # Price Alert Frame
        self.price_alert_frame = tk.Frame(create_panel, bg=self.colors["bg_light"])
        self.create_price_alert_inputs(self.price_alert_frame)
        self.price_alert_frame.pack(fill="x", padx=10, pady=10)
        
        # EMA Alert Frame (hidden initially)
        self.ema_alert_frame = tk.Frame(create_panel, bg=self.colors["bg_light"])
        self.create_ema_alert_inputs(self.ema_alert_frame)
        
        # Add Alert Button
        add_btn = tk.Button(create_panel, text="➕ Add Alert", command=self.add_alert,
                           font=("Segoe UI", 12, "bold"), bg=self.colors["green"], 
                           fg="white", relief="flat", pady=8)
        add_btn.pack(pady=10)
        
        # Active Alerts Panel
        active_panel = self.create_panel(parent, "📋 Active Alerts", height=300)
        
        # Alerts listbox with scrollbar
        list_frame = tk.Frame(active_panel, bg=self.colors["bg_light"])
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame, bg=self.colors["bg_medium"])
        scrollbar.pack(side="right", fill="y")
        
        self.alerts_listbox = tk.Listbox(list_frame, font=("Segoe UI", 9), 
                                        bg=self.colors["bg_dark"], fg=self.colors["text_primary"],
                                        selectbackground=self.colors["blue"], yscrollcommand=scrollbar.set)
        self.alerts_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.alerts_listbox.yview)
        
        # Alert management buttons
        btn_frame = tk.Frame(active_panel, bg=self.colors["bg_light"])
        btn_frame.pack(fill="x", padx=10, pady=5)
        
        delete_btn = tk.Button(btn_frame, text="🗑️ Delete Selected", command=self.delete_selected_alert,
                              font=("Segoe UI", 9), bg=self.colors["red"], fg="white", relief="flat")
        delete_btn.pack(side="left", padx=5)
        
        clear_btn = tk.Button(btn_frame, text="🧹 Clear All", command=self.clear_all_alerts,
                             font=("Segoe UI", 9), bg=self.colors["yellow"], fg="black", relief="flat")
        clear_btn.pack(side="left", padx=5)
    
    def create_live_activity_section(self, parent):
        """Create live alerts and activity monitoring"""
        
        # Live Alerts Panel
        live_panel = self.create_panel(parent, "🚨 Live Alerts & Notifications", height=400)
        
        # Filter buttons
        filter_frame = tk.Frame(live_panel, bg=self.colors["bg_light"])
        filter_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(filter_frame, text="Filter:", font=("Segoe UI", 10), 
                bg=self.colors["bg_light"], fg=self.colors["text_secondary"]).pack(side="left")
        
        self.alert_filter = tk.StringVar(value="all")
        filters = [("All", "all"), ("Critical", "critical"), ("High", "high"), ("Medium", "medium")]
        
        for text, value in filters:
            btn = tk.Radiobutton(filter_frame, text=text, variable=self.alert_filter, value=value,
                                font=("Segoe UI", 9), bg=self.colors["bg_light"], 
                                fg=self.colors["text_primary"], selectcolor=self.colors["bg_dark"])
            btn.pack(side="left", padx=5)
        
        # Live alerts display
        self.live_alerts_text = scrolledtext.ScrolledText(
            live_panel, height=15, font=("Consolas", 9),
            bg=self.colors["bg_dark"], fg=self.colors["text_primary"],
            insertbackground=self.colors["text_primary"], wrap=tk.WORD
        )
        self.live_alerts_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Control buttons
        control_frame = tk.Frame(live_panel, bg=self.colors["bg_light"])
        control_frame.pack(fill="x", padx=10, pady=5)
        
        self.monitoring_active = tk.BooleanVar(value=True)
        monitor_btn = tk.Checkbutton(control_frame, text="🔴 LIVE MONITORING", 
                                    variable=self.monitoring_active, command=self.toggle_monitoring,
                                    font=("Segoe UI", 10, "bold"), bg=self.colors["bg_light"], 
                                    fg=self.colors["green"], selectcolor=self.colors["bg_dark"])
        monitor_btn.pack(side="left")
        
        clear_log_btn = tk.Button(control_frame, text="🧹 Clear Log", command=self.clear_alerts_log,
                                 font=("Segoe UI", 9), bg=self.colors["purple"], fg="white", relief="flat")
        clear_log_btn.pack(side="right")
        
        # Market Summary Panel
        summary_panel = self.create_panel(parent, "📊 Market Summary", height=200)
        
        self.market_summary_text = scrolledtext.ScrolledText(
            summary_panel, height=8, font=("Segoe UI", 9),
            bg=self.colors["bg_dark"], fg=self.colors["text_primary"],
            insertbackground=self.colors["text_primary"], wrap=tk.WORD
        )
        self.market_summary_text.pack(fill="both", expand=True, padx=10, pady=10)
    
    def create_panel(self, parent, title, height):
        """Create a styled panel with title"""
        panel_frame = tk.LabelFrame(parent, text=title, font=("Segoe UI", 12, "bold"),
                                   bg=self.colors["bg_light"], fg=self.colors["text_primary"],
                                   relief="raised", bd=2)
        panel_frame.pack(fill="x", pady=5)
        panel_frame.configure(height=height)
        return panel_frame
    
    def create_price_alert_inputs(self, parent):
        """Create price alert input fields"""
        # Price input
        price_frame = tk.Frame(parent, bg=self.colors["bg_light"])
        price_frame.pack(fill="x", pady=5)
        
        tk.Label(price_frame, text="Price:", font=("Segoe UI", 10), 
                bg=self.colors["bg_light"], fg=self.colors["text_primary"]).pack(side="left", padx=5)
        
        self.price_entry = tk.Entry(price_frame, font=("Segoe UI", 10), bg=self.colors["bg_dark"], 
                                   fg=self.colors["text_primary"], insertbackground=self.colors["text_primary"])
        self.price_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # Label dropdown
        label_frame = tk.Frame(parent, bg=self.colors["bg_light"])
        label_frame.pack(fill="x", pady=5)
        
        tk.Label(label_frame, text="Label:", font=("Segoe UI", 10), 
                bg=self.colors["bg_light"], fg=self.colors["text_primary"]).pack(side="left", padx=5)
        
        self.label_var = tk.StringVar(value=self.label_options[2])  # Default to Watch
        self.label_dropdown = ttk.Combobox(label_frame, textvariable=self.label_var, 
                                          values=self.label_options, font=("Segoe UI", 10))
        self.label_dropdown.pack(side="left", padx=5, fill="x", expand=True)
        
        # Note input
        note_frame = tk.Frame(parent, bg=self.colors["bg_light"])
        note_frame.pack(fill="x", pady=5)
        
        tk.Label(note_frame, text="Note:", font=("Segoe UI", 10), 
                bg=self.colors["bg_light"], fg=self.colors["text_primary"]).pack(side="left", padx=5)
        
        self.note_entry = tk.Entry(note_frame, font=("Segoe UI", 10), bg=self.colors["bg_dark"], 
                                  fg=self.colors["text_primary"], insertbackground=self.colors["text_primary"])
        self.note_entry.pack(side="left", padx=5, fill="x", expand=True)
    
    def create_ema_alert_inputs(self, parent):
        """Create EMA alert input fields"""
        # Alert type
        type_frame = tk.Frame(parent, bg=self.colors["bg_light"])
        type_frame.pack(fill="x", pady=5)
        
        tk.Label(type_frame, text="Type:", font=("Segoe UI", 10), 
                bg=self.colors["bg_light"], fg=self.colors["text_primary"]).pack(side="left", padx=5)
        
        self.ema_alert_type_var = tk.StringVar(value=self.ema_alert_types[0])
        self.ema_alert_type_dropdown = ttk.Combobox(type_frame, textvariable=self.ema_alert_type_var, 
                                                   values=self.ema_alert_types, font=("Segoe UI", 10))
        self.ema_alert_type_dropdown.pack(side="left", padx=5, fill="x", expand=True)
        
        # Timeframe
        tf_frame = tk.Frame(parent, bg=self.colors["bg_light"])
        tf_frame.pack(fill="x", pady=5)
        
        tk.Label(tf_frame, text="Timeframe:", font=("Segoe UI", 10), 
                bg=self.colors["bg_light"], fg=self.colors["text_primary"]).pack(side="left", padx=5)
        
        self.timeframe_var = tk.StringVar(value=self.timeframe_options[1])  # Default to 1h
        self.timeframe_dropdown = ttk.Combobox(tf_frame, textvariable=self.timeframe_var, 
                                              values=self.timeframe_options, font=("Segoe UI", 10))
        self.timeframe_dropdown.pack(side="left", padx=5, fill="x", expand=True)
        
        # Distance threshold
        dist_frame = tk.Frame(parent, bg=self.colors["bg_light"])
        dist_frame.pack(fill="x", pady=5)
        
        tk.Label(dist_frame, text="Distance %:", font=("Segoe UI", 10), 
                bg=self.colors["bg_light"], fg=self.colors["text_primary"]).pack(side="left", padx=5)
        
        self.distance_entry = tk.Entry(dist_frame, font=("Segoe UI", 10), bg=self.colors["bg_dark"], 
                                      fg=self.colors["text_primary"], insertbackground=self.colors["text_primary"])
        self.distance_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.distance_entry.insert(0, "2.0")
        
        # Note
        note_frame = tk.Frame(parent, bg=self.colors["bg_light"])
        note_frame.pack(fill="x", pady=5)
        
        tk.Label(note_frame, text="Note:", font=("Segoe UI", 10), 
                bg=self.colors["bg_light"], fg=self.colors["text_primary"]).pack(side="left", padx=5)
        
        self.ema_note_entry = tk.Entry(note_frame, font=("Segoe UI", 10), bg=self.colors["bg_dark"], 
                                      fg=self.colors["text_primary"], insertbackground=self.colors["text_primary"])
        self.ema_note_entry.pack(side="left", padx=5, fill="x", expand=True)
    
    def switch_alert_type(self):
        """Switch between price and EMA alert inputs"""
        if self.alert_type.get() == "price":
            self.ema_alert_frame.pack_forget()
            self.price_alert_frame.pack(fill="x", padx=10, pady=10)
        else:
            self.price_alert_frame.pack_forget()
            self.ema_alert_frame.pack(fill="x", padx=10, pady=10)
    
    def add_alert(self):
        """Add new alert with comprehensive error handling"""
        try:
            if self.alert_type.get() == "price":
                price_text = self.price_entry.get().strip()
                if not price_text:
                    messagebox.showerror("❌ Invalid Input", "Please enter a price.")
                    return
                    
                price = float(price_text)
                label = self.label_var.get() if self.label_var.get() else "🟡 Watch"
                note = self.note_entry.get().strip()
                
                alert = {
                    "type": "price",
                    "price": price,
                    "label": label,
                    "notes": note,
                    "importance": label.lower(),
                    "created": datetime.now().isoformat()
                }
                
                self.price_entry.delete(0, tk.END)
                self.note_entry.delete(0, tk.END)
                
                messagebox.showinfo("✅ Alert Added", f"Price alert for ${price:,.2f} created!")
                
            else:
                alert_type = self.ema_alert_type_var.get() if self.ema_alert_type_var.get() else "Cross Above EMA"
                timeframe = self.timeframe_var.get() if self.timeframe_var.get() else "1h"
                note = self.ema_note_entry.get().strip()
                
                alert = {
                    "type": "ema",
                    "ema_alert_type": alert_type,
                    "timeframe": timeframe,
                    "notes": note,
                    "triggered": False,
                    "created": datetime.now().isoformat()
                }
                
                if "Distance" in alert_type:
                    distance_text = self.distance_entry.get().strip()
                    if distance_text:
                        distance = float(distance_text)
                        alert["distance_threshold"] = distance
                
                self.ema_note_entry.delete(0, tk.END)
                
                messagebox.showinfo("✅ Alert Added", f"EMA alert for {timeframe.upper()} created!")
            
            self.alerts.append(alert)
            save_alerts(self.alerts)
            self.refresh_alerts_list()
            
            # Log the alert creation
            self.log_alert(f"✅ Alert created: {alert.get('label', alert.get('ema_alert_type', 'Unknown'))}", "system")
            
        except ValueError as e:
            messagebox.showerror("❌ Invalid Input", f"Please check your input values: {str(e)}")
        except Exception as e:
            messagebox.showerror("❌ Error", f"Failed to add alert: {str(e)}")
            print(f"Add alert error: {e}")
    
    def refresh_alerts_list(self):
        """Refresh the alerts listbox"""
        try:
            self.alerts_listbox.delete(0, tk.END)
            for i, alert in enumerate(self.alerts):
                if alert.get("type") == "ema":
                    alert_type = alert["ema_alert_type"]
                    timeframe = alert["timeframe"].upper()
                    if "distance_threshold" in alert:
                        display_text = f"📈 {alert_type} {alert['distance_threshold']}% on {timeframe}"
                    else:
                        display_text = f"📈 {alert_type} on {timeframe}"
                else:
                    display_text = f"{alert['label']} - ${alert['price']:,.2f}"
                
                if alert.get('notes'):
                    display_text += f" - {alert['notes']}"
                
                self.alerts_listbox.insert(tk.END, display_text)
        except Exception as e:
            print(f"Refresh alerts list error: {e}")
    
    def delete_selected_alert(self):
        """Delete selected alert"""
        try:
            selection = self.alerts_listbox.curselection()
            if selection:
                index = selection[0]
                deleted_alert = self.alerts[index]
                self.alerts.pop(index)
                save_alerts(self.alerts)
                self.refresh_alerts_list()
                
                alert_desc = deleted_alert.get('label', 'EMA Alert') if deleted_alert.get('type') == 'price' else 'EMA Alert'
                self.log_alert(f"🗑️ Alert deleted: {alert_desc}", "system")
                messagebox.showinfo("🗑️ Alert Deleted", f"{alert_desc} has been removed.")
        except Exception as e:
            print(f"Delete alert error: {e}")
    
    def clear_all_alerts(self):
        """Clear all alerts after confirmation"""
        try:
            if messagebox.askyesno("🧹 Clear All Alerts", "Are you sure you want to delete all alerts?"):
                self.alerts = []
                save_alerts(self.alerts)
                self.refresh_alerts_list()
                self.log_alert("🧹 All alerts cleared", "system")
                messagebox.showinfo("✅ Cleared", "All alerts have been deleted.")
        except Exception as e:
            print(f"Clear alerts error: {e}")
    
    def toggle_monitoring(self):
        """Toggle live monitoring on/off"""
        try:
            if self.monitoring_active.get():
                self.log_alert("🟢 LIVE MONITORING ACTIVATED", "system")
            else:
                self.log_alert("🔴 LIVE MONITORING PAUSED", "system")
        except Exception as e:
            print(f"Toggle monitoring error: {e}")
    
    def clear_alerts_log(self):
        """Clear the live alerts log"""
        try:
            self.live_alerts_text.delete(1.0, tk.END)
            self.log_alert("🧹 Alert log cleared", "system")
        except Exception as e:
            print(f"Clear log error: {e}")
    
    def log_alert(self, message, priority="medium"):
        """Log alert to the live alerts display"""
        try:
            if not hasattr(self, 'live_alerts_text'):
                return
                
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_msg = f"[{timestamp}] {message}\n"
            
            # Insert at the top
            self.live_alerts_text.insert(1.0, formatted_msg)
            self.live_alerts_text.see(1.0)
            
            # Keep only last 100 lines
            lines = self.live_alerts_text.get(1.0, tk.END).split('\n')
            if len(lines) > 100:
                self.live_alerts_text.delete(f"{len(lines)-100}.0", tk.END)
        except Exception as e:
            print(f"Log alert error: {e}")
    
    def update_ema_display(self):
        """Update EMA status display"""
        try:
            if not self.ema_data or not hasattr(self, 'ema_labels'):
                return
            
            timeframes = ["15m", "1h", "4h", "1d"]
            above_count = 0
            total_count = 0
            
            for tf in timeframes:
                if tf in self.ema_data and "error" not in self.ema_data[tf]:
                    data = self.ema_data[tf]
                    pct_diff = data["percentage_diff"]
                    above_ema = data["above_ema"]
                    ema_val = data["ema_200"]
                    
                    if above_ema:
                        color = self.colors["green"]
                        symbol = "📈"
                        above_count += 1
                    else:
                        color = self.colors["red"]
                        symbol = "📉"
                    
                    total_count += 1
                    status_text = f"{symbol} ${ema_val:,.0f} ({pct_diff:+.2f}%)"
                    
                    self.ema_labels[tf].config(text=status_text, fg=color)
                else:
                    self.ema_labels[tf].config(text="❌ Error", fg=self.colors["text_secondary"])
            
            # Update EMA status indicator
            if hasattr(self, 'status_labels') and total_count > 0:
                ema_ratio = above_count / total_count
                if ema_ratio >= 0.75:
                    self.status_labels["ema"].config(fg=self.colors["green"])
                elif ema_ratio >= 0.5:
                    self.status_labels["ema"].config(fg=self.colors["yellow"])
                else:
                    self.status_labels["ema"].config(fg=self.colors["red"])
        except Exception as e:
            print(f"Update EMA display error: {e}")
    
    def update_volume_display(self):
        """Update volume and OI display"""
        try:
            if not self.volume_data or not hasattr(self, 'volume_labels'):
                return
            
            timeframes = ["15m", "1h", "4h", "1d"]
            volume_alerts = 0
            
            for tf in timeframes:
                if tf in self.volume_data and "error" not in self.volume_data[tf]:
                    data = self.volume_data[tf]
                    current_vol = data["current_volume"]
                    spike_pct = data["volume_spike_pct"]
                    is_spike = data["is_volume_spike"]
                    
                    if is_spike:
                        color = self.colors["green"] if spike_pct > 0 else self.colors["red"]
                        indicator = "🔥" if spike_pct > 100 else "📊"
                        volume_alerts += 1
                    elif spike_pct < -50:
                        color = self.colors["red"]
                        indicator = "💤"
                    else:
                        color = self.colors["text_secondary"]
                        indicator = "📊"
                    
                    vol_text = f"{indicator} {current_vol:,.0f} ({spike_pct:+.1f}%)"
                    self.volume_labels[tf].config(text=vol_text, fg=color)
                else:
                    self.volume_labels[tf].config(text="❌ Error", fg=self.colors["text_secondary"])
            
            # Update volume status indicator
            if hasattr(self, 'status_labels'):
                if volume_alerts > 0:
                    self.status_labels["volume"].config(fg=self.colors["green"])
                else:
                    self.status_labels["volume"].config(fg=self.colors["yellow"])
            
            # Update OI summary
            if hasattr(self, 'oi_summary_label'):
                oi_summary = self.generate_oi_summary()
                self.oi_summary_label.config(text=oi_summary)
                
                # Update OI status indicator
                if hasattr(self, 'status_labels'):
                    if "RISING" in oi_summary or "SURGE" in oi_summary:
                        self.status_labels["oi"].config(fg=self.colors["green"])
                    elif "FALLING" in oi_summary or "COLLAPSE" in oi_summary:
                        self.status_labels["oi"].config(fg=self.colors["red"])
                    else:
                        self.status_labels["oi"].config(fg=self.colors["yellow"])
        except Exception as e:
            print(f"Update volume display error: {e}")
    
    def generate_oi_summary(self):
        """Generate OI summary text"""
        try:
            if not self.volume_data:
                return "Fetching OI data..."
            
            oi_events = []
            for tf, data in self.volume_data.items():
                if "error" not in data:
                    oi_change_1p = data.get("oi_change_1p", 0)
                    oi_change_5p = data.get("oi_change_5p", 0)
                    
                    if abs(oi_change_1p) >= 10:
                        direction = "RISING" if oi_change_1p > 0 else "FALLING"
                        oi_events.append(f"{tf.upper()}: {direction} {oi_change_1p:+.1f}%")
                    
                    if abs(oi_change_5p) >= 20:
                        direction = "SURGE" if oi_change_5p > 0 else "COLLAPSE"
                        oi_events.append(f"{tf.upper()}: {direction} {oi_change_5p:+.1f}% (5p)")
            
            if oi_events:
                return " | ".join(oi_events[:2])  # Show max 2 events
            else:
                return "OI levels stable across timeframes"
        except Exception as e:
            print(f"Generate OI summary error: {e}")
            return "OI analysis error"
    
    def update_confluence_display(self):
        """Update confluence analysis display"""
        try:
            if not self.confluence_results or not hasattr(self, 'confluence_summary'):
                return
            
            # Update confluence summary
            self.confluence_summary.delete(1.0, tk.END)
            
            if "error" in self.confluence_results:
                self.confluence_summary.insert(tk.END, f"❌ Analysis Error: {self.confluence_results['error']}")
                return
            
            # Display confluence analysis
            summary_text = f"🎯 CONFLUENCE ANALYSIS SUMMARY\n"
            summary_text += f"{'='*50}\n"
            summary_text += f"💰 BTC: ${self.confluence_results.get('current_price', 0):,.2f}\n"
            
            context = self.confluence_results.get('price_context', {})
            summary_text += f"📊 Trend: {context.get('trend_strength', 'unknown').upper()}\n"
            summary_text += f"📈 EMA Position: {context.get('above_ema_count', 0)}/4 above\n\n"
            
            alerts = self.confluence_results.get('alerts', [])
            if alerts:
                summary_text += f"🔥 ACTIVE SIGNALS ({len(alerts)}):\n"
                for alert in alerts[:5]:  # Show top 5
                    priority_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}.get(alert['priority'], "⚪")
                    summary_text += f"{priority_icon} {alert['message']}\n"
                    summary_text += f"   └─ {alert['details']}\n\n"
            else:
                summary_text += "😴 No significant confluence signals detected\n"
                summary_text += "Market conditions don't meet strict criteria."
            
            self.confluence_summary.insert(tk.END, summary_text)
            
            # Update confluence status indicator
            if hasattr(self, 'status_labels'):
                critical_alerts = len([a for a in alerts if a.get('priority') == 'critical'])
                high_alerts = len([a for a in alerts if a.get('priority') == 'high'])
                
                if critical_alerts > 0:
                    self.status_labels["confluence"].config(fg=self.colors["red"])
                elif high_alerts > 0:
                    self.status_labels["confluence"].config(fg=self.colors["yellow"])
                elif alerts:
                    self.status_labels["confluence"].config(fg=self.colors["blue"])
                else:
                    self.status_labels["confluence"].config(fg=self.colors["text_secondary"])
        except Exception as e:
            print(f"Update confluence display error: {e}")
    
    def update_market_summary(self):
        """Update overall market summary"""
        try:
            if not hasattr(self, 'market_summary_text'):
                return
                
            if not all([self.ema_data, self.volume_data, self.confluence_results]):
                return
            
            self.market_summary_text.delete(1.0, tk.END)
            
            # Generate comprehensive market summary
            summary = f"📊 MARKET OVERVIEW - {datetime.now().strftime('%H:%M:%S')}\n"
            summary += f"{'='*50}\n\n"
            
            # Price and trend analysis
            price_context = self.confluence_results.get('price_context', {})
            trend_strength = price_context.get('trend_strength', 'unknown')
            above_ema_count = price_context.get('above_ema_count', 0)
            
            summary += f"💰 Current Price: ${self.current_price:,.2f}\n"
            summary += f"📈 Trend Strength: {trend_strength.upper()}\n"
            summary += f"🎯 EMA Alignment: {above_ema_count}/4 timeframes bullish\n\n"
            
            # Market sentiment
            if above_ema_count >= 3:
                sentiment = "🚀 BULLISH"
                sentiment_color = "Strong uptrend with EMA support"
            elif above_ema_count >= 2:
                sentiment = "⚖️ NEUTRAL-BULLISH" 
                sentiment_color = "Mixed signals, slight bullish bias"
            elif above_ema_count >= 1:
                sentiment = "⚖️ NEUTRAL-BEARISH"
                sentiment_color = "Mixed signals, slight bearish bias"
            else:
                sentiment = "🐻 BEARISH"
                sentiment_color = "Strong downtrend, EMA resistance"
            
            summary += f"📊 Market Sentiment: {sentiment}\n"
            summary += f"📝 Analysis: {sentiment_color}\n\n"
            
            # Volume analysis
            volume_spikes = sum(1 for tf, data in self.volume_data.items() 
                               if "error" not in data and data.get("is_volume_spike", False))
            
            if volume_spikes >= 2:
                volume_status = "🔥 HIGH ACTIVITY"
                volume_desc = f"Volume spikes on {volume_spikes} timeframes"
            elif volume_spikes == 1:
                volume_status = "📊 MODERATE ACTIVITY"
                volume_desc = "Volume spike on 1 timeframe"
            else:
                volume_status = "💤 LOW ACTIVITY"
                volume_desc = "Normal/low volume across timeframes"
            
            summary += f"📊 Volume Status: {volume_status}\n"
            summary += f"📝 Description: {volume_desc}\n\n"
            
            # Alert summary
            alerts = self.confluence_results.get('alerts', [])
            critical_count = len([a for a in alerts if a.get('priority') == 'critical'])
            high_count = len([a for a in alerts if a.get('priority') == 'high'])
            
            summary += f"🚨 Active Alerts: {len(alerts)} total\n"
            if critical_count > 0:
                summary += f"🔴 Critical: {critical_count} (Major opportunities!)\n"
            if high_count > 0:
                summary += f"🟠 High Priority: {high_count}\n"
            
            if not alerts:
                summary += f"😴 No major signals - Waiting for clearer opportunities\n"
            
            # Trading recommendation
            summary += f"\n💡 TRADING INSIGHT:\n"
            if critical_count > 0:
                summary += f"🎯 ACTIONABLE: Multiple critical signals detected!\n"
                summary += f"Consider position sizing based on confluence strength.\n"
            elif high_count > 0:
                summary += f"⚠️ WATCH CLOSELY: High-priority signals active.\n"
                summary += f"Monitor for additional confirmation.\n"  
            elif trend_strength == "strong":
                summary += f"📈 TREND FOLLOWING: Strong {sentiment.split()[1].lower()} trend.\n"
                summary += f"Look for continuation patterns.\n"
            else:
                summary += f"😴 PATIENCE: Waiting for clearer market direction.\n"
                summary += f"Avoid overtrading in mixed conditions.\n"
            
            self.market_summary_text.insert(tk.END, summary)
            
            # Update overall market sentiment in header
            if hasattr(self, 'sentiment_label'):
                self.sentiment_label.config(text=sentiment, 
                                           fg=self.colors["green"] if "BULLISH" in sentiment 
                                           else self.colors["red"] if "BEARISH" in sentiment 
                                           else self.colors["yellow"])
        except Exception as e:
            print(f"Update market summary error: {e}")
    
    def check_alert_triggers(self):
        """Check for triggered alerts"""
        try:
            if not self.current_price or not self.alerts:
                return
            
            proximity = 250  # Price alert proximity
            triggered_alerts = []
            
            for alert in self.alerts[:]:
                if alert.get("type") == "ema":
                    # Check EMA alerts
                    if self.check_ema_alert_trigger(alert):
                        triggered_alerts.append(alert)
                else:
                    # Check price alerts
                    if abs(alert["price"] - self.current_price) <= proximity:
                        triggered_alerts.append(alert)
            
            # Process triggered alerts
            for alert in triggered_alerts:
                if alert.get("type") == "ema":
                    msg = f"📈 EMA Alert: {alert['ema_alert_type']} on {alert['timeframe'].upper()}"
                else:
                    msg = f"💰 Price Alert: {alert['label']} hit at ${self.current_price:,.2f}"
                
                self.log_alert(msg, "high")
                
                # Send notification
                try:
                    notification.notify(
                        title="🚨 Alert_IQ Alert",
                        message=msg,
                        timeout=10
                    )
                except Exception as e:
                    print(f"Notification error: {e}")
            
            # Remove triggered alerts
            if triggered_alerts:
                self.alerts = [a for a in self.alerts if a not in triggered_alerts]
                save_alerts(self.alerts)
                self.refresh_alerts_list()
        except Exception as e:
            print(f"Check alert triggers error: {e}")
    
    def check_ema_alert_trigger(self, alert):
        """Check if EMA alert should trigger"""
        try:
            if not self.ema_data:
                return False
            
            timeframe = alert["timeframe"]
            alert_type = alert["ema_alert_type"]
            
            if timeframe not in self.ema_data or "error" in self.ema_data[timeframe]:
                return False
            
            current_data = self.ema_data[timeframe]
            current_above_ema = current_data["above_ema"]
            current_pct_diff = abs(current_data["percentage_diff"])
            
            # Store previous state
            if "previous_above_ema" not in alert:
                alert["previous_above_ema"] = current_above_ema
                return False
            
            previous_above_ema = alert["previous_above_ema"]
            triggered = False
            
            if alert_type == "Cross Above EMA":
                triggered = not previous_above_ema and current_above_ema
            elif alert_type == "Cross Below EMA":
                triggered = previous_above_ema and not current_above_ema
            elif alert_type == "Distance Above EMA":
                threshold = alert.get("distance_threshold", 2.0)
                triggered = current_above_ema and current_pct_diff >= threshold
            elif alert_type == "Distance Below EMA":
                threshold = alert.get("distance_threshold", 2.0)
                triggered = not current_above_ema and current_pct_diff >= threshold
            
            # Update previous state
            alert["previous_above_ema"] = current_above_ema
            
            return triggered
        except Exception as e:
            print(f"Check EMA alert trigger error: {e}")
            return False
    
    def start_data_updates(self):
        """Start background data updates with better error handling"""
        def update_loop():
            update_count = 0
            while self.gui_active:
                try:
                    update_count += 1
                    print(f"🔄 Update cycle {update_count}")
                    
                    # Check if GUI is still alive
                    if not self.root.winfo_exists():
                        print("GUI closed, stopping updates")
                        break
                    
                    # Only update if monitoring is active
                    if not hasattr(self, 'monitoring_active') or self.monitoring_active.get():
                        # Update current price
                        try:
                            price = get_btc_price()
                            if price:
                                self.current_price = price
                                # Safe GUI update
                                try:
                                    self.root.after_idle(lambda: self.price_label.config(text=f"${price:,.2f}"))
                                except:
                                    pass  # GUI might be closing
                        except Exception as e:
                            print(f"Price update error: {e}")
                        
                        # Update EMA data
                        try:
                            ema_data = self.ema_engine.analyze_ema("BTCUSDT")
                            self.ema_data = ema_data
                            try:
                                self.root.after_idle(self.update_ema_display)
                            except:
                                pass
                        except Exception as e:
                            print(f"EMA update error: {e}")
                        
                        # Update volume/OI data
                        try:
                            volume_data = self.volume_engine.analyze_volume_oi("BTCUSDT")
                            self.volume_data = volume_data
                            try:
                                self.root.after_idle(self.update_volume_display)
                            except:
                                pass
                        except Exception as e:
                            print(f"Volume update error: {e}")
                        
                        # Update confluence analysis (less frequently)
                        if update_count % 2 == 0:  # Every other update
                            try:
                                confluence_results = self.confluence_engine.run_confluence_analysis("BTCUSDT")
                                self.confluence_results = confluence_results
                                try:
                                    self.root.after_idle(self.update_confluence_display)
                                except:
                                    pass
                                
                                # Log confluence alerts
                                if "alerts" in confluence_results:
                                    for alert in confluence_results["alerts"]:
                                        if alert.get("priority") in ["critical", "high"]:
                                            msg = f"🎯 {alert['priority'].upper()}: {alert['message']}"
                                            try:
                                                self.root.after_idle(lambda m=msg: self.log_alert(m, alert['priority']))
                                            except:
                                                pass
                            except Exception as e:
                                print(f"Confluence update error: {e}")
                        
                        # Update market summary
                        try:
                            self.root.after_idle(self.update_market_summary)
                        except:
                            pass
                        
                        # Check for alert triggers
                        try:
                            self.root.after_idle(self.check_alert_triggers)
                        except:
                            pass
                    
                    print(f"✅ Update cycle {update_count} completed")
                
                except Exception as e:
                    print(f"❌ Update loop error: {e}")
                
                # Sleep for 30 seconds
                for i in range(30):
                    if not self.gui_active or not hasattr(self, 'root') or not self.root.winfo_exists():
                        print("GUI closed during sleep, exiting update loop")
                        return
                    time.sleep(1)
        
        # Start update thread
        self.update_thread = threading.Thread(target=update_loop, daemon=True)
        self.update_thread.start()
        
        # Initial load
        try:
            self.refresh_alerts_list()
            self.log_alert("🚀 Alert_IQ started successfully!", "system")
            print("✅ Initial setup completed")
        except Exception as e:
            print(f"❌ Initial load error: {e}")
    
    def on_closing(self):
        """Handle GUI closing"""
        try:
            print("🛑 Shutting down Alert_IQ...")
            self.gui_active = False
            
            # Wait a moment for threads to close
            time.sleep(1)
            
            self.root.destroy()
        except Exception as e:
            print(f"Shutdown error: {e}")


def main():
    """Launch the professional Alert_IQ application with error handling"""
    try:
        print("🚀 Starting Alert_IQ...")
        
        root = tk.Tk()
        
        # Add error handling for GUI creation
        try:
            app = ProfessionalAlertIQ(root)
        except Exception as e:
            print(f"❌ Failed to create GUI: {e}")
            messagebox.showerror("Startup Error", f"Failed to initialize Alert_IQ:\n{str(e)}")
            return
        
        # Handle window closing
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        
        # Center window on screen
        try:
            root.update_idletasks()
            x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
            y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
            root.geometry(f"+{x}+{y}")
        except Exception as e:
            print(f"⚠️ Window positioning error: {e}")
        
        print("✅ GUI ready, starting main loop...")
        root.mainloop()
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        try:
            messagebox.showerror("Critical Error", f"Alert_IQ encountered a critical error:\n{str(e)}")
        except:
            pass


if __name__ == "__main__":
    main()
    """Delete selected alert"""