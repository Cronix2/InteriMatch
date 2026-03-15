"use client";

import { useEffect, useState } from "react";
import {
  Mail,
  Loader2,
  CheckCircle,
  Edit3,
  Copy,
} from "lucide-react";
import { generateEmail, updateEmail } from "@/lib/api";

interface EmailPreviewProps {
  matchingResultId: string;
}

export default function EmailPreview({
  matchingResultId,
}: EmailPreviewProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [emailData, setEmailData] = useState<any>(null);
  const [editing, setEditing] = useState(false);
  const [editSubject, setEditSubject] = useState("");
  const [editBody, setEditBody] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const generate = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await generateEmail(matchingResultId);
        setEmailData(response.data);
        setEditSubject(response.data.subject);
        setEditBody(response.data.body);
      } catch (err: any) {
        setError(
          err.response?.data?.detail ||
            "Erreur lors de la génération du mail"
        );
      } finally {
        setLoading(false);
      }
    };
    generate();
  }, [matchingResultId]);

  const handleSave = async () => {
    if (!emailData) return;
    try {
      const response = await updateEmail(emailData.id, {
        subject: editSubject,
        body: editBody,
      });
      setEmailData(response.data);
      setEditing(false);
    } catch (err: any) {
      setError("Erreur lors de la sauvegarde");
    }
  };

  const handleValidate = async () => {
    if (!emailData) return;
    try {
      const response = await updateEmail(emailData.id, {
        status: "validated",
      });
      setEmailData(response.data);
    } catch (err: any) {
      setError("Erreur lors de la validation");
    }
  };

  const handleCopy = () => {
    const text = `Objet : ${editSubject}\n\n${editBody}`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto text-center py-16">
        <Loader2 className="w-12 h-12 text-primary-600 animate-spin mx-auto mb-4" />
        <p className="text-lg font-medium text-gray-900">
          Rédaction du mail en cours...
        </p>
        <p className="text-sm text-gray-500 mt-1">
          L&apos;IA génère un mail professionnel personnalisé
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Mail className="w-6 h-6" />
          Mail généré
        </h2>
        <div className="flex items-center gap-2">
          {emailData?.status === "validated" ? (
            <span className="flex items-center gap-1 px-3 py-1.5 bg-green-100 text-green-700 rounded-lg text-sm font-medium">
              <CheckCircle className="w-4 h-4" /> Validé
            </span>
          ) : (
            <>
              <button
                onClick={() => setEditing(!editing)}
                className="flex items-center gap-1 px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 transition-colors"
              >
                <Edit3 className="w-4 h-4" />
                {editing ? "Annuler" : "Modifier"}
              </button>
              <button
                onClick={handleValidate}
                className="flex items-center gap-1 px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 transition-colors font-medium"
              >
                <CheckCircle className="w-4 h-4" /> Valider
              </button>
            </>
          )}
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 transition-colors"
          >
            <Copy className="w-4 h-4" />
            {copied ? "Copié !" : "Copier"}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {/* Objet */}
        <div className="border-b border-gray-200 px-6 py-4">
          <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
            Objet
          </label>
          {editing ? (
            <input
              type="text"
              value={editSubject}
              onChange={(e) => setEditSubject(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
            />
          ) : (
            <p className="text-gray-900 font-medium">{editSubject}</p>
          )}
        </div>

        {/* Corps */}
        <div className="px-6 py-6">
          <label className="block text-xs font-medium text-gray-500 uppercase mb-2">
            Corps du mail
          </label>
          {editing ? (
            <textarea
              value={editBody}
              onChange={(e) => setEditBody(e.target.value)}
              rows={16}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none resize-y"
            />
          ) : (
            <div className="whitespace-pre-wrap text-gray-800 leading-relaxed">
              {editBody}
            </div>
          )}
        </div>

        {editing && (
          <div className="border-t border-gray-200 px-6 py-4 flex justify-end">
            <button
              onClick={handleSave}
              className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium text-sm"
            >
              Sauvegarder les modifications
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
