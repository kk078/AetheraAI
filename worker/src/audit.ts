import type { Env } from "./types";
import { redact } from "./sensitivity";

/** Append a HIPAA audit entry to D1 (append-only table). PHI is redacted from
 * the resource/details before it is written. Best-effort: never throws. */
export async function logAudit(
  env: Env,
  e: { user_id?: string; action: string; resource?: string; details?: string; ip?: string; sensitivity?: string },
): Promise<void> {
  if (!env.DB) return;
  try {
    await env.DB.prepare(
      `INSERT INTO audit_log (id, user_id, action, resource, details, ip_address, sensitivity)
       VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)`,
    )
      .bind(
        crypto.randomUUID(),
        e.user_id ?? "",
        e.action,
        redact(e.resource ?? ""),
        redact(e.details ?? ""),
        e.ip ?? "",
        e.sensitivity ?? "",
      )
      .run();
  } catch {
    /* audit is best-effort; never block the request */
  }
}

/** Query recent audit entries (already redacted at write time). */
export async function queryAudit(env: Env, opts: { user_id?: string; limit?: number } = {}): Promise<any[]> {
  if (!env.DB) return [];
  const limit = Math.min(opts.limit ?? 100, 500);
  try {
    if (opts.user_id) {
      const res = await env.DB.prepare(
        "SELECT id, ts, user_id, action, resource, details, sensitivity FROM audit_log WHERE user_id = ?1 ORDER BY ts DESC LIMIT ?2",
      ).bind(opts.user_id, limit).all<any>();
      return res.results ?? [];
    }
    const res = await env.DB.prepare(
      "SELECT id, ts, user_id, action, resource, details, sensitivity FROM audit_log ORDER BY ts DESC LIMIT ?1",
    ).bind(limit).all<any>();
    return res.results ?? [];
  } catch {
    return [];
  }
}
