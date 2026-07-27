export const jsonResponse = (statusCode, body, extraHeaders = {}) => ({
  statusCode,
  headers: {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    ...extraHeaders
  },
  body: JSON.stringify(body)
});

export const htmlResponse = (statusCode, title, message, email = "hiroaki@japanresearchoffice.com") => ({
  statusCode,
  headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
  body: `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(title)}</title></head><body><main style="max-width:680px;margin:4rem auto;padding:1rem;font:16px/1.6 system-ui"><h1>${escapeHtml(title)}</h1><p>${escapeHtml(message)}</p><p><a href="mailto:${escapeHtml(email)}">${escapeHtml(email)}</a></p><p><a href="/contact.html">Return to the contact page</a></p></main></body></html>`
});

export const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
}[char]));

export const parseEventBody = (event) => {
  const raw = event.isBase64Encoded ? Buffer.from(event.body || "", "base64").toString("utf8") : (event.body || "");
  const type = String(event.headers?.["content-type"] || event.headers?.["Content-Type"] || "").split(";")[0].trim();
  if (type === "application/json") return JSON.parse(raw || "{}");
  if (type === "application/x-www-form-urlencoded" || !type) return Object.fromEntries(new URLSearchParams(raw));
  throw new Error(`Unsupported content type: ${type}`);
};

export const wantsHtml = (event) => String(event.headers?.accept || event.headers?.Accept || "").includes("text/html");
