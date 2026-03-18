"use client";

import { useEffect, useState } from "react";
import {
  Search,
  Loader2,
  MapPin,
  Building,
  ArrowRight,
  TrendingUp,
  Clock,
  X,
  ChevronDown,
  ChevronUp,
  Briefcase,
  GraduationCap,
  Euro,
  FileText,
  Send,
  Mail,
} from "lucide-react";
import { computeMatching, getCandidateMatchings, getProposalCounts, lookupRecruiter } from "@/lib/api";

interface MatchingResultsProps {
  candidateId: string;
  profileData?: any;
  results: any[];
  onResultsLoaded: (results: any[]) => void;
  onSelectMatch: (match: any) => void;
}

export default function MatchingResults({
  candidateId,
  profileData,
  results,
  onResultsLoaded,
  onSelectMatch,
}: MatchingResultsProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [keywords, setKeywords] = useState(() => {
    if (profileData?.professional_domain) {
      // Prendre uniquement le premier mot du domaine
      return profileData.professional_domain.split(/\s+/)[0];
    }
    const titles = profileData?.desired_job_titles;
    if (titles && titles.length > 0) {
      // Prendre le premier mot du premier intitulé
      return titles[0].split(/\s+/)[0];
    }
    return "";
  });
  const [location, setLocation] = useState(() => {
    const raw = profileData?.mobility || profileData?._candidateLocation || "";
    // Retirer le code postal s'il est en début (ex: "75017 PARIS" → "PARIS")
    return raw.replace(/^\d{4,5}\s*/, "").trim();
  });
  const [department, setDepartment] = useState("");
  const [history, setHistory] = useState<any[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [selectedOffer, setSelectedOffer] = useState<any>(null);
  const [proposalCounts, setProposalCounts] = useState<Record<string, number>>({});
  const [recruiterInfo, setRecruiterInfo] = useState<any>(null);
  const [recruiterLoading, setRecruiterLoading] = useState(false);

  // Charger l'historique et les propositions au montage
  useEffect(() => {
    const loadData = async () => {
      setHistoryLoading(true);
      try {
        const [histRes, proposalsRes] = await Promise.all([
          getCandidateMatchings(candidateId),
          getProposalCounts(),
        ]);
        setHistory(histRes.data || []);
        setProposalCounts(proposalsRes.data || {});
      } catch {
        // Silencieux
      } finally {
        setHistoryLoading(false);
      }
    };
    loadData();
  }, [candidateId]);

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
      // Rafraîchir l'historique et propositions après une nouvelle recherche
      const [histResponse, proposalsRes] = await Promise.all([
        getCandidateMatchings(candidateId),
        getProposalCounts(),
      ]);
      setHistory(histResponse.data || []);
      setProposalCounts(proposalsRes.data || {});
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
    if (score >= 75) return "text-green-700 bg-green-100 dark:text-green-400 dark:bg-green-900/30";
    if (score >= 50) return "text-amber-700 bg-amber-100 dark:text-amber-400 dark:bg-amber-900/30";
    return "text-red-700 bg-red-100 dark:text-red-400 dark:bg-red-900/30";
  };

  const handleLookupRecruiter = async (jobId: string) => {
    setRecruiterLoading(true);
    setRecruiterInfo(null);
    try {
      const res = await lookupRecruiter(jobId);
      setRecruiterInfo(res.data);
    } catch {
      setRecruiterInfo({ error: true });
    } finally {
      setRecruiterLoading(false);
    }
  };

  const getExcellenceScore = (match: any) => {
    const skills = Number(match.skills_score ?? 0);
    const experience = Number(match.experience_score ?? 0);
    const education = Number(match.education_score ?? 0);
    const title = Number(match.job_title_score ?? 0);
    return 0.45 * skills + 0.35 * experience + 0.1 * education + 0.1 * title;
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

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Matching candidat / offres
        </h2>
        {history.length > 0 && (
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            <Clock className="w-4 h-4" />
            Historique ({history.length})
            {showHistory ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
        )}
      </div>

      {/* Historique des recherches */}
      {showHistory && (
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700 p-4 mb-6">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Recherches précédentes
          </h3>
          {historyLoading ? (
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              Chargement...
            </div>
          ) : (
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {history.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between bg-white dark:bg-gray-800 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-700 hover:border-primary-200 dark:hover:border-primary-700 cursor-pointer transition-colors"
                  onClick={() => { setSelectedOffer(item.job_offer); setRecruiterInfo(null); }}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {item.job_offer?.title || "Offre inconnue"}
                    </p>
                    <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      {item.job_offer?.company_name && (
                        <span className="flex items-center gap-1">
                          <Building className="w-3 h-3" />
                          {item.job_offer.company_name}
                        </span>
                      )}
                      {item.job_offer?.location && (
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3 h-3" />
                          {item.job_offer.location}
                        </span>
                      )}
                      {item.created_at && (
                        <span>{formatDate(item.created_at)}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-3">
                    <span
                      className={`text-xs font-bold px-2 py-1 rounded ${getScoreColor(item.global_score)}`}
                    >
                      {Math.round(item.global_score)}%
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectMatch(item);
                      }}
                      className="text-xs px-3 py-1.5 bg-primary-600 text-white rounded hover:bg-primary-700 transition-colors"
                    >
                      Mail
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Barre de recherche */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Mots-clés (optionnel)
            </label>
            <input
              type="text"
              placeholder="Ex: développeur, maçon, infirmier..."
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Commune
            </label>
            <input
              type="text"
              placeholder="Ex: Paris"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Département
            </label>
            <input
              type="text"
              placeholder="Ex: 75"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
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
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
          <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
        </div>
      )}

      {/* Modal détail offre */}
      {selectedOffer && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto shadow-xl">
            <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex items-center justify-between rounded-t-2xl">
              <h3 className="text-lg font-bold text-gray-900 dark:text-white truncate pr-4">
                {selectedOffer.title}
              </h3>
              <button
                onClick={() => setSelectedOffer(null)}
                className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors flex-shrink-0"
              >
                <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
              </button>
            </div>
            <div className="px-6 py-5 space-y-5">
              {/* Info principales */}
              <div className="flex flex-wrap gap-3">
                {selectedOffer.company_name && (
                  <span className="flex items-center gap-1.5 text-sm text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 px-3 py-1.5 rounded-lg">
                    <Building className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                    {selectedOffer.company_name}
                  </span>
                )}
                {selectedOffer.location && (
                  <span className="flex items-center gap-1.5 text-sm text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 px-3 py-1.5 rounded-lg">
                    <MapPin className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                    {selectedOffer.location}
                  </span>
                )}
                {selectedOffer.contract_type && (
                  <span className="flex items-center gap-1.5 text-sm text-gray-700 dark:text-gray-300 bg-blue-50 dark:bg-blue-900/20 px-3 py-1.5 rounded-lg">
                    <Briefcase className="w-4 h-4 text-blue-500 dark:text-blue-400" />
                    {selectedOffer.contract_type}
                  </span>
                )}
                {selectedOffer.experience_level && (
                  <span className="flex items-center gap-1.5 text-sm text-gray-700 dark:text-gray-300 bg-purple-50 dark:bg-purple-900/20 px-3 py-1.5 rounded-lg">
                    <GraduationCap className="w-4 h-4 text-purple-500 dark:text-purple-400" />
                    {selectedOffer.experience_level}
                  </span>
                )}
                {selectedOffer.salary_info && (
                  <span className="flex items-center gap-1.5 text-sm text-gray-700 dark:text-gray-300 bg-green-50 dark:bg-green-900/20 px-3 py-1.5 rounded-lg">
                    <Euro className="w-4 h-4 text-green-500 dark:text-green-400" />
                    {selectedOffer.salary_info}
                  </span>
                )}
              </div>

              {/* Description */}
              {selectedOffer.description && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-2 flex items-center gap-2">
                    <FileText className="w-4 h-4" />
                    Description du poste
                  </h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed whitespace-pre-line">
                    {selectedOffer.description}
                  </p>
                </div>
              )}

              {/* Compétences requises */}
              {selectedOffer.required_skills &&
                selectedOffer.required_skills.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-2">
                      Compétences requises
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {selectedOffer.required_skills.map(
                        (skill: string, i: number) => (
                          <span
                            key={i}
                            className="text-xs px-2.5 py-1 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400 rounded-full"
                          >
                            {skill}
                          </span>
                        )
                      )}
                    </div>
                  </div>
                )}

              {/* Source */}
              {selectedOffer.source && (
                <p className="text-xs text-gray-400 dark:text-gray-500">
                  Source : {selectedOffer.source}
                  {selectedOffer.publication_date &&
                    ` — publié le ${formatDate(selectedOffer.publication_date)}`}
                </p>
              )}

              {/* Recherche recruteur */}
              <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                <h4 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-3 flex items-center gap-2">
                  <Search className="w-4 h-4" />
                  Contact recruteur
                </h4>
                {!recruiterInfo && !recruiterLoading && selectedOffer.id && (
                  <button
                    onClick={() => handleLookupRecruiter(selectedOffer.id)}
                    className="px-4 py-2 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                  >
                    Rechercher le contact
                  </button>
                )}
                {recruiterLoading && (
                  <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Recherche en cours...
                  </div>
                )}
                {recruiterInfo && !recruiterInfo.error && (
                  <div className="space-y-2">
                    {recruiterInfo.has_contact ? (
                      <div className="bg-green-50 dark:bg-green-900/10 rounded-lg p-3 space-y-1.5">
                        {recruiterInfo.contact.contact_name && (
                          <p className="text-sm text-gray-900 dark:text-white font-medium">
                            {recruiterInfo.contact.contact_name}
                          </p>
                        )}
                        {recruiterInfo.contact.contact_email && (
                          <p className="text-sm text-gray-600 dark:text-gray-400 flex items-center gap-1.5">
                            <Mail className="w-3.5 h-3.5" />
                            <a href={`mailto:${recruiterInfo.contact.contact_email}`} className="text-primary-600 dark:text-primary-400 hover:underline">
                              {recruiterInfo.contact.contact_email}
                            </a>
                          </p>
                        )}
                        {recruiterInfo.contact.contact_phone && (
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            Tél : {recruiterInfo.contact.contact_phone}
                          </p>
                        )}
                        {recruiterInfo.contact.contact_info && (
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            {recruiterInfo.contact.contact_info}
                          </p>
                        )}
                        {recruiterInfo.contact.application_url && (
                          <p className="text-sm">
                            <a href={recruiterInfo.contact.application_url} target="_blank" rel="noopener noreferrer" className="text-primary-600 dark:text-primary-400 hover:underline">
                              Postuler en ligne
                            </a>
                          </p>
                        )}
                      </div>
                    ) : (
                      <div className="bg-amber-50 dark:bg-amber-900/10 rounded-lg p-3">
                        <p className="text-sm text-amber-700 dark:text-amber-400">
                          Aucune information de contact disponible pour cette offre.
                        </p>
                        {recruiterInfo.contact.company_url && (
                          <p className="text-sm mt-1">
                            <a href={recruiterInfo.contact.company_url} target="_blank" rel="noopener noreferrer" className="text-primary-600 dark:text-primary-400 hover:underline">
                              Site de l&apos;entreprise
                            </a>
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}
                {recruiterInfo?.error && (
                  <p className="text-sm text-red-600 dark:text-red-400">
                    Impossible de récupérer les informations de contact.
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Résultats */}
      {results.length > 0 && (
        <div className="space-y-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {results.length} offre(s) classée(s) par pertinence
          </p>
          {results.map((match, index) => (
            <div
              key={match.id}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between gap-4">
                <div
                  className="flex-1 cursor-pointer"
                  onClick={() => { setSelectedOffer(match.job_offer); setRecruiterInfo(null); }}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-sm font-bold text-gray-400 dark:text-gray-500">
                      #{index + 1}
                    </span>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white hover:text-primary-600 dark:hover:text-primary-400 transition-colors">
                      {match.job_offer?.title}
                    </h3>
                  </div>
                  <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600 dark:text-gray-400 mb-3">
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
                      <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                        {match.job_offer.contract_type}
                      </span>
                    )}
                    {match.job_offer?.id && proposalCounts[match.job_offer.id] > 0 && (
                      <span className="flex items-center gap-1 px-2 py-0.5 bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 rounded text-xs font-medium">
                        <Send className="w-3 h-3" />
                        {proposalCounts[match.job_offer.id]} proposition(s) envoyée(s)
                      </span>
                    )}
                  </div>
                  {match.explanation && (
                    <p className="text-sm text-gray-600 dark:text-gray-400">
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
                        className="text-xs px-2 py-1 bg-gray-50 dark:bg-gray-700 rounded text-gray-600 dark:text-gray-400"
                      >
                        {s.label}: {Math.round(s.value)}%
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-3">
                  <div className="space-y-2">
                    <div
                      className={`flex items-center gap-1 px-3 py-1.5 rounded-lg font-bold text-sm ${getScoreColor(match.global_score)}`}
                    >
                      <TrendingUp className="w-4 h-4" />
                      Adéquation profil: {Math.round(match.global_score)}%
                    </div>
                    <div
                      className={`flex items-center gap-1 px-3 py-1.5 rounded-lg font-bold text-sm ${getScoreColor(getExcellenceScore(match))}`}
                    >
                      <TrendingUp className="w-4 h-4" />
                      Potentiel d&apos;excellence: {Math.round(getExcellenceScore(match))}%
                    </div>
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
        <div className="text-center py-12 text-gray-400 dark:text-gray-500">
          <Search className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>Lancez une recherche pour trouver les offres les plus pertinentes</p>
        </div>
      )}
    </div>
  );
}
