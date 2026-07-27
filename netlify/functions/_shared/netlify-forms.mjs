export const persistNetlifyForm = async (submission, siteUrl) => {
  if (!siteUrl) return { skipped: true, reason: "missing-site-url" };
  const form = new URLSearchParams();
  const formName = submission.formName || submission["form-name"] || "contact";
  form.set("form-name", formName);
  for (const [key, value] of Object.entries(submission)) {
    if (value === undefined || value === null || typeof value === "object") continue;
    form.set(key, String(value));
  }
  const response = await fetch(`${siteUrl.replace(/\/$/, "")}/`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
    redirect: "manual"
  });
  if (response.status >= 400) throw new Error(`Netlify Forms ${response.status}`);
  return { ok: true, status: response.status };
};
