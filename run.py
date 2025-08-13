# run.py

from tools.alert_manager import AlertManager
from tools.fetcher import get_btc_price  # ✅ fixed import

manager = AlertManager()

# You can feed in your alerts manually or keep predefined in btc.json
# manager.add_alert(119800, label="HTF Resistance", note="Watch volume here")

current_price = get_btc_price()
if current_price:
    print(f"\n📈 BTC Price: ${current_price}")
    manager.check_alerts(current_price)
else:
    print("❌ Price fetch failed.")
