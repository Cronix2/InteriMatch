import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import Dashboard from "./Dashboard";

describe("Dashboard", () => {
  it("renders without throwing", () => {
    expect(() => render(<Dashboard />)).not.toThrow();
  });
});
