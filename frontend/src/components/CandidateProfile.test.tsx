import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import CandidateProfile from "./CandidateProfile";

const profile = {
  first_name: "Jean",
  last_name: "Dupont",
  email: "j.d@example.com",
  phone: null,
  location: null,
  skills: [],
  experiences: [],
  education: [],
  desired_job_titles: [],
  languages: [],
  summary: null,
};

describe("CandidateProfile", () => {
  it("renders without throwing", () => {
    expect(() =>
      render(<CandidateProfile profile={profile} onNext={() => {}} />)
    ).not.toThrow();
  });
});
