import { describe, it, expect } from "vitest";
import { verifyAccessJwt } from "../src/access";

const TEAM = "aetheraonline.cloudflareaccess.com";
const AUD = "8719a614a2aecd72bef4d3d063a95f8999e9345297f5f13982400cb74f69da56";
const env: any = { ACCESS_TEAM_DOMAIN: TEAM, ACCESS_AUD: AUD };

function jwt(payload: any, header: any = { alg: "RS256", kid: "k1" }) {
  const b = (o: any) =>
    btoa(JSON.stringify(o)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return `${b(header)}.${b(payload)}.AA`; // signature never reached for these cases
}

const future = Math.floor(Date.now() / 1000) + 3600;
const past = Math.floor(Date.now() / 1000) - 3600;

describe("verifyAccessJwt claim checks (no network)", () => {
  it("false when team domain / aud not configured", async () => {
    expect(await verifyAccessJwt({} as any, jwt({ iss: `https://${TEAM}`, aud: [AUD], exp: future }))).toBe(false);
  });
  it("false for null / malformed token", async () => {
    expect(await verifyAccessJwt(env, null)).toBe(false);
    expect(await verifyAccessJwt(env, "not.a")).toBe(false);
  });
  it("false for wrong issuer", async () => {
    expect(await verifyAccessJwt(env, jwt({ iss: "https://evil.cloudflareaccess.com", aud: [AUD], exp: future }))).toBe(false);
  });
  it("false for wrong audience", async () => {
    expect(await verifyAccessJwt(env, jwt({ iss: `https://${TEAM}`, aud: ["other"], exp: future }))).toBe(false);
  });
  it("false for expired token", async () => {
    expect(await verifyAccessJwt(env, jwt({ iss: `https://${TEAM}`, aud: [AUD], exp: past }))).toBe(false);
  });
  it("false for non-RS256 / missing kid", async () => {
    expect(await verifyAccessJwt(env, jwt({ iss: `https://${TEAM}`, aud: [AUD], exp: future }, { alg: "none" }))).toBe(false);
  });
});
