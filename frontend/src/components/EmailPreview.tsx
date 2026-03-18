"use client";

import { useEffect, useRef, useState } from "react";
import {
  Mail,
  Loader2,
  CheckCircle,
  Edit3,
  Copy,
  ExternalLink,
} from "lucide-react";
import { generateEmail, updateEmail, getMe } from "@/lib/api";

interface EmailPreviewProps {
  matchingResultId: string;
}

function replaceSenderPlaceholders(text: string, firstName: string, lastName: string, company: string): string {
  // Replace common placeholder patterns the LLM might generate
  let result = text;
  const fullName = `${firstName} ${lastName}`.trim();
  const replacements: [RegExp, string][] = [
    [/\[Votre Prénom\]/gi, firstName],
    [/\[Votre Nom\]/gi, lastName],
    [/\[Prénom\]/gi, firstName],
    [/\[Nom\]/gi, lastName],
    [/\[Votre Prénom Nom\]/gi, fullName],
    [/\[Votre nom complet\]/gi, fullName],
    [/\[Votre nom\]/gi, fullName],
    [/\[Nom Prénom\]/gi, fullName],
    [/\[Prénom Nom\]/gi, fullName],
    [/\[Nom de votre agence\]/gi, company],
    [/\[Nom de l'agence\]/gi, company],
    [/\[Nom de votre entreprise\]/gi, company],
    [/\[Votre entreprise\]/gi, company],
    [/\[Nom de l'entreprise d'intérim\]/gi, company],
    [/\[Agence\]/gi, company],
    [/\[Votre agence\]/gi, company],
    [/\[Nom agence\]/gi, company],
    [/\[Votre société\]/gi, company],
  ];
  for (const [pattern, replacement] of replacements) {
    if (replacement) {
      result = result.replace(pattern, replacement);
    }
  }
  return result;
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
  const generatedForIdRef = useRef<string | null>(null);
  const senderInfoRef = useRef<{ firstName: string; lastName: string; company: string }>({
    firstName: "",
    lastName: "",
    company: "",
  });

  // Load user settings once
  useEffect(() => {
    const loadSender = async () => {
      try {
        const res = await getMe();
        const s = res.data.settings;
        senderInfoRef.current = {
          firstName: s.first_name || "",
          lastName: s.last_name || "",
          company: s.company_name || "",
        };
      } catch {
        // silently fail — placeholders just won't be replaced
      }
    };
    loadSender();
  }, []);

  useEffect(() => {
    if (generatedForIdRef.current === matchingResultId) {
      return;
    }
    generatedForIdRef.current = matchingResultId;

    const generate = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await generateEmail(matchingResultId);
        setEmailData(response.data);
        const { firstName, lastName, company } = senderInfoRef.current;
        setEditSubject(
          replaceSenderPlaceholders(response.data.subject, firstName, lastName, company)
        );
        setEditBody(
          replaceSenderPlaceholders(response.data.body, firstName, lastName, company)
        );
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
    } catch {
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

      // Open default mail client with pre-filled content
      const subject = encodeURIComponent(editSubject);
      const body = encodeURIComponent(editBody);
      window.location.href = `mailto:?subject=${subject}&body=${body}`;
    } catch {
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
        <p className="text-lg font-medium text-gray-900 dark:text-white">
          Rédaction du mail en cours...
        </p>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          L&apos;IA génère un mail professionnel personnalisé
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Mail className="w-6 h-6" />
          Mail généré
        </h2>
        <div className="flex items-center gap-2">
          {emailData?.status === "validated" ? (
            <>
              <span className="flex items-center gap-1 px-3 py-1.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-lg text-sm font-medium">
                <CheckCircle className="w-4 h-4" /> Validé
              </span>
              <button
                onClick={() => {
                  const subject = encodeURIComponent(editSubject);
                  const body = encodeURIComponent(editBody);
                  window.location.href = `mailto:?subject=${subject}&body=${body}`;
                }}
                className="flex items-center gap-1 px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 transition-colors font-medium"
              >
                <ExternalLink className="w-4 h-4" /> Ouvrir dans la messagerie
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => setEditing(!editing)}
                className="flex items-center gap-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <Edit3 className="w-4 h-4" />
                {editing ? "Annuler" : "Modifier"}
              </button>
              <button
                onClick={handleValidate}
                className="flex items-center gap-1 px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 transition-colors font-medium"
              >
                <CheckCircle className="w-4 h-4" /> Valider & Envoyer
              </button>
            </>
          )}
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            <Copy className="w-4 h-4" />
            {copied ? "Copié !" : "Copier"}
          </button>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {/* Objet */}
        <div className="border-b border-gray-200 dark:border-gray-700 px-6 py-4">
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">
            Objet
          </label>
          {editing ? (
            <input
              type="text"
              value={editSubject}
              onChange={(e) => setEditSubject(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
            />
          ) : (
            <p className="text-gray-900 dark:text-white font-medium">{editSubject}</p>
          )}
        </div>

        {/* Corps */}
        <div className="px-6 py-6">
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-2">
            Corps du mail
          </label>
          {editing ? (
            <textarea
              value={editBody}
              onChange={(e) => setEditBody(e.target.value)}
              rows={16}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none resize-y"
            />
          ) : (
            <div className="whitespace-pre-wrap text-gray-800 dark:text-gray-200 leading-relaxed">
              {editBody}
            </div>
          )}
        </div>

        {editing && (
          <div className="border-t border-gray-200 dark:border-gray-700 px-6 py-4 flex justify-end">
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
