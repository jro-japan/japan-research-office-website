// Email-only service: legacy public submission endpoint intentionally retired.
// Historical implementation remains in Git history. No external integrations run.
export const handler = async () => ({
  statusCode: 410,
  headers: {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store"},
  body: JSON.stringify({ok:false,message:"Web inquiry form retired. Please use the official email address listed on the Contact page."})
});
