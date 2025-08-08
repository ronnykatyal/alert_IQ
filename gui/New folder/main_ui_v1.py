# gui/main_ui.py - Updated with EMA Integration
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import threading
import time
from plyer import notification
from tools.fetcher import get_btc_price
from tools.ema_engine_production import ProductionEMAEngine

# Proper JSON path
DATA_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "btc.json"))

# Load & Save JSON
def load_alerts():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({"alerts": []}, f, indent=2)
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
        return data.get("alerts", [])

def save_alerts(alerts):
    with open(DATA_FILE, "w") as f:
        json.dump({"alerts": alerts}, f, indent=2)

class AlertApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📊 AlertIQ - Crypto Alert System")
        self.root.geometry("700x800")
        self.root.configure(bg="#f0f2f5")

        self.alerts = load_alerts()
        self.triggered = []
        self.label_options = [
            "🟢 Support", "🔴 Resistance", "🟡 Watch", "🔵 Breakout",
            "🟣 Custom", "⚪ Retest", "🟤 Demand", "⚫ Supply"
        ]
        
        # Initialize EMA Engine
        self.ema_engine = ProductionEMAEngine()
        self.ema_data = {}

        self.create_widgets()
        self.update_price_loop()
        self.update_ema_loop()

    def create_widgets(self):
        # Main container with two columns
        main_frame = tk.Frame(self.root, bg="#f0f2f5")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Left column for EMA and price data
        left_frame = tk.Frame(main_frame, bg="#f0f2f5")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Right column for alerts
        right_frame = tk.Frame(main_frame, bg="#f0f2f5")
        right_frame.pack(side="right", fill="both", expand=True)

        # === LEFT COLUMN ===
        # 💰 Live Price Label
        self.price_label = tk.Label(left_frame, text="BTC Price: $--", 
                                   font=("Segoe UI", 18, "bold"), bg="#f0f2f5", fg="#1f2937")
        self.price_label.pack(pady=(0, 20))

        # 📈 EMA Status Section
        ema_frame = tk.LabelFrame(left_frame, text="📈 200 EMA Status", 
                                 font=("Segoe UI", 12, "bold"), bg="#ffffff", 
                                 relief="raised", bd=2, padx=10, pady=10)
        ema_frame.pack(fill="x", pady=(0, 20))

        # EMA status labels for each timeframe
        self.ema_labels = {}
        timeframes = ["15m", "1h", "4h", "1d"]
        
        for i, tf in enumerate(timeframes):
            frame = tk.Frame(ema_frame, bg="#ffffff")
            frame.pack(fill="x", pady=2)
            
            # Timeframe label
            tf_label = tk.Label(frame, text=f"{tf.upper()}:", font=("Segoe UI", 11, "bold"), 
                               bg="#ffffff", fg="#374151", width=8, anchor="w")
            tf_label.pack(side="left")
            
            # Status label (will be updated with EMA data)
            status_label = tk.Label(frame, text="Loading...", font=("Segoe UI", 11), 
                                   bg="#ffffff", fg="#6b7280", anchor="w")
            status_label.pack(side="left", fill="x", expand=True)
            
            self.ema_labels[tf] = status_label

        # Market sentiment summary
        self.sentiment_label = tk.Label(ema_frame, text="Market Sentiment: Loading...", 
                                       font=("Segoe UI", 12, "bold"), bg="#ffffff", fg="#1f2937")
        self.sentiment_label.pack(pady=(10, 0))

        # === RIGHT COLUMN ===
        # 🔔 Alert Input Section
        alert_frame = tk.LabelFrame(right_frame, text="🔔 Add New Alert", 
                                   font=("Segoe UI", 12, "bold"), bg="#ffffff", 
                                   relief="raised", bd=2, padx=10, pady=10)
        alert_frame.pack(fill="x", pady=(0, 20))

        input_frame = tk.Frame(alert_frame, bg="#ffffff")
        input_frame.pack(fill="x")

        tk.Label(input_frame, text="Price:", bg="#ffffff", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", pady=5)
        self.price_entry = tk.Entry(input_frame, font=("Segoe UI", 10))
        self.price_entry.grid(row=0, column=1, pady=5, padx=(10, 0), sticky="ew")

        tk.Label(input_frame, text="Label:", bg="#ffffff", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", pady=5)
        self.label_var = tk.StringVar()
        self.label_dropdown = ttk.Combobox(input_frame, textvariable=self.label_var, 
                                          values=self.label_options, font=("Segoe UI", 10))
        self.label_dropdown.current(2)
        self.label_dropdown.grid(row=1, column=1, pady=5, padx=(10, 0), sticky="ew")

        tk.Label(input_frame, text="Note:", bg="#ffffff", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w", pady=5)
        self.note_entry = tk.Entry(input_frame, font=("Segoe UI", 10))
        self.note_entry.grid(row=2, column=1, pady=5, padx=(10, 0), sticky="ew")

        # Configure grid weight
        input_frame.columnconfigure(1, weight=1)

        add_btn = tk.Button(alert_frame, text="➕ Add Alert", command=self.add_alert, 
                           font=("Segoe UI", 10, "bold"), bg="#10b981", fg="white", 
                           relief="raised", bd=2, pady=5)
        add_btn.pack(pady=(10, 0))

        # 📋 Active Alerts Section
        active_frame = tk.LabelFrame(right_frame, text="📋 Active Alerts", 
                                    font=("Segoe UI", 12, "bold"), bg="#ffffff", 
                                    relief="raised", bd=2, padx=10, pady=10)
        active_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Add scrollbar to alerts listbox
        alerts_scroll_frame = tk.Frame(active_frame, bg="#ffffff")
        alerts_scroll_frame.pack(fill="both", expand=True)

        alerts_scrollbar = tk.Scrollbar(alerts_scroll_frame)
        alerts_scrollbar.pack(side="right", fill="y")

        self.alerts_listbox = tk.Listbox(alerts_scroll_frame, height=8, font=("Segoe UI", 9), 
                                        yscrollcommand=alerts_scrollbar.set)
        self.alerts_listbox.pack(side="left", fill="both", expand=True)
        alerts_scrollbar.config(command=self.alerts_listbox.yview)

        # 🚨 Triggered Alerts Section
        triggered_frame = tk.LabelFrame(right_frame, text="🚨 Triggered Alerts", 
                                       font=("Segoe UI", 12, "bold"), bg="#ffffff", 
                                       relief="raised", bd=2, padx=10, pady=10)
        triggered_frame.pack(fill="both", expand=True)

        # Add scrollbar to triggered alerts
        triggered_scroll_frame = tk.Frame(triggered_frame, bg="#ffffff")
        triggered_scroll_frame.pack(fill="both", expand=True)

        triggered_scrollbar = tk.Scrollbar(triggered_scroll_frame)
        triggered_scrollbar.pack(side="right", fill="y")

        self.triggered_box = tk.Listbox(triggered_scroll_frame, height=6, font=("Segoe UI", 9), 
                                       yscrollcommand=triggered_scrollbar.set)
        self.triggered_box.pack(side="left", fill="both", expand=True)
        triggered_scrollbar.config(command=self.triggered_box.yview)

        self.refresh_alerts_list()

    def add_alert(self):
        try:
            price = float(self.price_entry.get())
            label = self.label_var.get()
            note = self.note_entry.get()
            alert = {"price": price, "label": label, "notes": note, "importance": label.lower()}
            self.alerts.append(alert)
            save_alerts(self.alerts)
            messagebox.showinfo("✅ Alert Saved", f"Alert for ${price:,.2f} added!")
            
            # Clear input fields
            self.price_entry.delete(0, tk.END)
            self.note_entry.delete(0, tk.END)
            
            self.refresh_alerts_list()
        except ValueError:
            messagebox.showerror("❌ Invalid Price", "Please enter a valid numeric price.")

    def refresh_alerts_list(self):
        self.alerts_listbox.delete(0, tk.END)
        for a in self.alerts:
            self.alerts_listbox.insert(tk.END, f"{a['label']} - ${a['price']:,.2f} - {a['notes']}")

    def update_ema_display(self):
        """Update EMA labels with current data"""
        if not self.ema_data:
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
                
                # Color and symbol based on above/below EMA
                if above_ema:
                    color = "#10b981"  # Green
                    symbol = "📈"
                    above_count += 1
                else:
                    color = "#ef4444"  # Red
                    symbol = "📉"
                
                total_count += 1
                
                # Format the display text
                status_text = f"{symbol} ${ema_val:,.0f} ({pct_diff:+.2f}%)"
                
                self.ema_labels[tf].config(text=status_text, fg=color)
            else:
                self.ema_labels[tf].config(text="❌ Error", fg="#6b7280")
        
        # Update market sentiment
        if total_count > 0:
            bullish_ratio = above_count / total_count
            if bullish_ratio >= 0.75:
                sentiment = "🚀 BULLISH"
                sentiment_color = "#10b981"
            elif bullish_ratio >= 0.5:
                sentiment = "⚖️ NEUTRAL"
                sentiment_color = "#f59e0b"
            else:
                sentiment = "🐻 BEARISH"
                sentiment_color = "#ef4444"
            
            sentiment_text = f"Market Sentiment: {sentiment} ({above_count}/{total_count} above EMA)"
            self.sentiment_label.config(text=sentiment_text, fg=sentiment_color)

    def update_price_loop(self):
        def loop():
            while True:
                price = get_btc_price()
                if price:
                    self.root.after(0, lambda p=price: self.price_label.config(text=f"BTC Price: ${p:,.2f}"))
                    self.check_triggers(price)
                time.sleep(30)
        threading.Thread(target=loop, daemon=True).start()

    def update_ema_loop(self):
        def loop():
            while True:
                try:
                    # Fetch EMA data
                    ema_results = self.ema_engine.analyze_ema("BTCUSDT")
                    self.ema_data = ema_results
                    
                    # Update display in main thread
                    self.root.after(0, self.update_ema_display)
                    
                except Exception as e:
                    print(f"EMA update error: {e}")
                
                time.sleep(30)  # Update every 30 seconds
        threading.Thread(target=loop, daemon=True).start()

    def check_triggers(self, live_price):
        proximity = 250  # hardcoded for now
        triggered_now = []
        for alert in self.alerts[:]:
            if abs(alert["price"] - live_price) <= proximity:
                msg = f"🚨 ${live_price:.2f} | {alert['label']} | {alert['notes']}"
                self.triggered_box.insert(0, msg)  # Insert at top
                notification.notify(title="🚨 BTC Alert Triggered!", message=msg, timeout=8)
                triggered_now.append(alert)
        
        if triggered_now:
            self.alerts = [a for a in self.alerts if a not in triggered_now]
            save_alerts(self.alerts)
            self.refresh_alerts_list()

# Run App
if __name__ == "__main__":
    root = tk.Tk()
    app = AlertApp(root)
    root.mainloop()