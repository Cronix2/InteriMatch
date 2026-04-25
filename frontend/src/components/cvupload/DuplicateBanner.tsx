"use client";

import { AlertCircle, UserCheck, UserPlus } from "lucide-react";

export interface DuplicateCandidateInfo {
  existing_candidate: {
    candidate_id: string;
    candidate_name: string;
    similarity: number;
    match_reasons: string[];
  };
  file: File;
}

interface DuplicateBannerProps {
  info: DuplicateCandidateInfo;
  loading: boolean;
  onUpdate: () => void;
  onCreateNew: () => void;
  onDismiss: () => void;
}

export default function DuplicateBanner({
  info,
  loading,
  onUpdate,
  onCreateNew,
  onDismiss,
}: DuplicateBannerProps) {
  const reasons = info.existing_candidate.match_reasons;
  return (
    <div className="mb-6 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-5">
      <div className="flex items-start gap-3">
        <AlertCircle className="w-6 h-6 text-amber-500 mt-0.5 flex-shrink-0" />
        <div className="flex-1">
          <h3 className="text-base font-semibold text-amber-800 dark:text-amber-300 mb-1">
            Candidat similaire détecté
          </h3>
          <p className="text-sm text-amber-700 dark:text-amber-400 mb-3">
            <strong>{info.existing_candidate.candidate_name}</strong> semble correspondre au CV importé.
            {reasons.includes("name") && " (même nom)"}
            {reasons.includes("face") && " (reconnaissance faciale)"}
            {reasons.includes("career") && " (parcours similaire)"}
            {" — "}Similarité : {Math.round(info.existing_candidate.similarity * 100)}%
          </p>
          <div className="flex items-center gap-3">
            <button
              onClick={onUpdate}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 transition-colors font-medium disabled:opacity-50"
            >
              <UserCheck className="w-4 h-4" />
              Mettre à jour le candidat existant
            </button>
            <button
              onClick={onCreateNew}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors font-medium disabled:opacity-50"
            >
              <UserPlus className="w-4 h-4" />
              Créer un nouveau candidat
            </button>
            <button
              onClick={onDismiss}
              className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              Annuler
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
