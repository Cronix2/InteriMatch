import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import AuthScreen from "./AuthScreen";

describe("AuthScreen", () => {
  it("renders without throwing", () => {
    expect(() => render(<AuthScreen onAuthenticated={() => {}} />)).not.toThrow();
  });
});
