"use client";

import { useEffect, useState } from "react";
import {
  Clock,
  Loader2,
  Building,
  MapPin,
  TrendingUp,
  User,
  Briefcase,
  Search,
} from "lucide-react";
import { getMatchingHistory } from "@/lib/api";

interface HistoryEntry {
  id: string;
  global_score: number;
  skills_score: number;
  experience_score: number;
  education_score: number;
  job_title_score: number;
  location_score: number;
  explanation: string;
  created_at: string;
  candidate: {
    id: string;
    first_name: string;
    last_name: string;
  } | null;
  job_offer: {
    id: string;
    title: string;
    company_name: string;
    location: string;
    contract_type: string;
  } | null;
}

export default function History() {
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const res = await getMatchingHistory();
        setEntries(res.data);
      } catch {
        setError("Impossible de charger l'historique");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const getScoreColor = (score: number) => {
    if (score >= 75)
      return "text-green-700 bg-green-100 dark:text-green-400 dark:bg-green-900/30";
    if (score >= 50)
      return "text-amber-700 bg-amber-100 dark:text-amber-400 dark:bg-amber-900/30";
    return "text-red-700 bg-red-100 dark:text-red-400 dark:bg-red-900/30";
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  const filtered = entries.filter((e) => {
    if (!filter) return true;
    const q = filter.toLowerCase();
    const candidateName = e.candidate
      ? `${e.candidate.first_name} ${e.candidate.last_name}`.toLowerCase()
      : "";
    const offerTitle = e.job_offer?.title?.toLowerCase() || "";
    const company = e.job_offer?.company_name?.toLowerCase() || "";
    return (
      candidateName.includes(q) ||
      offerTitle.includes(q) ||
      company.includes(q)
    );
  });

  if (loading) {
    return (
      <div className="text-center py-16">
        <Loader2 className="w-10 h-10 text-primary-600 animate-spin mx-auto mb-3" />
        <p className="text-gray-500 dark:text-gray-400">
          Chargement de l&apos;historique...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Clock className="w-6 h-6" />
          Historique des matchings
        </h2>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {entries.length} résultat(s)
        </span>
      </div>

      {/* Filtre */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-500" />
          <input
            type="text"
            placeholder="Filtrer par candidat, offre ou entreprise..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
          />
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-12 text-gray-400 dark:text-gray-500">
          <Clock className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>
            {entries.length === 0
              ? "Aucun matching effectué pour le moment"
              : "Aucun résultat pour ce filtre"}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((entry) => (
            <div
              key={entry.id}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  {/* Candidat */}
                  <div className="flex items-center gap-2 mb-1.5">
                    <User className="w-4 h-4 text-gray-400 dark:text-gray-500 flex-shrink-0" />
                    <span className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                      {entry.candidate
                        ? `${entry.candidate.first_name} ${entry.candidate.last_name}`
                        : "Candidat inconnu"}
                    </span>
                  </div>

                  {/* Offre */}
                  <h3 className="text-base font-medium text-gray-800 dark:text-gray-200 mb-2">
                    {entry.job_offer?.title || "Offre inconnue"}
                  </h3>

                  <div className="flex flex-wrap items-center gap-3 text-sm text-gray-600 dark:text-gray-400">
                    {entry.job_offer?.company_name && (
                      <span className="flex items-center gap-1">
                        <Building className="w-3.5 h-3.5" />
                        {entry.job_offer.company_name}
                      </span>
                    )}
                    {entry.job_offer?.location && (
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5" />
                        {entry.job_offer.location}
                      </span>
                    )}
                    {entry.job_offer?.contract_type && (
                      <span className="flex items-center gap-1 px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                        <Briefcase className="w-3 h-3" />
                        {entry.job_offer.contract_type}
                      </span>
                    )}
                    {entry.created_at && (
                      <span className="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500">
                        <Clock className="w-3 h-3" />
                        {formatDate(entry.created_at)}
                      </span>
                    )}
                  </div>

                  {entry.explanation && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 line-clamp-2">
                      {entry.explanation}
                    </p>
                  )}
                </div>

                {/* Score */}
                <div
                  className={`flex items-center gap-1 px-3 py-1.5 rounded-lg font-bold text-sm flex-shrink-0 ${getScoreColor(entry.global_score)}`}
                >
                  <TrendingUp className="w-4 h-4" />
                  {Math.round(entry.global_score)}%
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
