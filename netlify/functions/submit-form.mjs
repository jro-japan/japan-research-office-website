import { jsonResponse, htmlResponse, parseEventBody, wantsHtml } from "./_shared/http.mjs";
import { verifyTurnstile } from "./_shared/turnstile.mjs";
import { upsertHubSpotContact } from "./_shared/hubspot.mjs";
import { sendGoogleWebhook } from "./_shared/google-webhook.mjs";
import { persistNetlifyForm } from "./_shared/netlify-forms.mjs";

const allowedForms = new Set(["contact", "general-inquiry", "sample-request"]);
const trim = (value, max = 5000) => String(value ?? "").trim().slice(0, max);
const validEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

const normalizedSubmission = (input) => ({
  formName: trim(input.formName || input["form-name"] || "contact", 80),
  name: trim(input.name, 200),
  company: trim(input.company || input.company_name, 300),
  email: trim(input.email, 320).toLowerCase(),
  service: trim(input.service, 300),
  message: trim(input.message || input["project-details"] || input.project_details, 10000),
  "privacy-consent": trim(input["privacy-consent"] || input.privacyConsent, 30),
  "cf-turnstile-response": trim(input["cf-turnstile-response"] || input.turnstileToken, 4096),
  "bot-field": trim(input["bot-field"], 200),
  sourcePage: trim(input.sourcePage, 1000),
  referrer: trim(input.referrer, 1000),
  submittedAt: trim(input.submittedAt || new Date().toISOString(), 80)
});

export const handler = async (event) => {
  const contactEmail = process.env.CONTACT_EMAIL || "hiroaki@japanresearchoffice.com";
  if (event.httpMethod !== "POST") return jsonResponse(405, { ok: false, message: "Method not allowed." }, { Allow: "POST" });
  let submission;
  try { submission = normalizedSubmission(parseEventBody(event)); }
  catch (error) { return jsonResponse(400, { ok: false, message: "Invalid request body." }); }

  if (submission["bot-field"]) {
    return wantsHtml(event)
      ? { statusCode: 303, headers: { Location: "/thank-you.html", "Cache-Control": "no-store" }, body: "" }
      : jsonResponse(200, { ok: true, redirect: "/thank-you.html" });
  }

  const problems = [];
  if (!allowedForms.has(submission.formName)) problems.push("Unknown form.");
  if (!submission.name) problems.push("Name is required.");
  if (!validEmail(submission.email)) problems.push("A valid email is required.");
  if (!submission.message) problems.push("Project details are required.");
  if (submission["privacy-consent"] !== "agreed") problems.push("Privacy consent is required.");
  if (problems.length) {
    const message = problems.join(" ");
    return wantsHtml(event) ? htmlResponse(400, "Please review your inquiry", message, contactEmail) : jsonResponse(400, { ok: false, message });
  }

  const turnstileRequired = String(process.env.TURNSTILE_REQUIRED || "false").toLowerCase() === "true";
  if (turnstileRequired) {
    if (!process.env.TURNSTILE_SECRET_KEY) return jsonResponse(503, { ok: false, message: "Security verification is not configured." });
    const remoteIp = event.headers?.["x-nf-client-connection-ip"] || event.headers?.["x-forwarded-for"]?.split(",")[0]?.trim() || "";
    const expectedHostname = process.env.SITE_HOSTNAME || "japanresearchoffice.com";
    const verification = await verifyTurnstile({
      token: submission["cf-turnstile-response"],
      secret: process.env.TURNSTILE_SECRET_KEY,
      remoteIp,
      expectedHostname
    });
    if (!verification.success) {
      const message = "Security verification failed. Please refresh the page and try again.";
      return wantsHtml(event) ? htmlResponse(400, "Security verification failed", message, contactEmail) : jsonResponse(400, { ok: false, message, codes: verification.errorCodes });
    }
  }

  const clean = { ...submission };
  delete clean["cf-turnstile-response"];
  delete clean["bot-field"];
  const tasks = [
    persistNetlifyForm(clean, process.env.SITE_URL || "https://japanresearchoffice.com"),
    sendGoogleWebhook(clean, process.env.GOOGLE_APPS_SCRIPT_WEBHOOK_URL, process.env.GOOGLE_APPS_SCRIPT_SHARED_SECRET),
    upsertHubSpotContact(clean, process.env.HUBSPOT_PRIVATE_APP_TOKEN)
  ];
  const results = await Promise.allSettled(tasks);
  const failures = results.filter((item) => item.status === "rejected");
  failures.forEach((failure) => console.error("Integration failure:", failure.reason));

  // Netlify Forms is the minimum durable record. Fail the request only if it failed.
  if (results[0].status === "rejected") {
    const message = "We could not record your inquiry. Please try again or contact us by email.";
    return wantsHtml(event) ? htmlResponse(502, "Inquiry not sent", message, contactEmail) : jsonResponse(502, { ok: false, message });
  }

  return wantsHtml(event)
    ? { statusCode: 303, headers: { Location: "/thank-you.html", "Cache-Control": "no-store" }, body: "" }
    : jsonResponse(200, { ok: true, redirect: "/thank-you.html", integrations: results.map((item) => item.status) });
};
