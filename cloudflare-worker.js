/**
 * Cloudflare Worker for SIH Website Monitoring
 * Runs 24/7 on Cloudflare's edge network for free (100k requests/day)
 * Triggers every 1 minute via Cron Trigger: * * * * *
 */

// Match your ntfy topic name
const NTFY_TOPIC = "sih_status_alert_psp";
const SIH_URL = "https://sih.gov.in/";

export default {
  // Handles scheduled cron trigger (every 1 minute)
  async scheduled(event, env, ctx) {
    ctx.waitUntil(checkSIH(false));
  },

  // Allows testing & manual status check in browser
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // If you visit /test, it triggers a test push notification to phone
    if (url.pathname === "/test") {
      await sendNtfyNotification(
        "[Cloudflare] Test Ping",
        "Test successful! Cloudflare Worker is active and monitoring SIH every 60 seconds.",
        "default"
      );
      return new Response("Test notification sent to your phone via ntfy!", {
        headers: { "Content-Type": "text/plain" },
      });
    }

    const result = await checkSIH(true);
    return new Response(JSON.stringify(result, null, 2), {
      headers: { "Content-Type": "application/json" },
    });
  },
};

async function checkSIH(isManual = false) {
  const timestamp = new Date().toISOString();
  try {
    const response = await fetch(SIH_URL, {
      method: "GET",
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      },
    });

    const status = response.status;
    const body = await response.text();
    const lowerBody = body.toLowerCase();

    // Azure gateway 403 / maintenance / server errors
    const isGatewayError =
      status === 403 ||
      lowerBody.includes("403 forbidden") ||
      lowerBody.includes("application-gateway");
    const isServerError = [500, 502, 503, 504].includes(status);
    const isMaintenance = lowerBody.includes("under maintenance");

    if (isGatewayError || isServerError || isMaintenance) {
      console.log(`[${timestamp}] SIH is DOWN (Status ${status})`);
      return {
        online: false,
        status,
        message: "Site still down (Azure Gateway / 403 / Maintenance)",
        checkedAt: timestamp,
      };
    }

    if (status === 200) {
      console.log(`[${timestamp}] SIH is ONLINE! Sending push notification...`);
      await sendNtfyNotification(
        "[Cloudflare] SIH WEBSITE IS ONLINE!",
        `SIH Portal is back online!\n\nLink: ${SIH_URL}\n\nSubmit your PPT now!`,
        "urgent"
      );
      return {
        online: true,
        status,
        message: "SIH is LIVE! Notification dispatched to phone.",
        checkedAt: timestamp,
      };
    }

    return {
      online: false,
      status,
      message: `Unexpected status code: ${status}`,
      checkedAt: timestamp,
    };
  } catch (err) {
    console.error(`[${timestamp}] Fetch error: ${err.message}`);
    return { online: false, error: err.message, checkedAt: timestamp };
  }
}

async function sendNtfyNotification(title, message, priority = "urgent") {
  const ntfyUrl = `https://ntfy.sh/${NTFY_TOPIC}`;
  await fetch(ntfyUrl, {
    method: "POST",
    headers: {
      Title: title,
      Priority: priority,
      Tags: "tada,rotating_light,white_check_mark",
      Click: SIH_URL,
      Actions: `view, Open SIH Portal, ${SIH_URL}`,
    },
    body: message,
  });
}
