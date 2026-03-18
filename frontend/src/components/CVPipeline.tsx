"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  Upload,
  Loader2,
  Search,
  CheckCircle,
  Clock,
  Mail,
  RefreshCw,
  Filter,
  Users,
} from "lucide-react";
import CVUpload from "@/components/CVUpload";
import MatchingResults from "@/components/MatchingResults";
import EmailPreview from "@/components/EmailPreview";
import {
  listPipelineCandidates,
  updateCandidateStatus,
  getCandidateProfile,
} from "@/lib/api";

type View = "table" | "matching" | "email";

type PipelineStatus = "pending" | "matching" | "email" | "completed";

interface PipelineCandidate {
  id: string;
  first_name: string;
  last_name: string;
  email: string | null;
  location: string | null;
  processing_status: PipelineStatus;
  created_at: string | null;
  profile: {
    professional_domain?: string;
    desired_job_titles?: string[];
    mobility?: string;
    skills?: string[];
  };
}

const STATUS_CONFIG: Record<
  PipelineStatus,
  { label: string; color: string; icon: typeof Clock }
> = {
  pending: {
    label: "À traiter",
    color:
      "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
    icon: Clock,
  },
  matching: {
    label: "Matching",
    color:
      "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    icon: Search,
  },
  email: {
    label: "Email",
    color:
      "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    icon: Mail,
  },
  completed: {
    label: "Traité",
    color:
      "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    icon: CheckCircle,
  },
};

