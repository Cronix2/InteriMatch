import { describe, it, expect } from "vitest";
import { AxiosError, AxiosHeaders } from "axios";
import { cn, getApiErrorDetail, getApiErrorStatus } from "./utils";

function makeAxiosError(status: number, detail?: string): AxiosError {
  const headers = new AxiosHeaders();
  const err = new AxiosError(
    "Request failed",
    String(status),
    { headers },
    null,
    {
      status,
      statusText: "ERR",
      headers,
      config: { headers },
      data: detail !== undefined ? { detail } : {},
    }
  );
  return err;
}

describe("cn()", () => {
  it("merges plain class names", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("dedupes conflicting Tailwind classes via twMerge", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
  });

  it("ignores falsy values", () => {
    expect(cn("a", false && "b", null, undefined, "c")).toBe("a c");
  });
});

describe("getApiErrorDetail()", () => {
  it("returns the API detail when present on an axios error", () => {
    const err = makeAxiosError(400, "Champ obligatoire");
    expect(getApiErrorDetail(err)).toBe("Champ obligatoire");
  });

  it("falls back to the axios message when no detail field", () => {
    const err = makeAxiosError(500);
    err.message = "Network Error";
    expect(getApiErrorDetail(err)).toBe("Network Error");
  });

  it("returns the fallback for non-axios errors with no message", () => {
    expect(getApiErrorDetail({}, "Bad")).toBe("Bad");
  });

  it("returns the Error.message for plain JS errors", () => {
    expect(getApiErrorDetail(new Error("Boom"))).toBe("Boom");
  });

  it("uses the default fallback when nothing else available", () => {
    expect(getApiErrorDetail(undefined)).toBe("Une erreur est survenue");
  });
});

describe("getApiErrorStatus()", () => {
  it("returns the HTTP status from an axios error", () => {
    expect(getApiErrorStatus(makeAxiosError(404))).toBe(404);
  });

  it("returns undefined for non-axios errors", () => {
    expect(getApiErrorStatus(new Error("nope"))).toBeUndefined();
    expect(getApiErrorStatus(undefined)).toBeUndefined();
  });
});
