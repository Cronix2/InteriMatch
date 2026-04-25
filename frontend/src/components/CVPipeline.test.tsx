import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import CVPipeline from "./CVPipeline";

describe("CVPipeline", () => {
  it("renders without throwing", () => {
    expect(() => render(<CVPipeline />)).not.toThrow();
  });
});
