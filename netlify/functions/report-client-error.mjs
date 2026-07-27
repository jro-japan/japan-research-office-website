import { jsonResponse, parseEventBody } from "./_shared/http.mjs";
import { sendGoogleWebhook } from "./_shared/google-webhook.mjs";

export const handler = async (event) => {
  if (event.httpMethod !== "POST") return jsonResponse(405, { ok: false });
  let payload;
  try { payload = parseEventBody(event); }
  catch { return jsonResponse(400, { ok: false }); }
  const safe = {
    type: String(payload.type || "client_error").slice(0, 80),
    message: String(payload.message || "").slice(0, 2000),
    source: String(payload.source || "").slice(0, 1000),
    page: String(payload.page || "").slice(0, 1000),
    line: Number(payload.line || 0),
    column: Number(payload.column || 0),
    formName: String(payload.formName || "").slice(0, 100),
    occurredAt: String(payload.occurredAt || new Date().toISOString()).slice(0, 80)
  };
  console.error("Client report:", safe);
  try {
    await sendGoogleWebhook(safe, process.env.GOOGLE_APPS_SCRIPT_WEBHOOK_URL, process.env.GOOGLE_APPS_SCRIPT_SHARED_SECRET, "client_error");
  } catch (error) {
    console.error("Error webhook failure:", error);
  }
  return jsonResponse(202, { ok: true });
};
