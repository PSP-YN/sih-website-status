# SIH Website Uptime Monitor & Mobile Notification System

An automated monitor for **Smart India Hackathon (SIH)** ([https://sih.gov.in/](https://sih.gov.in/)).

It continuously checks whether the SIH portal is online (detecting and bypassing Azure Gateway 403 Forbidden, 502/503 errors, and maintenance pages) and **immediately rings your phone with an urgent push notification** when the website is live so you can submit your PPT right away.

Runs **100% free** in the cloud — **your laptop can be completely powered down**.

---

## 📱 Step 1: Set Up Phone Push Notifications (Takes 60 seconds)

We use **ntfy.sh**, a 100% free and open-source push notification service that requires **no account, no registration, and no phone number**.

1. **Install the App**:
   - **Android**: Install [ntfy from Google Play](https://play.google.com/store/apps/details?id=io.heckel.ntfy) or F-Droid.
   - **iOS**: Install [ntfy from the App Store](https://apps.apple.com/us/app/ntfy/id1625396347).
   - *(Alternative: Open `https://ntfy.sh` directly in Chrome/Safari on your phone and tap "Subscribe to topic" to get web push alerts).*

2. **Subscribe to your Topic**:
   - Open the app, tap `+` (Subscribe to topic).
   - Enter a topic name (e.g., `sih_status_alert_psp` or your own unique name).
   - Enable high-priority alerts / sound permissions so it rings loudly even if your phone is locked.

3. **Test It Right Now**:
   Run this in terminal to verify your phone rings:
   ```bash
   NTFY_TOPIC=sih_status_alert_psp python3 check_sih.py --test
   ```
   Or visit `https://ntfy.sh/sih_status_alert_psp` in any browser and send a test message.

---

## ☁️ Step 2: Run in the Cloud (Laptop Powered Down)

Choose whichever cloud method is easiest for you:

### Method A: GitHub Actions (Recommended)

GitHub Actions runs every 5 minutes in GitHub's cloud for free, polling every 30 seconds.

1. Create a new repository on [GitHub](https://github.com/new) (can be Public or Private).
2. Push this folder to your GitHub repo:
   ```bash
   git add .
   git commit -m "feat: SIH uptime monitor"
   git remote add origin https://github.com/<YOUR_USERNAME>/<YOUR_REPO>.git
   git branch -M main
   git push -u origin main
   ```
3. *(Optional)* If you changed the topic name from `sih_status_alert_psp`:
   - Go to your repo **Settings** → **Secrets and variables** → **Actions** → **Repository variables**.
   - Add variable `NTFY_TOPIC` with your chosen topic name.
   - *(Optional)* Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` under Secrets if you also want Telegram messages.
4. Go to the **Actions** tab on your GitHub repository:
   - Select **SIH Website Uptime Monitor** and click **Run workflow**.
   - From then on, GitHub's cloud scheduler will automatically run it 24/7.
   - **You can safely turn off your laptop.**

---

### Method B: Cloudflare Workers (Fastest 1-minute interval)

If you have a free Cloudflare account, you can deploy a worker that checks every single minute:

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com/) → **Workers & Pages** → **Create application** → **Create Worker**.
2. Paste the code from [`cloudflare-worker.js`](cloudflare-worker.js).
3. Update `const NTFY_TOPIC = "your_topic_name";` at the top.
4. Click **Deploy**.
5. Go to Worker **Settings** → **Triggers** → **Cron Triggers** → **Add Cron Trigger**:
   - Set expression to `* * * * *` (Every minute).
6. That's it! Cloudflare runs it every minute 24/7 for free.

---

### Method C: UptimeRobot Mobile App (Zero Code)

If you don't want to use GitHub or Cloudflare:
1. Install **UptimeRobot** from Google Play or App Store.
2. Create a free account.
3. Add a new monitor:
   - Type: **HTTP(s)**
   - URL: `https://sih.gov.in/`
   - Monitoring Interval: `5 minutes`
4. Since the site currently returns `403 Forbidden`, UptimeRobot will show it as **DOWN**.
5. As soon as SIH goes back up (HTTP 200), the app will send an alert sound directly to your phone.

---

## 🔍 Local Quick Run

To check current status locally anytime:
```bash
python3 check_sih.py
```
