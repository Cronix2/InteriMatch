import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import History from "./History";

describe("History", () => {
  it("renders without throwing", () => {
    expect(() => render(<History />)).not.toThrow();
  });
});
