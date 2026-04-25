import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import Home from "./page";

describe("Home page", () => {
  it("renders without throwing", () => {
    expect(() => render(<Home />)).not.toThrow();
  });
});
