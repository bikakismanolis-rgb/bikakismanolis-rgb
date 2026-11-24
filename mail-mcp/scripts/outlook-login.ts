/**
 * One-off helper: gets a refresh token for an Outlook.com / Hotmail mailbox
 * using Microsoft's device-code flow. Run it on your own computer:
 *
 *   npm run outlook-login -- <azure-app-client-id>
 *
 * Then paste the printed refresh token into the account's `oauth.refreshToken`
 * inside MAIL_ACCOUNTS. The token is printed only to your terminal.
 */
import { OUTLOOK_SCOPE } from "../src/config.js";

const clientId = process.argv[2];
if (!clientId) {
  console.error("usage: npm run outlook-login -- <azure-app-client-id>");
  process.exit(1);
}

const base = "https://login.microsoftonline.com/consumers/oauth2/v2.0";
const form = (data: Record<string, string>) => ({
  method: "POST",
  headers: { "content-type": "application/x-www-form-urlencoded" },
  body: new URLSearchParams(data),
});

const start = (await (await fetch(`${base}/devicecode`, form({ client_id: clientId, scope: OUTLOOK_SCOPE }))).json()) as {
  device_code?: string;
  message?: string;
  interval?: number;
  expires_in?: number;
  error_description?: string;
};
if (!start.device_code) {
  console.error("Could not start login:", start.error_description ?? start);
  process.exit(1);
}
console.log(start.message);

const deadline = Date.now() + (start.expires_in ?? 900) * 1000;
while (Date.now() < deadline) {
  await new Promise((r) => setTimeout(r, (start.interval ?? 5) * 1000));
  const res = (await (
    await fetch(
      `${base}/token`,
      form({
        grant_type: "urn:ietf:params:oauth:grant-type:device_code",
        client_id: clientId,
        device_code: start.device_code,
      }),
    )
  ).json()) as { refresh_token?: string; error?: string; error_description?: string };
  if (res.refresh_token) {
    console.log("\nRefresh token (keep it secret):\n");
    console.log(res.refresh_token);
    process.exit(0);
  }
  if (res.error !== "authorization_pending" && res.error !== "slow_down") {
    console.error("Login failed:", res.error_description ?? res.error);
    process.exit(1);
  }
}
console.error("Login timed out.");
process.exit(1);
