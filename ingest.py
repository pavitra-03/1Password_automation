import requests
import json
import os
import sys
from datetime import datetime

API_TOKEN = os.getenv("ONEPASSWORD_EVENTS_TOKEN")
if not API_TOKEN:
    print("Error: ONEPASSWORD_EVENTS_TOKEN variable not set.")
    sys.exit(1)

BASE_URL = "https://events.1password.com/api/v2"
STATE_FILE = "1password_cursors.json"
LOG_OUTPUT_FILE = "1password_events.log"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def load_cursors():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading state file: {e}")
    return {"auditevents": None, "signinattempts": None, "itemusages": None}

def save_cursors(cursors):
    with open(STATE_FILE, "w") as f:
        json.dump(cursors, f, indent=4)

def append_to_log(endpoint_name, items):
    if not items:
        return
    with open(LOG_OUTPUT_FILE, "a") as f:
        for item in items:
            item["_ingested_at"] = datetime.utcnow().isoformat()
            item["_log_type"] = endpoint_name
            f.write(json.dumps(item) + "\n")

def fetch_1password_logs():
    cursors = load_cursors()
    endpoints = ["auditevents", "signinattempts", "itemusages"]

    for endpoint in endpoints:
        url = f"{BASE_URL}/{endpoint}"
        
        if cursors.get(endpoint):
            payload = {"cursor": cursors[endpoint]}
        else:
            payload = {"limit": 100}

        try:
            response = requests.post(url, headers=HEADERS, json=payload)
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                append_to_log(endpoint, items)
                print(f"[{datetime.utcnow()}] [{endpoint}] Retrieved {len(items)} new events.")
                
                new_cursor = data.get("cursor")
                if new_cursor:
                    cursors[endpoint] = new_cursor
            else:
                print(f"Error fetching {endpoint}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Exception during ingestion of {endpoint}: {str(e)}")

    save_cursors(cursors)

if __name__ == "__main__":
    fetch_1password_logs()
