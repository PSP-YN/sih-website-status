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
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "sih_status_alert_psp")
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


def send_ntfy_notification(title: str, message: str, priority: str = "urgent", tags: str = "white_check_mark,tada"):
    """Send free instant push notification via ntfy.sh to phone."""
    try:
        url = f"https://ntfy.sh/{NTFY_TOPIC}"
        # HTTP headers must be ASCII-safe
        safe_title = title.encode("ascii", "ignore").decode("ascii").strip()
        headers = {
            "Title": safe_title or "SIH Status Alert",
            "Priority": priority,  # max/urgent causes loud alarm on phone
            "Tags": tags,
            "Click": SIH_URL,
            "Actions": f"view, Open SIH Portal, {SIH_URL}",
        }
        res = requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=10)
        if res.status_code == 200:
            print(f"[✓] Push notification successfully sent via ntfy.sh/{NTFY_TOPIC} ({tags})")
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


def monitor_continuous(
    interval_seconds: int = 60,
    max_iterations: int = None,
    heartbeat_every: int = 0
):
    """
    Monitors SIH website continuously every `interval_seconds`.
    - Only sends notifications when the status CHANGES (e.g. DOWN -> UP).
    - Avoids spamming notifications continuously when state hasn't changed.
    """
    iteration = 0
    last_state = None  # None: initial, True: online, False: offline
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting state-aware monitor (interval: {interval_seconds}s)...")
    print(f"[*] State change notifications only: You will NOT be spammed continuously.")

    while True:
        iteration += 1
        now_str = time.strftime('%Y-%m-%d %H:%M:%S')
        is_online, details = check_sih_status()

        # Check if state changed
        state_changed = (last_state is not None and is_online != last_state)
        first_run = (last_state is None)

        if is_online:
            if state_changed or first_run:
                title = "[SIH Monitor] SIH IS ONLINE!"
                message = (
                    f"🟢🟢 SIH Portal is LIVE and accessible!\n\n"
                    f"Status: {details}\n"
                    f"Link: {SIH_URL}\n\n"
                    f"👉 Submit your PPT now! (Detected at {now_str})"
                )
                print(f"\n>>> [{now_str}] *** STATUS ALERT: SITE IS ONLINE! ***")
                print(f">>> Details: {details}")
                print(f">>> Sending urgent notification to phone...")
                send_ntfy_notification(
                    title=title,
                    message=message,
                    priority="urgent",
                    tags="green_circle,white_check_mark,tada,rocket"
                )
                send_telegram_notification(f"<b>{title}</b>\n\n{message}")
            else:
                # Same state: silent check, just log to console
                print(f"[{now_str}] Check #{iteration}: ONLINE (No change, silent) - {details}")

        else:
            if state_changed:
                red_title = "[SIH Monitor] SIH WENT DOWN"
                red_message = (
                    f"🔴 SIH Portal is currently DOWN or inaccessible.\n\n"
                    f"Status: {details}\n"
                    f"Time: {now_str}\n\n"
                    f"⏳ Will sound full urgent alarm as soon as it goes live."
                )
                print(f"\n>>> [{now_str}] *** STATUS ALERT: SITE WENT DOWN! ***")
                print(f">>> Details: {details}")
                print(f">>> Sending alert to phone...")
                send_ntfy_notification(
                    title=red_title,
                    message=red_message,
                    priority="default",
                    tags="red_circle,warning,x"
                )
                send_telegram_notification(f"<b>{red_title}</b>\n\n{red_message}")
            elif first_run:
                print(f"[{now_str}] Check #{iteration}: DOWN ({details})")
                print(f"[*] Watching silently every {interval_seconds}s. Alarm will trigger only when it goes UP.")
            else:
                print(f"[{now_str}] Check #{iteration}: DOWN ({details}) - silent")

        # Optional periodic heartbeat (disabled by default)
        if heartbeat_every > 0 and iteration % heartbeat_every == 0 and not state_changed:
            status_text = "ONLINE 🟢" if is_online else "DOWN 🔴"
            send_ntfy_notification(
                title=f"[SIH Monitor] Heartbeat #{iteration}",
                message=f"Monitor is actively running. Current status: {status_text}",
                priority="low",
                tags="information_source"
            )

        last_state = is_online

        if max_iterations and iteration >= max_iterations:
            print(f"Reached max iterations ({max_iterations}). Exiting.")
            break

        time.sleep(interval_seconds)


def main():
    if "--test" in sys.argv:
        print(">>> Sending TEST notification to verify phone reception...")
        title = "[SIH Monitor] Test Notification"
        message = (
            "If you received this, phone notifications are working perfectly!\n"
            "You will be alerted immediately when SIH status changes."
        )
        send_ntfy_notification(title, message, priority="urgent")
        send_telegram_notification(f"<b>{title}</b>\n\n{message}")
        print(">>> Test notification sent.")
        return

    if "--once" in sys.argv:
        is_online, details = check_sih_status()
        print(f"Status: {'ONLINE' if is_online else 'DOWN'} ({details})")
        sys.exit(0 if is_online else 1)

    # Parse interval from env or --interval flag
    interval = int(os.environ.get("CHECK_INTERVAL", "60"))
    if "--interval" in sys.argv:
        try:
            idx = sys.argv.index("--interval")
            interval = int(sys.argv[idx + 1])
        except (ValueError, IndexError):
            pass

    max_iter = int(os.environ.get("MAX_ITERATIONS", "0")) or None
    heartbeat = int(os.environ.get("HEARTBEAT_EVERY", "0"))

    monitor_continuous(
        interval_seconds=interval,
        max_iterations=max_iter,
        heartbeat_every=heartbeat
    )


if __name__ == "__main__":
    main()
