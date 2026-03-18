"use client";

import { useCallback, useState, useEffect, useRef } from "react";
import { useDropzone } from "react-dropzone";
import {
  Upload,
  FileText,
  Loader2,
  CheckCircle,
  Archive,
  AlertCircle,
  XCircle,
  RefreshCw,
  Pause,
  Play,
  Square,
} from "lucide-react";
import { uploadCV, uploadBulkCV, getBulkJobStatus, pauseBulkJob, resumeBulkJob, cancelBulkJob } from "@/lib/api";

interface CVUploadProps {
  onSuccess: (data: any) => void;
  onStartMatching?: (candidateId: string) => void;
}

interface BulkJob {
  id: string;
  total_files: number;
  processed_files: number;
  successful_files: number;
  failed_files: number;
  status: string;
  results: { filename: string; status: string; error?: string; candidate_name?: string; candidate_id?: string }[];
}

export default function CVUpload({ onSuccess, onStartMatching }: CVUploadProps) {
  const [mode, setMode] = useState<"single" | "bulk">("single");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  // Bulk upload state
  const [bulkJob, setBulkJob] = useState<BulkJob | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Polling for bulk job status
  useEffect(() => {
    if (bulkJob && (bulkJob.status === "processing" || bulkJob.status === "paused")) {
      pollingRef.current = setInterval(async () => {
        try {
          const res = await getBulkJobStatus(bulkJob.id);
          setBulkJob(res.data);
          if (res.data.status === "completed" || res.data.status === "cancelled") {
            if (pollingRef.current) clearInterval(pollingRef.current);
            if (res.data.status === "completed") {
              const last = res.data.results?.find((r: any) => r.status === "success");
              if (last) onSuccess({ refreshList: true });
            }
          }
        } catch {
          // Ignore polling errors
        }
      }, 2000);
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [bulkJob?.id, bulkJob?.status, onSuccess]);

  const onDropSingle = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file) return;

      setFileName(file.name);
      setLoading(true);
      setError(null);

      try {
        const response = await uploadCV(file);
        onSuccess(response.data);
      } catch (err: any) {
        setError(
          err.response?.data?.detail ||
            "Erreur lors de l'upload du CV. Vérifiez le format du fichier."
        );
      } finally {
        setLoading(false);
      }
    },
    [onSuccess]
  );

  const onDropBulk = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file) return;

      setFileName(file.name);
      setLoading(true);
      setError(null);
      setBulkJob(null);

      try {
        const response = await uploadBulkCV(file);
        setBulkJob(response.data.job);
      } catch (err: any) {
        setError(
          err.response?.data?.detail ||
            "Erreur lors de l'upload du ZIP."
        );
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const singleDropzone = useDropzone({
    onDrop: onDropSingle,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        [".docx"],
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024,
    disabled: loading,
  });

  const bulkDropzone = useDropzone({
    onDrop: onDropBulk,
    accept: {
      "application/zip": [".zip"],
      "application/x-zip-compressed": [".zip"],
    },
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024,
    disabled: loading || (bulkJob?.status === "processing"),
  });

  const dropzone = mode === "single" ? singleDropzone : bulkDropzone;

  const progressPct = bulkJob
    ? Math.round((bulkJob.processed_files / Math.max(bulkJob.total_files, 1)) * 100)
    : 0;

  const handlePauseBulk = async () => {
    if (!bulkJob) return;
    try { await pauseBulkJob(bulkJob.id); setBulkJob({ ...bulkJob, status: "paused" }); } catch {}
  };

  const handleResumeBulk = async () => {
    if (!bulkJob) return;
    try { await resumeBulkJob(bulkJob.id); setBulkJob({ ...bulkJob, status: "processing" }); } catch {}
  };

  const handleCancelBulk = async () => {
    if (!bulkJob) return;
    try { await cancelBulkJob(bulkJob.id); setBulkJob({ ...bulkJob, status: "cancelled" }); } catch {}
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Importer des CV
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Importez un CV unique ou plusieurs CV d&apos;un coup via un fichier ZIP.
        </p>
      </div>

      {/* Mode Toggle */}
      <div className="flex justify-center mb-6">
        <div className="inline-flex rounded-lg bg-gray-100 dark:bg-gray-800 p-1">
          <button
            onClick={() => { setMode("single"); setError(null); setBulkJob(null); }}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-all flex items-center gap-2 ${
              mode === "single"
                ? "bg-white dark:bg-gray-700 text-primary-700 dark:text-primary-400 shadow-sm"
                : "text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
            }`}
          >
            <FileText className="w-4 h-4" />
            CV unique
          </button>
          <button
            onClick={() => { setMode("bulk"); setError(null); setFileName(null); }}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-all flex items-center gap-2 ${
              mode === "bulk"
                ? "bg-white dark:bg-gray-700 text-primary-700 dark:text-primary-400 shadow-sm"
                : "text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
            }`}
          >
            <Archive className="w-4 h-4" />
            Import groupé (ZIP)
          </button>
        </div>
      </div>

      {/* Dropzone */}
      <div
        {...dropzone.getRootProps()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
          dropzone.isDragActive
            ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
            : loading
            ? "border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 cursor-wait"
            : "border-gray-300 dark:border-gray-600 hover:border-primary-400 hover:bg-gray-50 dark:hover:bg-gray-800/50"
        }`}
      >
        <input {...dropzone.getInputProps()} />

        {loading ? (
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="w-12 h-12 text-primary-600 animate-spin" />
            <div>
              <p className="text-lg font-medium text-gray-900 dark:text-white">
                {mode === "single" ? "Analyse en cours..." : "Envoi du ZIP..."}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {mode === "single"
                  ? "Extraction du texte et analyse IA du CV"
                  : "Extraction des fichiers et lancement du traitement"}
              </p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4">
            {mode === "single" ? (
              <Upload className="w-12 h-12 text-gray-400 dark:text-gray-500" />
            ) : (
              <Archive className="w-12 h-12 text-gray-400 dark:text-gray-500" />
            )}
            <div>
              <p className="text-lg font-medium text-gray-900 dark:text-white">
                {dropzone.isDragActive
                  ? "Déposez le fichier ici"
                  : mode === "single"
                  ? "Glissez-déposez un CV ici"
                  : "Glissez-déposez un fichier ZIP ici"}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {mode === "single"
                  ? "ou cliquez pour sélectionner un fichier (PDF, DOCX — max 10 Mo)"
                  : "ZIP contenant des fichiers PDF/DOCX (max 50 CV, 50 Mo)"}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Single success */}
      {mode === "single" && fileName && !loading && !error && (
        <div className="mt-4 flex items-center gap-2 text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/20 rounded-lg p-3">
          <CheckCircle className="w-5 h-5" />
          <span className="text-sm font-medium">{fileName} — analysé avec succès</span>
        </div>
      )}

      {/* Bulk Job Progress */}
      {mode === "bulk" && bulkJob && (
        <div className="mt-6 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              {bulkJob.status === "processing" ? (
                <RefreshCw className="w-4 h-4 animate-spin text-primary-500" />
              ) : bulkJob.status === "paused" ? (
                <Pause className="w-4 h-4 text-amber-500" />
              ) : bulkJob.status === "cancelled" ? (
                <XCircle className="w-4 h-4 text-red-500" />
              ) : (
                <CheckCircle className="w-4 h-4 text-green-500" />
              )}
              {bulkJob.status === "processing"
                ? "Traitement en cours..."
                : bulkJob.status === "paused"
                ? "En pause"
                : bulkJob.status === "cancelled"
                ? "Annulé"
                : "Traitement terminé"}
            </h3>
            <div className="flex items-center gap-2">
              {(bulkJob.status === "processing" || bulkJob.status === "paused") && (
                <>
                  {bulkJob.status === "processing" ? (
                    <button
                      onClick={handlePauseBulk}
                      className="p-1.5 text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors"
                      title="Mettre en pause"
                    >
                      <Pause className="w-4 h-4" />
                    </button>
                  ) : (
                    <button
                      onClick={handleResumeBulk}
                      className="p-1.5 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg transition-colors"
                      title="Reprendre"
                    >
                      <Play className="w-4 h-4" />
                    </button>
                  )}
                  <button
                    onClick={handleCancelBulk}
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

          {/* Progress Bar */}
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

          {/* Results detail */}
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
      )}

      {error && (
        <div className="mt-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
        </div>
      )}
    </div>
  );
}
