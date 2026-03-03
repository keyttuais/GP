import os
import json
import requests
import time
from datetime import datetime

# --- CONFIG ---
THRESHOLD_PERCENT = 2.0
DATA_FILE = "history.json"
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
LINK_1 = os.getenv("LINK_1")
LINK_2 = os.getenv("LINK_2")

def clean_to_float(value):
    """Ensures price is a float even if it contains symbols or comes as a string."""
    if value is None:
        return 0.0
    try:
        if isinstance(value, (int, float)):
            return float(value)
        # Remove currency symbols and commas, then convert
        clean_str = "".join(c for c in str(value) if c.isdigit() or c == '.')
        return float(clean_str)
    except Exception as e:
        print(f"Conversion Error: {value} is not a number. {e}")
        return 0.0

def send_telegram(message, level="info"):
    icons = {"info": "📅", "alert": "🚨"}
    title = "*NEW UPDATE FOR YOU*" if level == "info" else "*PRICE DROP ALERT*"
    full_body = f"{icons[level]} {title} {icons[level]}\n\n{message}"
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": full_body, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload)
        r.raise_for_status()
    except Exception as e:
        print(f"Telegram Error: {e}")

def main():
    # 1. Load History
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                db = json.load(f)
            except:
                db = {"last_scheduled_time": 0, "history": {}, "logs": []}
    else:
        db = {"last_scheduled_time": 0, "history": {}, "logs": []}

    # 2. Fetch Data from API 1 (Lalitha)
    try:
        res1 = requests.get(LINK_1)
        res1.raise_for_status()
        data1 = res1.json()
        # Using clean_to_float to prevent TypeError
        silver_1 = clean_to_float(data1['data']['prices']['silver']['price'])
        gold_1 = clean_to_float(data1['data']['prices']['gold']['price'])
    except Exception as e:
        print(f"Error fetching Site 1: {e}")
        return

    # 3. Fetch Data from API 2 (Augmont)
    try:
        res2 = requests.get(LINK_2)
        res2.raise_for_status()
        data2 = res2.json()
        gold_2 = clean_to_float(data2['rate']['rates']['gBuy'])
        silver_2 = clean_to_float(data2['rate']['rates']['sBuy'])
    except Exception as e:
        print(f"Error fetching Site 2: {e}")
        return

    current_prices = {
        "Site_1": {"Gold": gold_1, "Silver": silver_1},
        "Site_2": {"Gold": gold_2, "Silver": silver_2}
    }
    
    now_ts = time.time()
    report_lines = []
    any_price_crashed = False

    # 4. Process the Two Sites
    for site in ["Site_1", "Site_2"]:
        site_name = "Lalitha Jewellers" if site == "Site_1" else "Augmont"
        site_header = f"📍 *{site_name}*"
        site_lines = [site_header]
        
        old_site_data = db["history"].get(site, {})

        for label in ["Gold", "Silver"]:
            curr_val = current_prices[site][label]
            # Ensure prev_val is treated as float when loaded from JSON
            prev_val = old_site_data.get(label)
            if prev_val is not None:
                prev_val = float(prev_val)
            
            if prev_val is not None and prev_val > 0:
                change = ((curr_val - prev_val) / prev_val) * 100
                change_str = f"{change:+.2f}%"
                
                line = f"  • {label}: `{curr_val}` (Prev: `{prev_val}`, {change_str})"
                
                if change <= -THRESHOLD_PERCENT:
                    any_price_crashed = True
                    line = f"  📉 {line} — *DROP!*"
                
                site_lines.append(line)
            else:
                site_lines.append(f"  • {label}: `{curr_val}` (Baseline set)")
        
        report_lines.append("\n".join(site_lines))

    # 5. Message & Update Logic
    final_msg = "\n\n".join(report_lines)
    two_hours = 2 * 60 * 60
    is_time_for_update = now_ts >= (db.get("last_scheduled_time", 0) + two_hours)

    # CRITICAL FIX: Only update history baseline when an alert happens OR at the 2-hour mark
    if any_price_crashed:
        send_telegram(final_msg, level="alert")
        db["history"] = current_prices
    elif is_time_for_update:
        send_telegram(final_msg, level="info")
        db["history"] = current_prices
        db["last_scheduled_time"] = now_ts
    else:
        print("No drop and not time for update. Baseline maintained.")

    # 6. Maintenance & Save
    db["logs"].append({"t": datetime.now().isoformat(), "alert": any_price_crashed})
    db["logs"] = db["logs"][-50:]

    with open(DATA_FILE, "w") as f:
        json.dump(db, f, indent=4)

if __name__ == "__main__":
    main()
