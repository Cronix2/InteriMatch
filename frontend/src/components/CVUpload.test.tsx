import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import CVUpload from "./CVUpload";

describe("CVUpload", () => {
  it("renders without throwing", () => {
    expect(() =>
      render(
        <CVUpload
          onSuccess={() => {}}
          onStartMatching={() => {}}
          bulkJob={null}
          onBulkJobChange={() => {}}
        />
      )
    ).not.toThrow();
  });
});
