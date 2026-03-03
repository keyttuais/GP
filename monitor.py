import os
import json
import requests

# --- CONFIG ---
THRESHOLD_PERCENT = 2.0
DATA_FILE = "history.json"
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FORCE_ALERT = True  # Set to True just to test the message format!

def send_telegram(message, level="info"):
    """
    Sends a formatted Markdown message.
    Levels: info (ℹ️), alert (🚨), sync (⚠️)
    """
    icons = {"info": "ℹ️", "alert": "🚨", "sync": "⚠️"}
    icon = icons.get(level, "🤖")
    
    # Constructing the Markdown string
    header = f"{icon} *SCRAPER NOTIFICATION* {icon}"
    full_body = f"{header}\n\n{message}"

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": full_body,
        "parse_mode": "Markdown"  # Enables *bold* and _italic_
    }
    
    try:
        r = requests.post(url, json=payload)
        r.raise_for_status()
    except Exception as e:
        print(f"Error sending Telegram: {e}")

def main():
    # 1. Dummy data for testing
    s1, s2, s3, s4 = 100.0, 100.0, 50.0, 48.0
    
    # 2. Build the message
    report = []
    
    # Discrepancy Example
    if s1 == s2: # Usually s1 != s2, but for testing we use ==
        report.append(f"🔄 *Sync Status:* Sites 1 & 2 are matching at `{s1}`")

    # Drop Example
    report.append(f"📉 *Price Drop:* Site 4 dropped to *{s4}*")

    # 3. Decision Logic
    final_message = "\n\n".join(report)
    
    if FORCE_ALERT or report:
        send_telegram(final_message, level="alert")
        print("Alert sent!")
    else:
        print("No changes detected. Silence is golden.")

if __name__ == "__main__":
    main()
