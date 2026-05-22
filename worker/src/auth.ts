import type { Env } from "./types";
import { verifyAccessJwt } from "./access";

const PUBLIC_PATHS = new Set(["/api/health"]);

function authEnabled(env: Env): boolean {
  return ["1", "true", "yes", "on"].includes(String(env.API_AUTH_ENABLED ?? "").toLowerCase());
}

function allowedKeys(env: Env): string[] {
  return String(env.API_KEYS ?? "")
    .split(",")
    .map((k) => k.trim())
    .filter(Boolean);
}

function constantTimeEquals(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function extractBearer(header: string | null): string | null {
  if (!header) return null;
  const m = header.match(/^Bearer\s+(.+)$/i);
  return m ? m[1].trim() : null;
}

/** Bearer-key check (defense-in-depth / API clients). */
export function bearerAuthorized(env: Env, authHeader: string | null): boolean {
  const token = extractBearer(authHeader);
  if (!token) return false;
  return allowedKeys(env).some((k) => constantTimeEquals(token, k));
}

/**
 * Authentication gate for /api/* (off unless API_AUTH_ENABLED). Cloudflare
 * Access is the primary login: a valid `Cf-Access-Jwt-Assertion` header (signed
 * by the team's JWKS) authorizes the request, so the browser needs no key. A
 * valid bearer key is accepted as a fallback for API clients / curl.
 */
export async function authorizeRequest(
  env: Env,
  path: string,
  method: string,
  authHeader: string | null,
  accessJwt: string | null,
): Promise<boolean> {
  if (!authEnabled(env)) return true;
  if (method.toUpperCase() === "OPTIONS") return true;
  if (!path.startsWith("/api/")) return true;
  if (PUBLIC_PATHS.has(path)) return true;
  if (await verifyAccessJwt(env, accessJwt)) return true;
  return bearerAuthorized(env, authHeader);
}