export default function CVPipeline() {
  const [view, setView] = useState<View>("table");
  const [candidates, setCandidates] = useState<PipelineCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<PipelineStatus | "all">("all");
  const [showUpload, setShowUpload] = useState(false);

  // Current candidate processing state
  const [currentCandidate, setCurrentCandidate] =
    useState<PipelineCandidate | null>(null);
  const [candidateId, setCandidateId] = useState<string | null>(null);
  const [profileData, setProfileData] = useState<any>(null);
  const [matchingResults, setMatchingResults] = useState<any[]>([]);
  const [selectedMatch, setSelectedMatch] = useState<any>(null);

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const silentUpdateStatus = async (id: string, status: string) => {
    try { await updateCandidateStatus(id, status); } catch { /* non-blocking */ }
  };

  const loadCandidates = useCallback(async () => {
    try {
      const res = await listPipelineCandidates();
      setCandidates(res.data);
    } catch {
      // silently fail
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadCandidates().finally(() => setLoading(false));
  }, [loadCandidates]);

  // Polling when on table view
  useEffect(() => {
    if (view === "table") {
      pollingRef.current = setInterval(loadCandidates, 5000);
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [view, loadCandidates]);

  const handleSelectCandidate = async (candidate: PipelineCandidate) => {
    setCurrentCandidate(candidate);
    setCandidateId(candidate.id);
    setMatchingResults([]);
    setSelectedMatch(null);

    try {
      const res = await getCandidateProfile(candidate.id);
      const { candidate: cand, extracted_profile } = res.data;
      setProfileData({
        ...extracted_profile,
        _candidateLocation: cand.location,
      });
    } catch {
      setProfileData({
        _candidateLocation: candidate.location,
        professional_domain: candidate.profile?.professional_domain,
        desired_job_titles: candidate.profile?.desired_job_titles,
        mobility: candidate.profile?.mobility,
      });
    }

    // Update status to matching
    await silentUpdateStatus(candidate.id, "matching");

    setView("matching");
  };

  const handleBackToTable = async () => {
    // Refresh candidates list
    await loadCandidates();
    setView("table");
    setCurrentCandidate(null);
    setCandidateId(null);
    setProfileData(null);
    setMatchingResults([]);
    setSelectedMatch(null);
  };

  const handleGoToEmail = async (match: any) => {
    setSelectedMatch(match);
    if (candidateId) {
      await silentUpdateStatus(candidateId, "email");
    }
    setView("email");
  };

  const handleMarkCompleted = async () => {
    if (candidateId) {
      await silentUpdateStatus(candidateId, "completed");
    }
    await handleBackToTable();
  };

  const handleUploadSuccess = async () => {
    setShowUpload(false);
    setLoading(true);
    await loadCandidates();
    setLoading(false);
  };

  const filtered =
    filter === "all"
      ? candidates
      : candidates.filter((c) => c.processing_status === filter);

  const counts = {
    all: candidates.length,
    pending: candidates.filter((c) => c.processing_status === "pending").length,
    matching: candidates.filter((c) => c.processing_status === "matching")
      .length,
    email: candidates.filter((c) => c.processing_status === "email").length,
    completed: candidates.filter((c) => c.processing_status === "completed")
      .length,
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "";
    try {
      return new Date(dateStr).toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  // ─── Processing View (matching or email) ─────────────────────────────
  if (view === "matching" || view === "email") {
    return (
      <div>
        {/* Header with back button */}
        <div className="flex items-center gap-4 mb-6">
          <button
            onClick={handleBackToTable}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Retour au tableau
          </button>
          {currentCandidate && (
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                {currentCandidate.first_name} {currentCandidate.last_name}
              </h2>
              <span
                className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${
                  STATUS_CONFIG[
                    view === "email" ? "email" : "matching"
                  ].color
                }`}
              >
                {view === "email" ? "Email" : "Matching"}
              </span>
            </div>
          )}
          {view === "email" && (
            <button
              onClick={handleMarkCompleted}
              className="ml-auto flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 transition-colors"
            >
              <CheckCircle className="w-4 h-4" />
              Marquer comme traité
            </button>
          )}
        </div>

        {/* Step indicators */}
        <div className="flex items-center gap-1 mb-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-2 w-fit">
          <button
            onClick={() => setView("matching")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              view === "matching"
                ? "bg-primary-600 text-white"
                : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
            }`}
          >
            1. Matching
          </button>
          <button
            onClick={() => {
              if (selectedMatch) setView("email");
            }}
            disabled={!selectedMatch}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              view === "email"
                ? "bg-primary-600 text-white"
                : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed"
            }`}
          >
            2. Email
          </button>
        </div>

        {/* Content */}
        {view === "matching" && candidateId && (
          <MatchingResults
            candidateId={candidateId}
            profileData={profileData}
            results={matchingResults}
            onResultsLoaded={setMatchingResults}
            onSelectMatch={handleGoToEmail}
          />
        )}
        {view === "email" && selectedMatch && (
          <EmailPreview
            matchingResultId={selectedMatch.id}
            candidateId={candidateId || undefined}
            jobOfferId={selectedMatch.job_offer?.id}
          />
        )}
      </div>
    );
  }

  // ─── Table View ──────────────────────────────────────────────────────
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Users className="w-6 h-6" />
            Pipeline de traitement
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {counts.pending} CV à traiter · {counts.matching + counts.email} en
            cours · {counts.completed} traités
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setLoading(true);
              loadCandidates().finally(() => setLoading(false));
            }}
            className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            title="Rafraîchir"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? "animate-spin" : ""}`} />
          </button>
          <button
            onClick={() => setShowUpload(!showUpload)}
            className="flex items-center gap-2 px-4 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium text-sm"
          >
            <Upload className="w-4 h-4" />
            Importer des CV
          </button>
        </div>
      </div>

      {/* Upload section (collapsible) */}
      {showUpload && (
        <div className="mb-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
          <CVUpload
            onSuccess={handleUploadSuccess}
          />
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex items-center gap-1 mb-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-1.5 w-fit">
        {(
          [
            { key: "all" as const, label: "Tous", count: counts.all },
            { key: "pending" as const, label: "À traiter", count: counts.pending },
            { key: "matching" as const, label: "Matching", count: counts.matching },
            { key: "email" as const, label: "Email", count: counts.email },
            { key: "completed" as const, label: "Traités", count: counts.completed },
          ] as const
        ).map(({ key, label, count }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 ${
              filter === key
                ? "bg-primary-600 text-white"
                : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
            }`}
          >
            {label}
            <span
              className={`px-1.5 py-0.5 rounded-full text-[10px] ${
                filter === key
                  ? "bg-white/20"
                  : "bg-gray-200 dark:bg-gray-600"
              }`}
            >
              {count}
            </span>
          </button>
        ))}
      </div>

      {/* Table */}
      {loading && candidates.length === 0 ? (
        <div className="text-center py-16">
          <Loader2 className="w-8 h-8 text-primary-600 animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Chargement des candidats...
          </p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
          <Filter className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {candidates.length === 0
              ? "Aucun CV importé. Importez des CV pour commencer."
              : "Aucun candidat dans cette catégorie."}
          </p>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Candidat
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden md:table-cell">
                  Domaine
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden md:table-cell">
                  Localisation
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Statut
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden sm:table-cell">
                  Date
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {filtered.map((candidate) => {
                const cfg = STATUS_CONFIG[candidate.processing_status];
                const StatusIcon = cfg.icon;
                const domain =
                  candidate.profile?.professional_domain ||
                  (candidate.profile?.desired_job_titles?.[0]
                    ?.split(/\s+/)[0]) ||
                  "—";
                const loc = (
                  candidate.location || candidate.profile?.mobility || ""
                )
                  .replace(/^\d{4,5}\s*/, "")
                  .trim() || "—";

                return (
                  <tr
                    key={candidate.id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors cursor-pointer"
                    onClick={() => handleSelectCandidate(candidate)}
                  >
                    <td className="px-4 py-3">
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {candidate.first_name} {candidate.last_name}
                        </p>
                        {candidate.email && (
                          <p className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[200px]">
                            {candidate.email}
                          </p>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <span className="text-sm text-gray-700 dark:text-gray-300 capitalize">
                        {domain}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <span className="text-sm text-gray-700 dark:text-gray-300">
                        {loc}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${cfg.color}`}
                      >
                        <StatusIcon className="w-3 h-3" />
                        {cfg.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden sm:table-cell">
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {formatDate(candidate.created_at)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSelectCandidate(candidate);
                        }}
                        className="px-3 py-1.5 text-xs font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                      >
                        {candidate.processing_status === "completed"
                          ? "Revoir"
                          : "Traiter"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
