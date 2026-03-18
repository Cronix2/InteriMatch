"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, Loader2, CheckCircle } from "lucide-react";
import { uploadCV } from "@/lib/api";

interface CVUploadProps {
  onSuccess: (data: any) => void;
}

export default function CVUpload({ onSuccess }: CVUploadProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  const onDrop = useCallback(
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

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        [".docx"],
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024, // 10 Mo
    disabled: loading,
  });

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Importer un CV
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Déposez un CV au format PDF ou DOCX. L&apos;IA analysera
          automatiquement le contenu pour extraire le profil du candidat.
        </p>
      </div>

      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
          isDragActive
            ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
            : loading
            ? "border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 cursor-wait"
            : "border-gray-300 dark:border-gray-600 hover:border-primary-400 hover:bg-gray-50 dark:hover:bg-gray-800/50"
        }`}
      >
        <input {...getInputProps()} />

        {loading ? (
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="w-12 h-12 text-primary-600 animate-spin" />
            <div>
              <p className="text-lg font-medium text-gray-900 dark:text-white">
                Analyse en cours...
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Extraction du texte et analyse IA du CV
              </p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4">
            <Upload className="w-12 h-12 text-gray-400 dark:text-gray-500" />
            <div>
              <p className="text-lg font-medium text-gray-900 dark:text-white">
                {isDragActive
                  ? "Déposez le fichier ici"
                  : "Glissez-déposez un CV ici"}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                ou cliquez pour sélectionner un fichier (PDF, DOCX — max 10 Mo)
              </p>
            </div>
          </div>
        )}
      </div>

      {fileName && !loading && !error && (
        <div className="mt-4 flex items-center gap-2 text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/20 rounded-lg p-3">
          <CheckCircle className="w-5 h-5" />
          <span className="text-sm font-medium">{fileName} — analysé avec succès</span>
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
