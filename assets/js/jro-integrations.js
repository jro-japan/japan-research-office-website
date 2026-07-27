/**
 * Japan Research Office Web Operations v8.0
 * Turnstile, consent, GA4, Clarity, Sentry, form delivery, outbound events,
 * Core Web Vitals and client-error reporting.
 */
(() => {
  "use strict";

  const cfg = window.JRO_CONFIG || {};
  const hasValue = (value) => typeof value === "string" && value.trim() !== "";
  const storageKey = cfg.consentStorageKey || "jro_privacy_consent_v1";
  const forms = [...document.querySelectorAll("form[name='contact'], form[name='general-inquiry'], form[name='sample-request']")];
  const turnstileWidgets = new WeakMap();

  const safeJson = (value, fallback = null) => {
    try { return JSON.parse(value); } catch { return fallback; }
  };

  const loadScript = (src, attributes = {}) => new Promise((resolve, reject) => {
    const existing = [...document.scripts].find((script) => script.src === src);
    if (existing) {
      if (existing.dataset.loaded === "true") resolve(existing);
      else existing.addEventListener("load", () => resolve(existing), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    Object.entries(attributes).forEach(([key, value]) => script.setAttribute(key, value));
    script.addEventListener("load", () => {
      script.dataset.loaded = "true";
      resolve(script);
    }, { once: true });
    script.addEventListener("error", reject, { once: true });
    document.head.appendChild(script);
  });

  const defaultConsent = () => ({ analytics: false, behavior: false, decided: false });
  const readConsent = () => ({ ...defaultConsent(), ...(safeJson(localStorage.getItem(storageKey), {}) || {}) });
  const saveConsent = (consent) => localStorage.setItem(storageKey, JSON.stringify({ ...consent, decided: true, updatedAt: new Date().toISOString() }));

  const sendClientError = (payload) => {
    if (!cfg.errorEndpoint || !navigator.sendBeacon) return;
    try {
      navigator.sendBeacon(cfg.errorEndpoint, new Blob([JSON.stringify({
        ...payload,
        page: location.href,
        userAgent: navigator.userAgent,
        occurredAt: new Date().toISOString()
      })], { type: "application/json" }));
    } catch { /* reporting must never break the page */ }
  };

  window.addEventListener("error", (event) => sendClientError({
    type: "javascript_error",
    message: event.message || "Unknown JavaScript error",
    source: event.filename || "",
    line: event.lineno || 0,
    column: event.colno || 0
  }));

  window.addEventListener("unhandledrejection", (event) => sendClientError({
    type: "unhandled_rejection",
    message: String(event.reason?.message || event.reason || "Unhandled promise rejection"),
    stack: String(event.reason?.stack || "")
  }));

  const track = (eventName, parameters = {}) => {
    if (typeof window.gtag === "function") window.gtag("event", eventName, parameters);
  };

  const loadGA4 = async () => {
    if (!hasValue(cfg.ga4MeasurementId) || window.__jroGa4Loaded) return;
    window.__jroGa4Loaded = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function gtag(){ window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", cfg.ga4MeasurementId, {
      anonymize_ip: true,
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
      send_page_view: true
    });
    await loadScript(`https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(cfg.ga4MeasurementId)}`);
  };

  const loadClarity = async () => {
    if (!hasValue(cfg.clarityProjectId) || window.__jroClarityLoaded) return;
    window.__jroClarityLoaded = true;
    window.clarity = window.clarity || function clarity(){ (window.clarity.q = window.clarity.q || []).push(arguments); };
    await loadScript(`https://www.clarity.ms/tag/${encodeURIComponent(cfg.clarityProjectId)}`);
  };

  const loadSentry = async () => {
    if (!hasValue(cfg.sentryLoaderUrl) || window.__jroSentryLoaded) return;
    window.__jroSentryLoaded = true;
    window.sentryOnLoad = () => {
      if (!window.Sentry) return;
      window.Sentry.init({
        sendDefaultPii: false,
        tracesSampleRate: 0,
        replaysSessionSampleRate: 0,
        replaysOnErrorSampleRate: 0,
        environment: location.hostname === "japanresearchoffice.com" ? "production" : "preview",
        release: `jro-webops@${cfg.version || "8.0.0"}`
      });
    };
    await loadScript(cfg.sentryLoaderUrl, { crossorigin: "anonymous" });
  };

  const observeWebVitals = () => {
    if (!("PerformanceObserver" in window)) return;
    let clsValue = 0;
    let lcpValue = 0;
    let inpValue = 0;
    try {
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (!entry.hadRecentInput) clsValue += entry.value;
        }
      }).observe({ type: "layout-shift", buffered: true });
    } catch { /* unsupported */ }
    try {
      new PerformanceObserver((list) => {
        const entries = list.getEntries();
        if (entries.length) lcpValue = entries.at(-1).startTime;
      }).observe({ type: "largest-contentful-paint", buffered: true });
    } catch { /* unsupported */ }
    try {
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) inpValue = Math.max(inpValue, entry.duration || 0);
      }).observe({ type: "event", buffered: true, durationThreshold: 40 });
    } catch { /* unsupported */ }
    addEventListener("visibilitychange", () => {
      if (document.visibilityState !== "hidden") return;
      if (lcpValue) track("web_vital", { metric_name: "LCP", metric_value: Math.round(lcpValue), non_interaction: true });
      track("web_vital", { metric_name: "CLS", metric_value: Math.round(clsValue * 1000), non_interaction: true });
      if (inpValue) track("web_vital", { metric_name: "INP", metric_value: Math.round(inpValue), non_interaction: true });
    }, { once: true });
  };

  const applyConsent = async (consent) => {
    if (consent.analytics) await loadGA4();
    if (consent.behavior) await loadClarity();
    await loadSentry();
    if (consent.analytics) observeWebVitals();
  };

  const renderConsentDialog = (force = false) => {
    const current = readConsent();
    if (current.decided && !force) {
      applyConsent(current);
      return;
    }
    document.getElementById("jro-consent")?.remove();
    const panel = document.createElement("section");
    panel.id = "jro-consent";
    panel.className = "jro-consent";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-modal", "true");
    panel.setAttribute("aria-labelledby", "jro-consent-title");
    panel.innerHTML = `
      <div class="jro-consent__inner">
        <h2 id="jro-consent-title">Privacy choices</h2>
        <p>Essential security and form functions always run. With your permission, we also use analytics and session-behaviour tools to improve this website.</p>
        <div class="jro-consent__options" hidden>
          <label><input type="checkbox" data-consent="analytics"> Analytics (Google Analytics 4)</label>
          <label><input type="checkbox" data-consent="behavior"> Behaviour analytics (Microsoft Clarity)</label>
        </div>
        <div class="jro-consent__actions">
          <button type="button" class="btn" data-action="reject">Essential only</button>
          <button type="button" class="btn" data-action="customize">Customize</button>
          <button type="button" class="btn btn-primary" data-action="accept">Accept all</button>
          <button type="button" class="btn btn-primary" data-action="save" hidden>Save choices</button>
        </div>
        <p class="jro-consent__links"><a href="/privacy.html">Privacy Policy</a></p>
      </div>`;
    document.body.appendChild(panel);
    const options = panel.querySelector(".jro-consent__options");
    const save = panel.querySelector("[data-action='save']");
    const customize = panel.querySelector("[data-action='customize']");
    panel.querySelector("[data-consent='analytics']").checked = current.analytics;
    panel.querySelector("[data-consent='behavior']").checked = current.behavior;
    const finish = (consent) => {
      saveConsent(consent);
      panel.remove();
      applyConsent({ ...consent, decided: true });
    };
    panel.querySelector("[data-action='accept']").addEventListener("click", () => finish({ analytics: true, behavior: true }));
    panel.querySelector("[data-action='reject']").addEventListener("click", () => finish({ analytics: false, behavior: false }));
    customize.addEventListener("click", () => {
      options.hidden = false;
      save.hidden = false;
      customize.hidden = true;
    });
    save.addEventListener("click", () => finish({
      analytics: panel.querySelector("[data-consent='analytics']").checked,
      behavior: panel.querySelector("[data-consent='behavior']").checked
    }));
    panel.querySelector("button")?.focus();
  };

  const addPrivacySettingsButton = () => {
    if (document.getElementById("jro-privacy-settings")) return;
    const button = document.createElement("button");
    button.id = "jro-privacy-settings";
    button.className = "jro-privacy-settings";
    button.type = "button";
    button.textContent = "Privacy settings";
    button.addEventListener("click", () => renderConsentDialog(true));
    document.body.appendChild(button);
  };

  const renderTurnstile = async () => {
    if (!forms.length || !hasValue(cfg.turnstileSiteKey)) return;
    await loadScript("https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit");
    if (!window.turnstile) throw new Error("Turnstile failed to load.");
    forms.forEach((form) => {
      let host = form.querySelector("[data-jro-turnstile]");
      if (!host) {
        host = document.createElement("div");
        host.className = "jro-turnstile";
        host.dataset.jroTurnstile = "true";
        const status = document.createElement("p");
        status.className = "jro-form-status";
        status.dataset.jroTurnstileStatus = "true";
        status.setAttribute("aria-live", "polite");
        const submit = form.querySelector("button[type='submit'], input[type='submit']");
        submit?.before(host, status);
      }
      const widgetId = window.turnstile.render(host, {
        sitekey: cfg.turnstileSiteKey,
        theme: "auto",
        size: "flexible",
        callback: () => {
          const status = form.querySelector("[data-jro-turnstile-status]");
          if (status) status.textContent = "";
        },
        "expired-callback": () => {
          const status = form.querySelector("[data-jro-turnstile-status]");
          if (status) status.textContent = "Security verification expired. Please try again.";
        },
        "error-callback": () => {
          const status = form.querySelector("[data-jro-turnstile-status]");
          if (status) status.textContent = "Security verification could not load. Please refresh the page or contact us by email.";
        }
      });
      turnstileWidgets.set(form, widgetId);
    });
  };

  const formPayload = (form) => {
    const data = Object.fromEntries(new FormData(form).entries());
    return {
      ...data,
      formName: data["form-name"] || form.name || "contact",
      sourcePage: location.href,
      referrer: document.referrer || "",
      submittedAt: new Date().toISOString()
    };
  };

  const bindForms = () => {
    forms.forEach((form) => {
      if (form.dataset.jroWebopsReady === "true") return;
      form.dataset.jroWebopsReady = "true";
      form.action = cfg.formEndpoint || "/.netlify/functions/submit-form";
      form.addEventListener("submit", async (event) => {
        if (event.defaultPrevented) return;
        const token = form.querySelector("[name='cf-turnstile-response']")?.value || "";
        if (cfg.turnstileRequired && hasValue(cfg.turnstileSiteKey) && !token) {
          event.preventDefault();
          const status = form.querySelector("[data-jro-turnstile-status]");
          if (status) status.textContent = "Please complete the security verification.";
          return;
        }
        event.preventDefault();
        const submit = form.querySelector("button[type='submit'], input[type='submit']");
        const originalText = submit?.textContent;
        if (submit) {
          submit.disabled = true;
          submit.textContent = "Sending…";
        }
        let result;
        try {
          const response = await fetch(cfg.formEndpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json", "Accept": "application/json" },
            body: JSON.stringify(formPayload(form))
          });
          result = await response.json().catch(() => ({}));
          if (!response.ok) throw new Error(result.message || `Submission failed (${response.status})`);
          track("form_submit", { form_name: form.name || "contact", service: form.elements.service?.value || "" });
          track("generate_lead", { form_name: form.name || "contact" });
          location.assign(result.redirect || "/thank-you.html");
        } catch (error) {
          window.Sentry?.captureException?.(error);
          sendClientError({ type: "form_submission_failure", message: error.message, formName: form.name || "contact" });
          track("form_submit_error", { form_name: form.name || "contact", error_message: error.message });
          let status = form.querySelector("[data-jro-submit-status]");
          if (!status) {
            status = document.createElement("p");
            status.dataset.jroSubmitStatus = "true";
            status.className = "jro-form-status jro-form-status--error";
            status.setAttribute("role", "alert");
            submit?.before(status);
          }
          const email = cfg.contactEmail || "hiroaki@japanresearchoffice.com";
          status.innerHTML = `We could not send your inquiry. Please try again or email <a href="mailto:${email}">${email}</a>.`;
          const widgetId = turnstileWidgets.get(form);
          if (widgetId !== undefined && window.turnstile) window.turnstile.reset(widgetId);
          if (submit) {
            submit.disabled = false;
            submit.textContent = originalText || "Submit";
          }
        }
      });
    });
  };

  const bindOutboundTracking = () => {
    document.addEventListener("click", (event) => {
      const link = event.target.closest("a[href]");
      if (!link) return;
      const url = new URL(link.href, location.href);
      if (url.origin === location.origin || ["mailto:", "tel:"].includes(url.protocol)) return;
      track("click", { event_category: "outbound", link_url: url.href, link_domain: url.hostname, link_text: (link.textContent || "").trim().slice(0, 100) });
    });
  };

  const init = async () => {
    addPrivacySettingsButton();
    bindOutboundTracking();
    bindForms();
    if (/^404\b/i.test(document.title)) track("page_not_found", { page_location: location.href });
    await loadSentry().catch((error) => sendClientError({ type: "sentry_load_error", message: error.message }));
    renderConsentDialog(false);
    await renderTurnstile().catch((error) => {
      sendClientError({ type: "turnstile_load_error", message: error.message });
      forms.forEach((form) => {
        const status = form.querySelector("[data-jro-turnstile-status]");
        if (status) status.textContent = "Security verification could not load. Please refresh the page or contact us by email.";
      });
    });
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
