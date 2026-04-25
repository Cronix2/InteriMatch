import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import MatchingResults from "./MatchingResults";

describe("MatchingResults", () => {
  it("renders without throwing", () => {
    expect(() =>
      render(
        <MatchingResults
          candidateId="c1"
          profileData={{ skills: [], experiences: [] }}
          results={[]}
          onResultsLoaded={() => {}}
          onSelectMatch={() => {}}
        />
      )
    ).not.toThrow();
  });
});
