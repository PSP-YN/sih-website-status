#!/usr/bin/env python3
"""
SIH (Smart India Hackathon) Website Uptime Checker
Checks if https://sih.gov.in/ is online and sends push notifications to phone.
"""

import os
import sys
import time
import urllib3
import requests

# Disable insecure request warnings if gov site has intermediate SSL chain issues
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SIH_URL = "https://sih.gov.in/"
# Unique default ntfy topic (can be overridden via environment variable NTFY_TOPIC)
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "sih_alert_uptime_notify")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def send_ntfy_notification(title: str, message: str, priority: str = "urgent"):
    """Send free instant push notification via ntfy.sh to phone."""
    try:
        url = f"https://ntfy.sh/{NTFY_TOPIC}"
        # HTTP headers must be ASCII-safe
        safe_title = title.encode("ascii", "ignore").decode("ascii").strip()
        headers = {
            "Title": safe_title or "SIH Status Alert",
            "Priority": priority,  # max/urgent causes loud alarm on phone
            "Tags": "tada,rotating_light,white_check_mark",
            "Click": SIH_URL,
            "Actions": f"view, Open SIH Portal, {SIH_URL}",
        }
        res = requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=10)
        if res.status_code == 200:
            print(f"[✓] Push notification successfully sent via ntfy.sh/{NTFY_TOPIC}")
        else:
            print(f"[!] ntfy.sh returned status {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[x] Error sending ntfy notification: {e}")


def send_telegram_notification(message: str):
    """Optional Telegram push notification if credentials provided."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("[✓] Telegram notification sent successfully")
        else:
            print(f"[!] Telegram API error: {res.text}")
    except Exception as e:
        print(f"[x] Error sending Telegram message: {e}")


def check_sih_status():
    """
    Checks if SIH portal is truly online and serving the portal
    (not 403 Forbidden / 502 Bad Gateway / Maintenance page).
    Returns (is_online, status_description).
    """
    try:
        # Check with 15s timeout
        response = requests.get(
            SIH_URL,
            headers=HEADERS,
            timeout=15,
            verify=False,
            allow_redirects=True
        )

        status_code = response.status_code
        content = response.text.lower()

        # Check for typical gateway errors or maintenance
        if status_code == 403 or "403 forbidden" in content or "application-gateway" in content:
            return False, f"HTTP {status_code} - Azure Gateway Error / 403 Forbidden"

        if status_code in (500, 502, 503, 504):
            return False, f"HTTP {status_code} - Server Error"

        if "under maintenance" in content or "site is under maintenance" in content:
            return False, f"HTTP {status_code} - Site Under Maintenance"

        # Check for successful response
        if status_code == 200:
            # Check if it has actual portal keywords
            if "hackathon" in content or "sih" in content or "login" in content or "submission" in content:
                return True, "HTTP 200 OK - SIH Website is LIVE and responding!"
            # Even if keywords differ, 200 with normal HTML indicates online
            return True, f"HTTP 200 OK - Page returned {len(response.text)} bytes"

        return False, f"Unexpected HTTP status: {status_code}"

    except requests.exceptions.Timeout:
        return False, "Connection Timed Out"
    except requests.exceptions.ConnectionError as e:
        return False, f"Connection Failed: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def monitor_continuous(interval_seconds: int = 60, max_iterations: int = None):
    """
    Monitors SIH website continuously every `interval_seconds`.
    When online, sends urgent notifications to phone every 60 seconds.
    """
    iteration = 0
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting continuous monitor (interval: {interval_seconds}s)...")

    while True:
        iteration += 1
        now_str = time.strftime('%Y-%m-%d %H:%M:%S')
        is_online, details = check_sih_status()
        print(f"[{now_str}] Check #{iteration}: {details}")

        if is_online:
            title = "SIH WEBSITE IS ONLINE!"
            message = (
                f"🚨 SIH Portal is LIVE and responding!\n\n"
                f"Status: {details}\n"
                f"Link: {SIH_URL}\n\n"
                f"👉 Submit your PPT now! (Alert #{iteration})"
            )
            print(f">>> [{now_str}] SITE IS ONLINE! Sending urgent notification to phone...")
            send_ntfy_notification(title, message, priority="urgent")
            send_telegram_notification(f"<b>{title}</b>\n\n{message}")
        else:
            print(f"[{now_str}] Site is down/gateway error. Waiting {interval_seconds}s...")

        if max_iterations and iteration >= max_iterations:
            print(f"Reached max iterations ({max_iterations}). Exiting.")
            break

        time.sleep(interval_seconds)


def main():
    if "--test" in sys.argv:
        print(">>> Sending TEST notification to verify phone reception...")
        title = "SIH Alert Test Notification"
        message = (
            "If you received this, phone notifications are working perfectly!\n"
            "You will be alerted every 60 seconds the moment SIH portal is online."
        )
        send_ntfy_notification(title, message, priority="urgent")
        send_telegram_notification(f"<b>{title}</b>\n\n{message}")
        print(">>> Test notification sent.")
        return

    # Interval in seconds (default: 60)
    interval = int(os.environ.get("CHECK_INTERVAL", "60"))
    # Max iterations per run (e.g., 20 checks for 20 minutes before GitHub Actions rotates)
    max_iter = int(os.environ.get("MAX_ITERATIONS", "0")) or None

    monitor_continuous(interval_seconds=interval, max_iterations=max_iter)


if __name__ == "__main__":
    main()
