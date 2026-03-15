"use client";

import { useState } from "react";
import {
  Search,
  Loader2,
  MapPin,
  Building,
  ArrowRight,
  TrendingUp,
} from "lucide-react";
import { computeMatching } from "@/lib/api";

interface MatchingResultsProps {
  candidateId: string;
  results: any[];
  onResultsLoaded: (results: any[]) => void;
  onSelectMatch: (match: any) => void;
}

export default function MatchingResults({
  candidateId,
  results,
  onResultsLoaded,
  onSelectMatch,
}: MatchingResultsProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [keywords, setKeywords] = useState("");
  const [location, setLocation] = useState("");
  const [department, setDepartment] = useState("");

  const handleSearch = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await computeMatching({
        candidate_id: candidateId,
        keywords: keywords || undefined,
        location: location || undefined,
        department: department || undefined,
        max_results: 10,
      });
      onResultsLoaded(response.data);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          "Erreur lors du calcul du matching"
      );
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 75) return "text-green-700 bg-green-100";
    if (score >= 50) return "text-amber-700 bg-amber-100";
    return "text-red-700 bg-red-100";
  };

  return (
    <div className="max-w-5xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">
        Matching candidat / offres
      </h2>

      {/* Barre de recherche */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Mots-clés (optionnel)
            </label>
            <input
              type="text"
              placeholder="Ex: développeur, maçon, infirmier..."
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Commune
            </label>
            <input
              type="text"
              placeholder="Ex: Paris"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Département
            </label>
            <input
              type="text"
              placeholder="Ex: 75"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
            />
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <button
            onClick={handleSearch}
            disabled={loading}
            className="flex items-center gap-2 px-6 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Search className="w-4 h-4" />
            )}
            {loading ? "Analyse en cours..." : "Lancer le matching"}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Résultats */}
      {results.length > 0 && (
        <div className="space-y-4">
          <p className="text-sm text-gray-500">
            {results.length} offre(s) classée(s) par pertinence
          </p>
          {results.map((match, index) => (
            <div
              key={match.id}
              className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-sm font-bold text-gray-400">
                      #{index + 1}
                    </span>
                    <h3 className="text-lg font-semibold text-gray-900">
                      {match.job_offer?.title}
                    </h3>
                  </div>
                  <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600 mb-3">
                    {match.job_offer?.company_name && (
                      <span className="flex items-center gap-1">
                        <Building className="w-4 h-4" />
                        {match.job_offer.company_name}
                      </span>
                    )}
                    {match.job_offer?.location && (
                      <span className="flex items-center gap-1">
                        <MapPin className="w-4 h-4" />
                        {match.job_offer.location}
                      </span>
                    )}
                    {match.job_offer?.contract_type && (
                      <span className="px-2 py-0.5 bg-gray-100 rounded text-xs">
                        {match.job_offer.contract_type}
                      </span>
                    )}
                  </div>
                  {match.explanation && (
                    <p className="text-sm text-gray-600">
                      {match.explanation}
                    </p>
                  )}
                  {/* Détail des scores */}
                  <div className="flex flex-wrap gap-2 mt-3">
                    {[
                      { label: "Compétences", value: match.skills_score },
                      { label: "Expérience", value: match.experience_score },
                      { label: "Intitulé", value: match.job_title_score },
                      { label: "Localisation", value: match.location_score },
                      { label: "Formation", value: match.education_score },
                    ].map((s) => (
                      <span
                        key={s.label}
                        className="text-xs px-2 py-1 bg-gray-50 rounded text-gray-600"
                      >
                        {s.label}: {Math.round(s.value)}%
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-3">
                  <div
                    className={`flex items-center gap-1 px-3 py-1.5 rounded-lg font-bold text-lg ${getScoreColor(match.global_score)}`}
                  >
                    <TrendingUp className="w-5 h-5" />
                    {Math.round(match.global_score)}%
                  </div>
                  <button
                    onClick={() => onSelectMatch(match)}
                    className="flex items-center gap-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium"
                  >
                    Générer le mail
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && results.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <Search className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>Lancez une recherche pour trouver les offres les plus pertinentes</p>
        </div>
      )}
    </div>
  );
}
