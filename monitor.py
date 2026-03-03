import os
import json
import requests
import time
from datetime import datetime, timedelta

# --- CONFIG ---
THRESHOLD_PERCENT = 2.0
DATA_FILE = "history.json"
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(message, level="info"):
    icons = {"info": "📅", "crash": "🚨"}
    title = "*SCHEDULED UPDATE*" if level == "info" else "*CRITICAL DROP ALERT*"
    full_body = f"{icons[level]} {title} {icons[level]}\n\n{message}"
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": full_body, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def main():
    # 1. Load Data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            db = json.load(f)
    else:
        db = {"last_scheduled_time": 0, "history": {}, "logs": []}

    # 2. Scrape Data (Replace placeholders with your real functions)
    current_prices = {"site1": 100.0, "site2": 100.0, "site3": 50.0, "site4": 48.0}
    now_ts = time.time()
    
    report_lines = []
    is_crash = False

    # 3. Analyze Prices
    for site, val in current_prices.items():
        old_val = db["history"].get(site)
        if old_val:
            change = ((val - old_val) / old_val) * 100
            line = f"• {site.upper()}: `{val}` (Prev: `{old_val}`, {change:+.2f}%)"
            if change <= -THRESHOLD_PERCENT:
                is_crash = True
                line = f"📉 {line} — *DROP!*"
            report_lines.append(line)
        else:
            report_lines.append(f"• {site.upper()}: `{val}` (Initial)")
        
        db["history"][site] = val # Update current price

    # 4. Decision Logic
    final_msg = "\n".join(report_lines)
    two_hours_ago = now_ts - (2 * 60 * 60)
    
    should_send = False
    alert_level = "info"

    if is_crash:
        should_send = True
        alert_level = "crash"
    elif now_ts >= db.get("last_scheduled_time", 0) + (2 * 60 * 60):
        should_send = True
        alert_level = "info"
        db["last_scheduled_time"] = now_ts # Update the 2-hour timer

    if should_send:
        send_telegram(final_msg, level=alert_level)

    # 5. Maintain Log (Max 50 entries)
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "prices": current_prices,
        "alert_sent": should_send
    }
    db["logs"].append(log_entry)
    
    # Remove oldest if > 50
    if len(db["logs"]) > 50:
        db["logs"] = db["logs"][-50:]

    # 6. Save back to JSON
    with open(DATA_FILE, "w") as f:
        json.dump(db, f, indent=4)

if __name__ == "__main__":
    main()
