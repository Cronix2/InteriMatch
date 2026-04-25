"use client";

import {
  CheckCircle,
  XCircle,
  AlertCircle,
  RefreshCw,
  Pause,
  Play,
  Square,
} from "lucide-react";
import type { BulkJob } from "../CVUpload";

interface BulkUploadProgressProps {
  bulkJob: BulkJob;
  progressPct: number;
  onPause: () => void;
  onResume: () => void;
  onCancel: () => void;
  onStartMatching?: (candidateId: string) => void;
}

function StatusHeader({ status }: { status: string }) {
  if (status === "processing") {
    return (
      <>
        <RefreshCw className="w-4 h-4 animate-spin text-primary-500" />
        Traitement en cours...
      </>
    );
  }
  if (status === "paused") {
    return (
      <>
        <Pause className="w-4 h-4 text-amber-500" />
        En pause
      </>
    );
  }
  if (status === "cancelled") {
    return (
      <>
        <XCircle className="w-4 h-4 text-red-500" />
        Annulé
      </>
    );
  }
  return (
    <>
      <CheckCircle className="w-4 h-4 text-green-500" />
      Traitement terminé
    </>
  );
}

export default function BulkUploadProgress({
  bulkJob,
  progressPct,
  onPause,
  onResume,
  onCancel,
  onStartMatching,
}: BulkUploadProgressProps) {
  const isActive = bulkJob.status === "processing" || bulkJob.status === "paused";

  return (
    <div className="mt-6 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <StatusHeader status={bulkJob.status} />
        </h3>
        <div className="flex items-center gap-2">
          {isActive && (
            <>
              {bulkJob.status === "processing" ? (
                <button
                  onClick={onPause}
                  className="p-1.5 text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors"
                  title="Mettre en pause"
                >
                  <Pause className="w-4 h-4" />
                </button>
              ) : (
                <button
                  onClick={onResume}
                  className="p-1.5 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg transition-colors"
                  title="Reprendre"
                >
                  <Play className="w-4 h-4" />
                </button>
              )}
              <button
                onClick={onCancel}
                className="p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                title="Arrêter"
              >
                <Square className="w-4 h-4" />
              </button>
            </>
          )}
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {bulkJob.processed_files}/{bulkJob.total_files} fichier(s)
          </span>
        </div>
      </div>

      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 mb-3">
        <div
          className="bg-primary-600 h-2.5 rounded-full transition-all duration-500"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      <div className="flex gap-4 text-xs text-gray-600 dark:text-gray-400 mb-3">
        <span className="flex items-center gap-1">
          <CheckCircle className="w-3.5 h-3.5 text-green-500" />
          {bulkJob.successful_files} réussi(s)
        </span>
        {bulkJob.failed_files > 0 && (
          <span className="flex items-center gap-1">
            <XCircle className="w-3.5 h-3.5 text-red-500" />
            {bulkJob.failed_files} échoué(s)
          </span>
        )}
      </div>

      {bulkJob.results && bulkJob.results.length > 0 && (
        <div className="max-h-48 overflow-y-auto space-y-1">
          {bulkJob.results.map((r, i) => (
            <div
              key={i}
              className={`text-xs px-3 py-1.5 rounded flex items-center justify-between ${
                r.status === "success"
                  ? "bg-green-50 dark:bg-green-900/10 text-green-700 dark:text-green-400"
                  : "bg-red-50 dark:bg-red-900/10 text-red-700 dark:text-red-400"
              }`}
            >
              <span className="flex items-center gap-2 truncate">
                {r.status === "success" ? (
                  <CheckCircle className="w-3.5 h-3.5 flex-shrink-0" />
                ) : (
                  <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                )}
                <span className="truncate">{r.filename}</span>
              </span>
              {r.status === "success" && r.candidate_name && (
                <span className="ml-2 text-gray-500 dark:text-gray-400 truncate">
                  → {r.candidate_name}
                </span>
              )}
              {r.status === "success" && r.candidate_id && onStartMatching && (
                <button
                  onClick={() => onStartMatching(r.candidate_id!)}
                  className="ml-2 flex-shrink-0 px-2 py-0.5 text-xs font-medium bg-primary-600 text-white rounded hover:bg-primary-700 transition-colors"
                >
                  Matching
                </button>
              )}
              {r.status === "failed" && r.error && (
                <span className="ml-2 text-red-500 truncate max-w-[200px]" title={r.error}>
                  {r.error}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
