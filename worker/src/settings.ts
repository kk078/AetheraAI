import type { Env } from "./types";

const SETTINGS_KEY = "app:settings";

const DEFAULT_SETTINGS = {
  default_specialist: "general",
  model_preference: "auto",
  response_style: "detailed",
  phi_detection_enabled: true,
  audit_logging_enabled: true,
  timezone: "UTC",
};

/** Read app settings from KV, merged over defaults. */
export async function getSettings(env: Env): Promise<Record<string, any>> {
  try {
    const raw = await env.CACHE.get(SETTINGS_KEY);
    return raw ? { ...DEFAULT_SETTINGS, ...JSON.parse(raw) } : { ...DEFAULT_SETTINGS };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

/** Merge updates into app settings and persist to KV. Returns the new settings. */
export async function updateSettings(env: Env, updates: Record<string, any>): Promise<Record<string, any>> {
  const current = await getSettings(env);
  const next = { ...current, ...updates };
  try {
    await env.CACHE.put(SETTINGS_KEY, JSON.stringify(next));
  } catch {
    /* persistence is best-effort */
  }
  return next;
}
