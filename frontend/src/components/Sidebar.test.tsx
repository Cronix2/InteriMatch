import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import Sidebar from "./Sidebar";

describe("Sidebar", () => {
  it("renders without throwing", () => {
    expect(() =>
      render(
        <Sidebar
          currentPage="dashboard"
          onNavigate={() => {}}
          onLogout={() => {}}
        />
      )
    ).not.toThrow();
  });
});
