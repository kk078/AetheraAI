import type { Env } from "./types";

// CMS / regulatory sources fetched on a cron and stored in D1 (knowledge_updates).
const CMS_DATA_GOV = "https://data.cms.gov/data.json";
const FEDERAL_REGISTER =
  "https://www.federalregister.gov/api/v1/documents.json" +
  "?conditions[agencies][]=centers-for-medicare-medicaid-services&order=newest&per_page=20";

interface RawItem {
  source_key: string;
  title: string;
  summary?: string;
  url?: string;
  published_date?: string;
}

type FetchImpl = typeof fetch;

async function fetchCmsDataGov(f: FetchImpl): Promise<RawItem[]> {
  try {
    const res = await f(CMS_DATA_GOV, { headers: { "User-Agent": "AetheraAI-Worker/1.0" } });
    if (!res.ok) return [];
    const data: any = await res.json();
    const datasets: any[] = Array.isArray(data?.dataset) ? data.dataset : [];
    const cutoff = Date.now() - 14 * 86400000;
    const items: RawItem[] = [];
    for (const ds of datasets) {
      const modified = String(ds?.modified ?? "");
      const t = Date.parse(modified);
      if (!isNaN(t) && t < cutoff) continue;
      const id = ds?.identifier || ds?.title;
      if (!id) continue;
      items.push({
        source_key: String(id),
        title: String(ds?.title ?? "CMS Dataset Update"),
        summary: String(ds?.description ?? "").slice(0, 500),
        url: ds?.landingPage || String(id),
        published_date: modified,
      });
    }
    items.sort((a, b) => (b.published_date ?? "").localeCompare(a.published_date ?? ""));
    return items.slice(0, 25);
  } catch {
    return [];
  }
}

async function fetchFederalRegister(f: FetchImpl): Promise<RawItem[]> {
  try {
    const res = await f(FEDERAL_REGISTER, { headers: { "User-Agent": "AetheraAI-Worker/1.0" } });
    if (!res.ok) return [];
    const data: any = await res.json();
    const results: any[] = Array.isArray(data?.results) ? data.results : [];
    return results.map((d) => ({
      source_key: String(d?.document_number ?? d?.id ?? ""),
      title: String(d?.title ?? "Untitled"),
      summary: String(d?.abstract ?? "").slice(0, 500),
      url: String(d?.html_url ?? ""),
      published_date: String(d?.publication_date ?? ""),
    }));
  } catch {
    return [];
  }
}

/** Fetch all sources and insert new items into D1 (dedup via unique index). */
export async function checkUpdates(
  env: Env,
  fetchImpl: FetchImpl = fetch,
): Promise<{ new: number; by_source: Record<string, number> }> {
  if (!env.DB) return { new: 0, by_source: {} };
  const sources: Array<[string, () => Promise<RawItem[]>]> = [
    ["cms_data_gov", () => fetchCmsDataGov(fetchImpl)],
    ["federal_register", () => fetchFederalRegister(fetchImpl)],
  ];
  let total = 0;
  const bySource: Record<string, number> = {};
  for (const [key, fetcher] of sources) {
    try {
      const items = await fetcher();
      let n = 0;
      for (const it of items) {
        if (!it.source_key) continue;
        const res: any = await env.DB.prepare(
          `INSERT OR IGNORE INTO knowledge_updates
             (id, source, source_key, title, summary, url, category, published_date)
           VALUES (?1, ?2, ?3, ?4, ?5, ?6, 'healthcare_regulatory', ?7)`,
        )
          .bind(crypto.randomUUID(), key, it.source_key, it.title, it.summary ?? "", it.url ?? "", it.published_date ?? "")
          .run();
        if (res?.meta?.changes) n += res.meta.changes;
      }
      bySource[key] = n;
      total += n;
    } catch {
      bySource[key] = 0;
    }
  }
  return { new: total, by_source: bySource };
}

export async function getChangelog(env: Env, days = 7, limit = 50): Promise<any[]> {
  if (!env.DB) return [];
  const cutoff = new Date(Date.now() - days * 86400000).toISOString();
  const res = await env.DB.prepare(
    `SELECT source, title, summary, url, category, published_date, fetched_at
     FROM knowledge_updates WHERE fetched_at >= ?1 ORDER BY fetched_at DESC LIMIT ?2`,
  )
    .bind(cutoff, limit)
    .all<any>();
  return res.results ?? [];
}
