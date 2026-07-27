const endpoint = "https://api.hubapi.com/crm/v3/objects/contacts";

const splitName = (name = "") => {
  const parts = String(name).trim().split(/\s+/).filter(Boolean);
  if (parts.length <= 1) return { firstname: parts[0] || "", lastname: "" };
  return { firstname: parts.slice(0, -1).join(" "), lastname: parts.at(-1) };
};

export const upsertHubSpotContact = async (submission, token) => {
  if (!token) return { skipped: true, reason: "missing-token" };
  const name = splitName(submission.name);
  const properties = {
    email: submission.email,
    firstname: name.firstname,
    lastname: name.lastname,
    company: submission.company || "",
    jro_service: submission.service || "",
    jro_inquiry_message: submission.message || submission["project-details"] || "",
    jro_form_name: submission.formName || "",
    jro_source_page: submission.sourcePage || "",
    jro_privacy_consent: String(submission["privacy-consent"] || submission.privacyConsent || "")
  };
  const headers = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
  let response = await fetch(`${endpoint}/${encodeURIComponent(submission.email)}?idProperty=email`, {
    method: "PATCH", headers, body: JSON.stringify({ properties })
  });
  if (response.status === 404) {
    response = await fetch(endpoint, { method: "POST", headers, body: JSON.stringify({ properties }) });
  }
  const text = await response.text();
  if (!response.ok) throw new Error(`HubSpot ${response.status}: ${text.slice(0, 500)}`);
  return text ? JSON.parse(text) : { ok: true };
};
