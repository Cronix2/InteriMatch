"use client";

import { useState } from "react";
import CVUpload from "@/components/CVUpload";
import CandidateProfile from "@/components/CandidateProfile";
import MatchingResults from "@/components/MatchingResults";
import EmailPreview from "@/components/EmailPreview";
import { getCandidateProfile } from "@/lib/api";

type Step = "upload" | "profile" | "matching" | "email";

export default function MatchFlow() {
  const [step, setStep] = useState<Step>("upload");
  const [candidateId, setCandidateId] = useState<string | null>(null);
  const [profileData, setProfileData] = useState<any>(null);
  const [matchingResults, setMatchingResults] = useState<any[]>([]);
  const [selectedMatch, setSelectedMatch] = useState<any>(null);

  const handleStartMatching = async (cid: string) => {
    try {
      const res = await getCandidateProfile(cid);
      const { candidate, extracted_profile } = res.data;
      setCandidateId(candidate.id);
      setProfileData({
        ...extracted_profile,
        _candidateLocation: candidate.location,
      });
      setMatchingResults([]);
      setSelectedMatch(null);
      setStep("matching");
    } catch {
      // silently fail
    }
  };

  const steps = [
    { key: "upload" as Step, label: "1. Upload CV" },
    { key: "profile" as Step, label: "2. Profil" },
    { key: "matching" as Step, label: "3. Matching" },
    { key: "email" as Step, label: "4. Email" },
  ];

  return (
    <div>
      {/* Breadcrumb étapes */}
      <div className="flex items-center gap-1 mb-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-2 w-fit">
        {steps.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setStep(key)}
            disabled={
              (key === "profile" && !candidateId) ||
              (key === "matching" && !profileData) ||
              (key === "email" && !selectedMatch)
            }
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              step === key
                ? "bg-primary-600 text-white"
                : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Contenu */}
      {step === "upload" && (
        <CVUpload
          onSuccess={(data) => {
            setCandidateId(data.candidate.id);
            setProfileData({
              ...data.extracted_profile,
              _candidateLocation: data.candidate?.location,
            });
            setStep("profile");
          }}
          onStartMatching={handleStartMatching}
        />
      )}
      {step === "profile" && profileData && (
        <CandidateProfile
          profile={profileData}
          onNext={() => setStep("matching")}
        />
      )}
      {step === "matching" && candidateId && (
        <MatchingResults
          candidateId={candidateId}
          profileData={profileData}
          results={matchingResults}
          onResultsLoaded={setMatchingResults}
          onSelectMatch={(match) => {
            setSelectedMatch(match);
            setStep("email");
          }}
        />
      )}
      {step === "email" && selectedMatch && (
        <EmailPreview matchingResultId={selectedMatch.id} candidateId={candidateId || undefined} />
      )}
    </div>
  );
}
