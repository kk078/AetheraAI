import { describe, it, expect } from "vitest";
import { checkUpdates, getChangelog } from "../src/knowledge";
import { generateBriefing, getBriefing } from "../src/briefing";

function makeKnowledgeDB() {
  const rows: any[] = [];
  const db: any = {
    _rows: rows,
    prepare(sql: string) {
      const stmt: any = {
        _args: [] as any[],
        bind(...a: any[]) { stmt._args = a; return stmt; },
        async run() {
          if (/INSERT/.test(sql)) {
            const [id, source, source_key, title, summary, url, published_date] = stmt._args;
            if (rows.some((r) => r.source === source && r.source_key === source_key)) {
              return { meta: { changes: 0 } };
            }
            rows.push({ id, source, source_key, title, summary, url, category: "healthcare_regulatory", published_date, fetched_at: new Date().toISOString() });
            return { meta: { changes: 1 } };
          }
          return { meta: { changes: 0 } };
        },
        async all() {
          const limit = stmt._args[1] ?? 50;
          return { results: rows.slice().reverse().slice(0, limit) };
        },
      };
      return stmt;
    },
  };
  return db;
}

function makeKV() {
  const store: Record<string, string> = {};
  return {
    async get(k: string) { return store[k] ?? null; },
    async put(k: string, v: string) { store[k] = v; },
  };
}

const fakeFetch = (async (url: string) => ({
  ok: true,
  json: async () =>
    String(url).includes("data.cms.gov")
      ? { dataset: [{ identifier: "ds-1", title: "2026 Physician Fee Schedule", description: "Updated rates", modified: new Date().toISOString(), landingPage: "https://data.cms.gov/ds-1" }] }
      : { results: [{ document_number: "2026-001", title: "CMS final rule", abstract: "abstract text", html_url: "https://fr/2026-001", publication_date: "2026-05-01" }] },
})) as any;

describe("checkUpdates", () => {
  it("inserts new items from both sources and dedups on re-run", async () => {
    const env: any = { DB: makeKnowledgeDB() };
    const first = await checkUpdates(env, fakeFetch);
    expect(first.new).toBe(2);
    expect(first.by_source.cms_data_gov).toBe(1);
    expect(first.by_source.federal_register).toBe(1);

    const second = await checkUpdates(env, fakeFetch);
    expect(second.new).toBe(0); // deduped

    const log = await getChangelog(env, 7, 50);
    expect(log.length).toBe(2);
  });

  it("no-op without DB", async () => {
    const r = await checkUpdates({} as any, fakeFetch);
    expect(r.new).toBe(0);
  });
});

describe("briefing", () => {
  it("generates and caches a briefing", async () => {
    const env: any = { DB: makeKnowledgeDB(), CACHE: makeKV() };
    await checkUpdates(env, fakeFetch);
    const b = await generateBriefing(env);
    expect(b.counts.recent_regulatory_updates).toBe(2);
    expect(b.headline).toContain("2 new");

    const cached = await getBriefing(env);
    expect(cached.counts.recent_regulatory_updates).toBe(2);
  });

  it("headline when nothing recent", async () => {
    const env: any = { DB: makeKnowledgeDB(), CACHE: makeKV() };
    const b = await generateBriefing(env);
    expect(b.headline).toContain("No new");
  });
});
