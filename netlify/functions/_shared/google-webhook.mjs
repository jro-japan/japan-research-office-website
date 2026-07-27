export const sendGoogleWebhook = async (submission, url, secret, type = "form_submission") => {
  if (!url) return { skipped: true, reason: "missing-url" };
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "text/plain;charset=utf-8" },
    body: JSON.stringify({ type, secret: secret || "", submission })
  });
  const text = await response.text();
  if (!response.ok) throw new Error(`Google webhook ${response.status}: ${text.slice(0, 500)}`);
  const result = text ? JSON.parse(text) : { ok: true };
  if (result && result.ok === false) throw new Error(`Google webhook rejected the request: ${result.error || "unknown error"}`);
  return result;
};
