import { describe, expect, it, vi, afterEach } from "vitest";
import { getSystemInfo } from "./api";

afterEach(() => vi.restoreAllMocks());

describe("api client", () => {
  it("parses system info", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            app_name: "InsightIQ",
            version: "0.1.0",
            environment: "ci",
            llm_provider: "mock",
            planner_model: "claude-sonnet-5",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );
    const info = await getSystemInfo();
    expect(info.app_name).toBe("InsightIQ");
    expect(info.planner_model).toBe("claude-sonnet-5");
  });

  it("throws on error envelope", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ error: { code: "boom", message: "nope" } }), {
          status: 500,
        }),
      ),
    );
    await expect(getSystemInfo()).rejects.toThrow("nope");
  });
});
