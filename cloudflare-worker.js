/**
 * Cloudflare Worker for SIH Website Monitoring
 * Runs 24/7 on Cloudflare's edge network for free (100k requests/day)
 * Triggers every 1 minute via Cron Trigger: * * * * *
 */

// Replace with your unique topic name
const NTFY_TOPIC = "sih_status_alert_psp";
const SIH_URL = "https://sih.gov.in/";

export default {
  // Handles scheduled cron trigger (every 1 minute)
  async scheduled(event, env, ctx) {
    ctx.waitUntil(checkSIH());
  },

  // Also allows testing via browser GET request
  async fetch(request, env, ctx) {
    const result = await checkSIH();
    return new Response(JSON.stringify(result, null, 2), {
      headers: { "Content-Type": "application/json" },
    });
  },
};

async function checkSIH() {
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

    // Check if site is still returning 403 or Azure gateway error
    const isGatewayError =
      status === 403 ||
      lowerBody.includes("403 forbidden") ||
      lowerBody.includes("application-gateway");
    const isServerError = [500, 502, 503, 504].includes(status);
    const isMaintenance = lowerBody.includes("under maintenance");

    if (isGatewayError || isServerError || isMaintenance) {
      console.log(`[${timestamp}] SIH is DOWN (Status ${status})`);
      return { online: false, status, message: "Site still down" };
    }

    if (status === 200) {
      console.log(`[${timestamp}] SIH is ONLINE! Sending push notification...`);
      await notifyPhone();
      return { online: true, status, message: "SIH is LIVE! Alert sent." };
    }

    return { online: false, status, message: `Unexpected status ${status}` };
  } catch (err) {
    console.error(`[${timestamp}] Fetch error: ${err.message}`);
    return { online: false, error: err.message };
  }
}

async function notifyPhone(details) {
  const ntfyUrl = `https://ntfy.sh/${NTFY_TOPIC}`;
  const message =
    `SIH Portal is back online!\n\nStatus: ${details}\nLink: ${SIH_URL}\n\nSubmit your PPT now before server gets overloaded!`;

  await fetch(ntfyUrl, {
    method: "POST",
    headers: {
      Title: "SIH WEBSITE IS ONLINE!",
      Priority: "urgent",
      Tags: "tada,rotating_light,white_check_mark",
      Click: SIH_URL,
      Actions: `view, Open SIH Portal, ${SIH_URL}`,
    },
    body: message,
  });
}
