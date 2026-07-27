export const verifyTurnstile = async ({ token, secret, remoteIp, expectedHostname }) => {
  if (!secret) return { success: false, errorCodes: ["missing-secret"] };
  const body = new URLSearchParams({ secret, response: token || "" });
  if (remoteIp) body.set("remoteip", remoteIp);
  const response = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body
  });
  const result = await response.json();
  const hostnameOk = !expectedHostname || !result.hostname || result.hostname === expectedHostname;
  return {
    success: Boolean(result.success && hostnameOk),
    hostname: result.hostname || "",
    action: result.action || "",
    errorCodes: result["error-codes"] || (hostnameOk ? [] : ["hostname-mismatch"])
  };
};
