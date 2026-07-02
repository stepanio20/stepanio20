/* Funnel analytics — the investor-data layer.
 * Every step fires a typed event. Wire ONE of the providers below and you get
 * the full funnel: view → quiz_start → quiz_step(n) → quiz_complete → lead → cta_click.
 *
 * Providers supported out of the box (set window.ANALYTICS before load):
 *   { provider: 'plausible' }                      // add Plausible script in <head>
 *   { provider: 'posthog', key: 'phc_...' }        // loads PostHog automatically
 *   { provider: 'ga', id: 'G-XXXX' }               // add gtag script in <head>
 *   { provider: 'custom', endpoint: '/api/track' } // POSTs JSON to your endpoint
 *   { provider: 'console' }                        // default: logs (dev)
 */
(function () {
  const cfg = window.ANALYTICS || { provider: 'console' };
  const VARIANT = (document.body && document.body.dataset.variant) || 'unknown';

  // one anonymous id per browser, so funnel steps join into a session
  function anonId() {
    let id = localStorage.getItem('idg_aid');
    if (!id) { id = 'a_' + Math.random().toString(36).slice(2) + Date.now().toString(36); localStorage.setItem('idg_aid', id); }
    return id;
  }
  const AID = anonId();

  if (cfg.provider === 'posthog' && cfg.key && !window.posthog) {
    // minimal PostHog snippet
    !function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.async=!0,p.src=s.api_host+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=function(){return u.toString(1)+".people (stub)"},o="init capture register register_once unregister opt_out_capturing has_opted_out_capturing opt_in_capturing reset isFeatureEnabled onFeatureFlags getFeatureFlag getFeatureFlagPayload reloadFeatureFlags group updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures getActiveMatchingSurveys getSurveys".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);
    window.posthog.init(cfg.key, { api_host: cfg.host || 'https://eu.posthog.com' });
  }

  function send(event, props) {
    const payload = Object.assign({ variant: VARIANT, aid: AID, ts: Date.now(), path: location.pathname }, props || {});
    // local ring buffer so the built-in dashboard renders this device's funnel with no backend
    try {
      const buf = JSON.parse(localStorage.getItem('idg_events') || '[]');
      buf.push({ event: event, variant: payload.variant, aid: payload.aid, ts: payload.ts });
      while (buf.length > 500) buf.shift();
      localStorage.setItem('idg_events', JSON.stringify(buf));
    } catch (e) {}
    try {
      switch (cfg.provider) {
        case 'plausible':
          if (window.plausible) window.plausible(event, { props: payload });
          break;
        case 'posthog':
          if (window.posthog) window.posthog.capture(event, payload);
          break;
        case 'ga':
          if (window.gtag) window.gtag('event', event, payload);
          break;
        case 'custom':
          navigator.sendBeacon
            ? navigator.sendBeacon(cfg.endpoint, JSON.stringify({ event, ...payload }))
            : fetch(cfg.endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ event, ...payload }), keepalive: true });
          break;
        default:
          console.log('[track]', event, payload);
      }
    } catch (e) { /* never break the funnel on analytics */ }
  }

  window.track = send;
  // auto-fire the page/funnel view once
  send('funnel_view');
})();
