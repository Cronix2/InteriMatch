import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import MatchFlow from "./MatchFlow";

describe("MatchFlow", () => {
  it("renders without throwing", () => {
    expect(() => render(<MatchFlow />)).not.toThrow();
  });
});
