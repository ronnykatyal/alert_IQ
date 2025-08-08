import os
import json
from plyer import notification  # pip install plyer

DATA_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "btc.json"))

class AlertManager:
    def __init__(self, proximity=250):
        self.proximity = proximity
        self.alert_file = DATA_FILE
        self.ensure_file()

    def ensure_file(self):
        if not os.path.exists(self.alert_file):
            with open(self.alert_file, "w") as f:
                json.dump({"alerts": []}, f, indent=2)

    def load_alerts(self):
        try:
            with open(self.alert_file, "r") as f:
                data = json.load(f)
                return data.get("alerts", [])
        except Exception as e:
            print(f"❌ Failed to load alerts: {e}")
            return []

    def save_alerts(self, alerts):
        try:
            with open(self.alert_file, "w") as f:
                json.dump({"alerts": alerts}, f, indent=2)
        except Exception as e:
            print(f"❌ Failed to save alerts: {e}")

    def check_alerts(self, current_price):
        alerts = self.load_alerts()
        remaining_alerts = []

        print(f"🔎 Checking alerts against live price: ${current_price}")

        for alert in alerts:
            alert_price = alert["price"]
            label = alert.get("label", "")
            notes = alert.get("notes", "")

            if abs(current_price - alert_price) <= self.proximity:
                print(f"🚨 Triggered: ${alert_price} | Label: {label} | Notes: {notes}")
                self.send_notification(f"{label}: {notes}", f"BTC hit ${current_price:.2f} (target: ${alert_price})")
                # ✅ DO NOT add to remaining_alerts → this removes it
            else:
                remaining_alerts.append(alert)

        self.save_alerts(remaining_alerts)

    def add_alert(self, price, label, notes=""):
        alerts = self.load_alerts()
        alerts.append({
            "price": price,
            "label": label,
            "importance": label.lower(),
            "notes": notes
        })
        self.save_alerts(alerts)

    def send_notification(self, title, message):
        try:
            notification.notify(
                title=title,
                message=message,
                timeout=10,
                app_name="AlertIQ"
            )
        except Exception as e:
            print(f"❌ Notification failed: {e}")
