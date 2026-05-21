import { describe, it, expect } from "vitest";
import { runAgentLoop } from "../src/agent";
import type { LLMClient } from "../src/llm";

function scripted(messages: any[]): LLMClient {
  const queue = [...messages];
  return async () => ({ choices: [{ message: queue.shift() }] });
}

const tc = (id: string, name: string, args: string) => ({
  id, type: "function", function: { name, arguments: args },
});

describe("runAgentLoop", () => {
  it("returns content when no tool calls", async () => {
    const r = await runAgentLoop(
      [{ role: "user", content: "hi" }], "m", [],
      { llmClient: scripted([{ content: "hello" }]) },
    );
    expect(r.content).toBe("hello");
    expect(r.stop_reason).toBe("completed");
    expect(r.tools_used).toEqual([]);
  });

  it("executes a tool then answers", async () => {
    const r = await runAgentLoop(
      [{ role: "user", content: "established 35 min visit" }], "m", ["em_level_advisor"],
      {
        llmClient: scripted([
          { content: "", tool_calls: [tc("c1", "em_level_advisor", '{"method":"time","patient_type":"established","total_time_minutes":35}')] },
          { content: "That visit supports 99214." },
        ]),
      },
    );
    expect(r.tools_used).toEqual(["em_level_advisor"]);
    expect(r.iterations).toBe(2);
    const toolMsg = r.messages.find((m) => m.role === "tool");
    expect(toolMsg?.content).toContain("99214");
    expect(r.content).toBe("That visit supports 99214.");
  });

  it("reports unknown tool and continues", async () => {
    const r = await runAgentLoop(
      [{ role: "user", content: "x" }], "m", [],
      {
        llmClient: scripted([
          { content: "", tool_calls: [tc("c1", "does_not_exist", "{}")] },
          { content: "done" },
        ]),
      },
    );
    expect(r.invocations[0].success).toBe(false);
    expect(r.content).toBe("done");
  });

  it("caps at max_iterations", async () => {
    const always = { content: "thinking", tool_calls: [tc("c", "em_level_advisor", '{"patient_type":"new"}')] };
    const r = await runAgentLoop(
      [{ role: "user", content: "x" }], "m", ["em_level_advisor"],
      { llmClient: scripted([always, always, always, always]), maxIterations: 3 },
    );
    expect(r.stop_reason).toBe("max_iterations");
    expect(r.iterations).toBe(3);
  });
});
