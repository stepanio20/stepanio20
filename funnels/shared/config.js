/* ─────────────────────────────────────────────────────────────────────────
 * ONE place to turn on analytics for ALL 5 funnels + the dashboard.
 *
 * To go live with PostHog (5 min, free):
 *   1. Create a project at https://posthog.com  (EU region recommended for GDPR)
 *   2. Copy the "Project API Key" — it starts with  phc_
 *   3. Paste it below as POSTHOG_KEY and set POSTHOG_HOST to your region.
 *   4. Commit + redeploy. Every funnel starts tracking; the dashboard fills up.
 *
 * Until a real key is set, events log to the browser console + a local buffer
 * (so the built-in dashboard still shows this device's funnel for QA/demos).
 * ───────────────────────────────────────────────────────────────────────── */

window.POSTHOG_KEY  = 'phc_PASTE_YOUR_POSTHOG_PROJECT_KEY_HERE';
window.POSTHOG_HOST = 'https://eu.posthog.com';   /* or https://us.posthog.com */

window.ANALYTICS =
  (window.POSTHOG_KEY &&
   window.POSTHOG_KEY.indexOf('phc_') === 0 &&
   window.POSTHOG_KEY.indexOf('PASTE') === -1)
    ? { provider: 'posthog', key: window.POSTHOG_KEY, host: window.POSTHOG_HOST }
    : { provider: 'console' };
