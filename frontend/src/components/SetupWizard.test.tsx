import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import SetupWizard from "./SetupWizard";

describe("SetupWizard", () => {
  it("renders without throwing", () => {
    expect(() => render(<SetupWizard onComplete={() => {}} />)).not.toThrow();
  });
});
