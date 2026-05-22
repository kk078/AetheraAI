import type { Env } from "./types";

// Cloudflare Access JWT verification. When the app is behind Access, every
// request that reaches the Worker carries a signed `Cf-Access-Jwt-Assertion`
// header. We verify it against the team's public keys (JWKS) so the Worker
// trusts Access as the login — no API key needs to live in the browser.

interface Jwk {
  kid: string;
  kty: string;
  n: string;
  e: string;
  alg?: string;
}

interface JwksCache {
  keys: Map<string, CryptoKey>;
  fetchedAt: number;
}

const JWKS_TTL_MS = 60 * 60 * 1000; // refresh hourly
let cache: JwksCache | null = null;

function b64urlToBytes(s: string): Uint8Array {
  const b64 = s.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(s.length / 4) * 4, "=");
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function decodeJson(segment: string): any {
  return JSON.parse(new TextDecoder().decode(b64urlToBytes(segment)));
}

async function loadKeys(teamDomain: string): Promise<Map<string, CryptoKey>> {
  if (cache && Date.now() - cache.fetchedAt < JWKS_TTL_MS) return cache.keys;
  const url = `https://${teamDomain}/cdn-cgi/access/certs`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`JWKS fetch failed: ${res.status}`);
  const body = (await res.json()) as { keys: Jwk[] };
  const keys = new Map<string, CryptoKey>();
  for (const jwk of body.keys ?? []) {
    try {
      const key = await crypto.subtle.importKey(
        "jwk",
        { kty: jwk.kty, n: jwk.n, e: jwk.e, alg: "RS256", ext: true },
        { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
        false,
        ["verify"],
      );
      keys.set(jwk.kid, key);
    } catch {
      /* skip malformed key */
    }
  }
  cache = { keys, fetchedAt: Date.now() };
  return keys;
}

/**
 * Verify a Cloudflare Access JWT: RS256 signature against the team JWKS,
 * audience contains the app AUD, issuer matches the team domain, not expired.
 * Returns false on any failure. Never throws.
 */
export async function verifyAccessJwt(env: Env, token: string | null): Promise<boolean> {
  const teamDomain = env.ACCESS_TEAM_DOMAIN;
  const aud = env.ACCESS_AUD;
  if (!teamDomain || !aud || !token) return false;
  const parts = token.split(".");
  if (parts.length !== 3) return false;
  try {
    const header = decodeJson(parts[0]);
    const payload = decodeJson(parts[1]);
    if (header.alg !== "RS256" || !header.kid) return false;

    // Claims: issuer, audience, expiry.
    if (payload.iss !== `https://${teamDomain}`) return false;
    const auds: string[] = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
    if (!auds.includes(aud)) return false;
    const now = Math.floor(Date.now() / 1000);
    if (typeof payload.exp === "number" && payload.exp < now) return false;
    if (typeof payload.nbf === "number" && payload.nbf > now + 60) return false;

    let keys = await loadKeys(teamDomain);
    let key = keys.get(header.kid);
    if (!key) {
      // Unknown kid — keys may have rotated; force a refresh once.
      cache = null;
      keys = await loadKeys(teamDomain);
      key = keys.get(header.kid);
    }
    if (!key) return false;

    const data = new TextEncoder().encode(`${parts[0]}.${parts[1]}`);
    const sig = b64urlToBytes(parts[2]);
    return await crypto.subtle.verify({ name: "RSASSA-PKCS1-v1_5" }, key, sig, data);
  } catch {
    return false;
  }
}
