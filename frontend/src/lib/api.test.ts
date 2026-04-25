import { describe, it, expect } from "vitest";
import * as api from "./api";

describe("lib/api exports", () => {
  it("exposes the main API helper functions", () => {
    expect(typeof api.login).toBe("function");
    expect(typeof api.uploadCV).toBe("function");
    expect(typeof api.getMe).toBe("function");
    expect(typeof api.computeMatching).toBe("function");
    expect(typeof api.generateEmail).toBe("function");
  });
});
