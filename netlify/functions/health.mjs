import { jsonResponse } from "./_shared/http.mjs";
export const handler = async () => jsonResponse(200, {
  ok: true,
  service: "japan-research-office-website",
  version: "8.0.0",
  timestamp: new Date().toISOString()
});
