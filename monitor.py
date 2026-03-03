import os
import json
import requests
import time
from datetime import datetime

# --- CONFIG ---
# We now define separate thresholds
THRESHOLDS = {
    "Gold": 1.0,   # 1% Drop
    "Silver": 5.0  # 5% Drop
}

DATA_FILE = "history.json"
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
LINK_1 = os.getenv("LINK_1")
LINK_2 = os.getenv("LINK_2")

def clean_to_float(value):
    if value is None: return 0.0
    try:
        if isinstance(value, (int, float)): return float(value)
        clean_str = "".join(c for c in str(value) if c.isdigit() or c == '.')
        return float(clean_str)
    except: return 0.0

def send_telegram(message, level="info"):
    icons = {"info": "📅", "alert": "🚨"}
    title = "*NEW UPDATE*" if level == "info" else "*PRICE DROP ALERT*"
    full_body = f"{icons[level]} {title} {icons[level]}\n\n{message}"
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": full_body, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def main():
    # 1. Load History
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try: db = json.load(f)
            except: db = {"last_scheduled_time": 0, "history": {}, "logs": []}
    else:
        db = {"last_scheduled_time": 0, "history": {}, "logs": []}

    # 2. Fetch Data
    try:
        data1 = requests.get(LINK_1).json()
        data2 = requests.get(LINK_2).json()
        
        current_prices = {
            "Site_1": {
                "Gold": clean_to_float(data1['data']['prices']['gold']['price']),
                "Silver": clean_to_float(data1['data']['prices']['silver']['price'])
            },
            "Site_2": {
                "Gold": clean_to_float(data2['rate']['rates']['gBuy']),
                "Silver": clean_to_float(data2['rate']['rates']['sBuy'])
            }
        }
    except Exception as e:
        print(f"Scrape Error: {e}")
        return

    now_ts = time.time()
    report_lines = []
    any_price_crashed = False

    # 3. Process the Two Sites
    for site in ["Site_1", "Site_2"]:
        site_name = "Lalitha Jewellers" if site == "Site_1" else "Augmont"
        site_lines = [f"📍 *{site_name}*"]
        old_site_data = db["history"].get(site, {})

        for label in ["Gold", "Silver"]:
            curr_val = current_prices[site][label]
            prev_val = old_site_data.get(label)
            
            # Get the specific threshold for this metal
            target_threshold = THRESHOLDS.get(label, 2.0)
            
            if prev_val is not None and prev_val > 0:
                change = ((curr_val - prev_val) / prev_val) * 100
                line = f"  • {label}: `{curr_val}` (Prev: `{prev_val}`, {change:+.2f}%)"
                
                # Compare against the specific Gold (1%) or Silver (5%) limit
                if change <= -target_threshold:
                    any_price_crashed = True
                    line = f"  📉 {line} — *DROP!*"
                
                site_lines.append(line)
            else:
                site_lines.append(f"  • {label}: `{curr_val}` (Baseline set)")
        
        report_lines.append("\n".join(site_lines))

    # 4. Message & Update Logic
    final_msg = "\n\n".join(report_lines)
    is_time_for_update = now_ts >= (db.get("last_scheduled_time", 0) + (2 * 3600))

    if any_price_crashed:
        send_telegram(final_msg, level="alert")
        db["history"] = current_prices # Reset baseline after alert
    elif is_time_for_update:
        send_telegram(final_msg, level="info")
        db["history"] = current_prices # Reset baseline every 2 hours
        db["last_scheduled_time"] = now_ts

    # 5. Save
    db["logs"].append({"t": datetime.now().isoformat(), "alert": any_price_crashed})
    db["logs"] = db["logs"][-50:]
    with open(DATA_FILE, "w") as f:
        json.dump(db, f, indent=4)

if __name__ == "__main__":
    main()
