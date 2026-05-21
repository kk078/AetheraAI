import { describe, it, expect } from "vitest";
import { buildMemoryContext, searchMemory, storeMemory, embed } from "../src/memory";

function fakeEnv(overrides: any = {}): any {
  return {
    AI: { run: async (_m: string, _i: any) => ({ data: [[0.1, 0.2, 0.3]] }) },
    VECTORIZE: {
      upsert: async (_v: any) => ({}),
      query: async (_v: number[], _o: any) => ({
        matches: [
          { id: "1", score: 0.92, metadata: { text: "User: claim denied CO-50\nAssistant: appeal it", user_id: "u1" } },
          { id: "2", score: 0.81, metadata: { text: "other user note", user_id: "u2" } },
        ],
      }),
    },
    ...overrides,
  };
}

describe("buildMemoryContext", () => {
  it("returns empty when no matches", () => {
    expect(buildMemoryContext([])).toBe("");
  });
  it("renders a memory block", () => {
    const ctx = buildMemoryContext([{ score: 0.9, text: "remember this" }]);
    expect(ctx).toContain("Relevant memory");
    expect(ctx).toContain("remember this");
  });
  it("skips empty-text matches", () => {
    expect(buildMemoryContext([{ score: 0.9, text: "" }])).toBe("");
  });
});

describe("embed", () => {
  it("returns null without AI binding", async () => {
    expect(await embed({} as any, "hello")).toBeNull();
  });
  it("returns the embedding vector", async () => {
    expect(await embed(fakeEnv(), "hello")).toEqual([0.1, 0.2, 0.3]);
  });
});

describe("searchMemory / storeMemory", () => {
  it("no-op when VECTORIZE is unbound", async () => {
    expect(await searchMemory({ AI: fakeEnv().AI } as any, "q", "u1")).toEqual([]);
    expect(await storeMemory({ AI: fakeEnv().AI } as any, "id", "text")).toBe(false);
  });

  it("returns matches filtered by user", async () => {
    const matches = await searchMemory(fakeEnv(), "denial appeal", "u1", 5);
    expect(matches.length).toBe(1); // u2's note filtered out
    expect(matches[0].text).toContain("CO-50");
  });

  it("stores when bound", async () => {
    expect(await storeMemory(fakeEnv(), "id1", "some memory", { user_id: "u1" })).toBe(true);
  });
});
