import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import EmailPreview from "./EmailPreview";

describe("EmailPreview", () => {
  it("renders without throwing", () => {
    expect(() =>
      render(
        <EmailPreview
          matchingResultId="m1"
          candidateId="c1"
          jobOfferId="j1"
        />
      )
    ).not.toThrow();
  });
});
