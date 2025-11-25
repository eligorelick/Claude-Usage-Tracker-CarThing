"""
Claude Usage Server for Car Thing
Fetches Claude.ai usage stats and serves them over local network

Created by Eli Gorelick - eligorelick.com
"""

from flask import Flask, jsonify
from curl_cffi import requests
import threading
import time

app = Flask(__name__)
usage_data = {"status": "starting"}

# ============================================================
#                    CONFIGURE THESE VALUES
# ============================================================
#
# ORG_ID: Your Claude organization ID
#   1. Go to https://claude.ai/settings
#   2. Open DevTools (F12) -> Network tab
#   3. Look at any API request URL, it contains your org ID
#   4. Example: 3746c04e-9223-4bde-a29f-39db3e23bfea
#
# SESSION_KEY: Your Claude session cookie
#   1. Go to https://claude.ai (make sure you're logged in)
#   2. Open DevTools (F12) -> Application tab -> Cookies
#   3. Click on https://claude.ai
#   4. Find "sessionKey" and copy its entire value
#   5. Example: sk-ant-sid01-xxxxx...
#
ORG_ID = "YOUR_ORG_ID_HERE"
SESSION_KEY = "YOUR_SESSION_KEY_HERE"
#
# ============================================================

# How often to fetch from Claude API (in seconds)
# Default: 300 (5 minutes) - this won't affect your usage limits
FETCH_INTERVAL = 300


def fetch_usage_loop():
    """Background thread that continuously fetches usage data"""
    global usage_data
    
    print("\n" + "="*50)
    print("Starting usage fetcher...")
    print("="*50 + "\n")
    
    while True:
        try:
            timestamp = time.strftime('%H:%M:%S')
            print(f"[{timestamp}] Fetching usage from Claude.ai...")
            
            response = requests.get(
                f"https://claude.ai/api/organizations/{ORG_ID}/usage",
                headers={
                    "Cookie": f"sessionKey={SESSION_KEY}",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                },
                impersonate="chrome"
            )
            
            if response.status_code == 200:
                usage_data = response.json()
                five_hour = usage_data.get('five_hour', {}).get('utilization', 'N/A')
                seven_day = usage_data.get('seven_day', {}).get('utilization', 'N/A')
                sonnet = usage_data.get('seven_day_sonnet', {}).get('utilization', 'N/A')
                print(f"[{timestamp}] SUCCESS!")
                print(f"           5-Hour: {five_hour}% | 7-Day: {seven_day}% | Sonnet: {sonnet}%")
            elif response.status_code == 401:
                print(f"[{timestamp}] ERROR: Session expired - get new SESSION_KEY from browser")
                usage_data = {"error": "Session expired - update SESSION_KEY"}
            elif response.status_code == 403:
                print(f"[{timestamp}] ERROR: Access denied - check your credentials")
                usage_data = {"error": "Access denied - check credentials"}
            else:
                print(f"[{timestamp}] ERROR: HTTP {response.status_code}")
                usage_data = {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            timestamp = time.strftime('%H:%M:%S')
            print(f"[{timestamp}] ERROR: {e}")
            usage_data = {"error": str(e)}
        
        time.sleep(FETCH_INTERVAL)


@app.route('/')
@app.route('/usage')
def get_usage():
    """Endpoint that serves usage data as JSON"""
    response = jsonify(usage_data)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/health')
def health():
    """Health check endpoint"""
    has_data = "five_hour" in usage_data
    return jsonify({
        "status": "ok",
        "has_data": has_data,
        "message": "Server is running"
    })


def print_banner():
    """Print startup banner"""
    print("\n")
    print("  ╔═══════════════════════════════════════════════╗")
    print("  ║     Claude Usage Server for Car Thing         ║")
    print("  ║                                               ║")
    print("  ║     Created by Eli Gorelick                   ║")
    print("  ║     eligorelick.com                           ║")
    print("  ╚═══════════════════════════════════════════════╝")
    print("\n")


if __name__ == '__main__':
    print_banner()
    
    # Check if credentials are configured
    if ORG_ID == "YOUR_ORG_ID_HERE" or SESSION_KEY == "YOUR_SESSION_KEY_HERE":
        print("  [!] WARNING: You need to configure your credentials!")
        print("")
        print("      1. Open this file (claude_usage_server.py)")
        print("      2. Find ORG_ID and SESSION_KEY near the top")
        print("      3. Replace with your actual values")
        print("      4. See the comments for instructions")
        print("")
        print("  Press Ctrl+C to exit and configure...")
        print("")
    
    # Start the background fetcher thread
    fetcher = threading.Thread(target=fetch_usage_loop, daemon=True)
    fetcher.start()
    
    print(f"  Server: http://172.16.42.1:8080")
    print(f"  Fetch interval: {FETCH_INTERVAL} seconds")
    print("")
    print("  Press Ctrl+C to stop")
    print("")
    print("-"*50)
    
    # Start the Flask server
    app.run(host='172.16.42.1', port=8080, threaded=True)
