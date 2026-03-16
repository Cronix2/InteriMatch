"use client";

import { useEffect, useState } from "react";
import AuthScreen from "@/components/AuthScreen";
import CVUpload from "@/components/CVUpload";
import CandidateProfile from "@/components/CandidateProfile";
import MatchingResults from "@/components/MatchingResults";
import EmailPreview from "@/components/EmailPreview";

type Step = "upload" | "profile" | "matching" | "email";

export default function Home() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [step, setStep] = useState<Step>("upload");
  const [candidateId, setCandidateId] = useState<string | null>(null);
  const [profileData, setProfileData] = useState<any>(null);
  const [matchingResults, setMatchingResults] = useState<any[]>([]);
  const [selectedMatch, setSelectedMatch] = useState<any>(null);

  useEffect(() => {
    const token = localStorage.getItem("interimatch_token");
    if (token) setIsAuthenticated(true);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("interimatch_token");
    setIsAuthenticated(false);
    setStep("upload");
    setCandidateId(null);
    setProfileData(null);
    setMatchingResults([]);
    setSelectedMatch(null);
  };

  if (!isAuthenticated) {
    return <AuthScreen onAuthenticated={() => setIsAuthenticated(true)} />;
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">IM</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                InteriMatch AI
              </h1>
              <p className="text-xs text-gray-500">
                Matching CV / Offres d&apos;emploi
              </p>
            </div>
          </div>
          <nav className="flex gap-1">
            {[
              { key: "upload", label: "1. Upload CV" },
              { key: "profile", label: "2. Profil" },
              { key: "matching", label: "3. Matching" },
              { key: "email", label: "4. Email" },
            ].map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setStep(key as Step)}
                disabled={
                  (key === "profile" && !candidateId) ||
                  (key === "matching" && !profileData) ||
                  (key === "email" && !selectedMatch)
                }
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  step === key
                    ? "bg-primary-600 text-white"
                    : "text-gray-600 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed"
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
          <button
            onClick={handleLogout}
            className="ml-4 px-3 py-1.5 text-sm text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
          >
            Déconnexion
          </button>
        </div>
      </header>

      {/* Contenu principal */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {step === "upload" && (
          <CVUpload
            onSuccess={(data) => {
              setCandidateId(data.candidate.id);
              setProfileData(data.extracted_profile);
              setStep("profile");
            }}
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
            results={matchingResults}
            onResultsLoaded={setMatchingResults}
            onSelectMatch={(match) => {
              setSelectedMatch(match);
              setStep("email");
            }}
          />
        )}
        {step === "email" && selectedMatch && (
          <EmailPreview matchingResultId={selectedMatch.id} />
        )}
      </main>
    </div>
  );
}
