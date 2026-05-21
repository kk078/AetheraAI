import type { Env } from "./types";

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

/**
 * Authentication gate for /api/* (off unless API_AUTH_ENABLED). Cloudflare
 * Access is the primary login at the edge; this is defense-in-depth.
 */
export function requestAuthorized(env: Env, path: string, method: string, authHeader: string | null): boolean {
  if (!authEnabled(env)) return true;
  if (method.toUpperCase() === "OPTIONS") return true;
  if (!path.startsWith("/api/")) return true;
  if (PUBLIC_PATHS.has(path)) return true;
  const token = extractBearer(authHeader);
  if (!token) return false;
  return allowedKeys(env).some((k) => constantTimeEquals(token, k));
}
