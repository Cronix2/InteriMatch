import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import Settings from "./Settings";

describe("Settings", () => {
  it("renders without throwing", () => {
    expect(() => render(<Settings onThemeChange={() => {}} />)).not.toThrow();
  });
});
