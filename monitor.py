import os
import json
import requests
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
THRESHOLD_PERCENT = 2.0  # Alert if drop is > 2%
DATA_FILE = "history.json"
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def scrape_site_1():
    # Placeholder: Your scraping logic for Site 1
    return 100.0

def scrape_site_2():
    # Placeholder: Your scraping logic for Site 2
    return 100.0

def scrape_site_3():
    return 50.0

def scrape_site_4():
    return 48.5  # Example: This is a 3% drop from 50.0

def send_telegram(message):
    if not TOKEN or not CHAT_ID:
        print("Missing Secrets!")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def main():
    # Load previous history
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            history = json.load(f)
    else:
        history = {}

    # Fetch current data
    s1, s2, s3, s4 = scrape_site_1(), scrape_site_2(), scrape_site_3(), scrape_site_4()
    current_data = {"site1": s1, "site2": s2, "site3": s3, "site4": s4}
    
    alerts = []

    # Check 1: Site 1 vs Site 2 Discrepancy
    if s1 != s2:
        alerts.append(f"⚠️ **Sync Error:** Site 1 ({s1}) != Site 2 ({s2})")

    # Check 2: Percentage Drop
    for site, val in current_data.items():
        old_val = history.get(site)
        if old_val:
            change = ((val - old_val) / old_val) * 100
            if change <= -THRESHOLD_PERCENT:
                alerts.append(f"📉 **{site.upper()} Drop:** {change:.2f}% (Now: {val})")
        
        # Update history
        history[site] = val

    # Send alerts if any
    if alerts:
        send_telegram("\n\n".join(alerts))

    # Save history back to file
    with open(DATA_FILE, "w") as f:
        json.dump(history, f, indent=4)

if __name__ == "__main__":
    main()
