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
            db = json.load(f)
    else:
        db = {"last_scheduled_time": 0, "history": {}, "logs": []}

    url = f"{LINK_1}"

    print(url)

    response = requests.get(url)
    response.raise_for_status() # Raise an exception for HTTP errors

    # Parse the JSON response
    data = response.json()

    # Extract silver and gold prices
    silver_price = data['data']['prices']['silver']['price']
    gold_price = data['data']['prices']['gold']['price'] # Correctly extract gold price

    url = f"{LINK_2}"

    print(url)

    response = requests.get(url)
    response.raise_for_status() # Raise an exception for HTTP errors

    data = response.json()

    gold_price_1 = data['rate']['rates']['gBuy']
    silver_price_1 = data['rate']['rates']['sBuy']

    # 2. Get Prices (REPLACE these with your actual scraping logic/functions)
    current_prices = {
        "Site_1": {"Gold": gold_price, "Silver": silver_price},
        "Site_2": {"Gold": gold_price_1, "Silver": silver_price_1}
    }
    
    now_ts = time.time()
    report_lines = []
    any_price_crashed = False

    # 3. Process the Two Sites
    for site in ["Site_1", "Site_2"]:
        if(site == "Site_1"):
            site_header = f"📍 *Lalitha Jewellers*"
        else:
            site_header = f"📍 *Augmont*
        site_lines = [site_header]
        
        # Get old data for this specific site
        old_site_data = db["history"].get(site, {})

        for label in ["Gold", "Silver"]:
            curr_val = current_prices[site][label]
            prev_val = old_site_data.get(label)
            
            label_name = label.replace('_', ' ').title() # "Price A"
            
            if prev_val is not None:
                change = ((curr_val - prev_val) / prev_val) * 100
                change_str = f"{change:+.2f}%"
                
                line = f"  • {label_name}: `{curr_val}` (Prev: `{prev_val}`, {change_str})"
                
                # Logic: If ANY individual price drops >= THRESHOLD
                if change <= -THRESHOLD_PERCENT:
                    any_price_crashed = True
                    line = f"  📉 {line} — *DROP!*"
                
                site_lines.append(line)
            else:
                site_lines.append(f"  • {label_name}: `{curr_val}` (Baseline set)")
        
        report_lines.append("\n".join(site_lines))
        db["history"][site] = current_prices[site]

    # 4. Message Logic
    final_msg = "\n\n".join(report_lines)
    two_hours = 2 * 60 * 60
    is_time_for_update = now_ts >= (db.get("last_scheduled_time", 0) + two_hours)

    if any_price_crashed:
        send_telegram(final_msg, level="alert")
        # Optional: update last_scheduled_time here if you want to skip 
        # the next scheduled update after a crash alert.
    elif is_time_for_update:
        send_telegram(final_msg, level="info")
        db["last_scheduled_time"] = now_ts

    # 5. Maintain Logs (keep 50)
    db["logs"].append({"t": datetime.now().isoformat(), "alert": any_price_crashed})
    db["logs"] = db["logs"][-50:]

    # 6. Save State
    with open(DATA_FILE, "w") as f:
        json.dump(db, f, indent=4)

if __name__ == "__main__":
    main()
