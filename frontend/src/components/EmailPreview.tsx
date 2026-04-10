"use client";

import { useEffect, useRef, useState } from "react";
import {
  Mail,
  Loader2,
  CheckCircle,
  Edit3,
  Copy,
  ExternalLink,
  Download,
  AlertTriangle,
} from "lucide-react";
import { generateEmail, updateEmail, getMe, downloadAnonymizedCV, downloadEmailEml, lookupRecruiter } from "@/lib/api";

interface EmailPreviewProps {
  matchingResultId: string;
  candidateId?: string;
  jobOfferId?: string;
}

function replaceSenderPlaceholders(
  text: string,
  firstName: string,
  lastName: string,
  company: string,
  agencyPhone: string = "",
  agencyEmail: string = "",
  agencyAddress: string = "",
): string {
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
    [/\[Votre numéro de téléphone\]/gi, agencyPhone],
    [/\[Téléphone\]/gi, agencyPhone],
    [/\[Votre téléphone\]/gi, agencyPhone],
    [/\[Votre email\]/gi, agencyEmail],
    [/\[Email de l'agence\]/gi, agencyEmail],
    [/\[Votre adresse\]/gi, agencyAddress],
    [/\[Adresse de l'agence\]/gi, agencyAddress],
    [/\[Adresse\]/gi, agencyAddress],
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
  candidateId,
  jobOfferId,
}: EmailPreviewProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [emailData, setEmailData] = useState<any>(null);
  const [editing, setEditing] = useState(false);
  const [editSubject, setEditSubject] = useState("");
  const [editBody, setEditBody] = useState("");
  const [copied, setCopied] = useState(false);
  const [recruiterEmail, setRecruiterEmail] = useState<string | null>(null);
  const generatedForIdRef = useRef<string | null>(null);
  const senderInfoRef = useRef<{
    firstName: string;
    lastName: string;
    company: string;
    agencyPhone: string;
    agencyEmail: string;
    agencyAddress: string;
  }>({
    firstName: "",
    lastName: "",
    company: "",
    agencyPhone: "",
    agencyEmail: "",
    agencyAddress: "",
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
          agencyPhone: s.agency_phone || "",
          agencyEmail: s.agency_email || "",
          agencyAddress: s.agency_address || "",
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
        // Recruiter email: from backend response — validate it's an actual email
        const rawEmail = response.data.recruiter_email;
        let rEmail = (rawEmail && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(rawEmail)) ? rawEmail : null;
        if (!rEmail && jobOfferId) {
          try {
            const rRes = await lookupRecruiter(jobOfferId);
            rEmail = rRes.data.contact?.contact_email || null;
          } catch {
            // silently fail
          }
        }
        setRecruiterEmail(rEmail);
        const { firstName, lastName, company, agencyPhone, agencyEmail, agencyAddress } = senderInfoRef.current;
        setEditSubject(
          replaceSenderPlaceholders(response.data.subject, firstName, lastName, company, agencyPhone, agencyEmail, agencyAddress)
        );
        setEditBody(
          replaceSenderPlaceholders(response.data.body, firstName, lastName, company, agencyPhone, agencyEmail, agencyAddress)
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

      // Download .eml file with the anonymized CV attached
      if (candidateId) {
        try {
          const res = await downloadEmailEml(emailData.id, candidateId);
          const url = window.URL.createObjectURL(new Blob([res.data], { type: "message/rfc822" }));
          const a = document.createElement("a");
          a.href = url;
          a.download = "email_proposition.eml";
          document.body.appendChild(a);
          a.click();
          a.remove();
          window.URL.revokeObjectURL(url);
        } catch {
          // Fallback to mailto: if .eml download fails
          const to = recruiterEmail ? encodeURIComponent(recruiterEmail) : "";
          const subject = encodeURIComponent(editSubject);
          const body = encodeURIComponent(editBody);
          window.location.href = `mailto:${to}?subject=${subject}&body=${body}`;
        }
      } else {
        const to = recruiterEmail ? encodeURIComponent(recruiterEmail) : "";
        const subject = encodeURIComponent(editSubject);
        const body = encodeURIComponent(editBody);
        window.location.href = `mailto:${to}?subject=${subject}&body=${body}`;
      }
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

  const handleDownloadAnonymizedCV = async () => {
    if (!candidateId) return;
    try {
      const res = await downloadAnonymizedCV(candidateId);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = "cv_anonymise.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      // silently fail
    }
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
                onClick={async () => {
                  if (candidateId && emailData) {
                    try {
                      const res = await downloadEmailEml(emailData.id, candidateId);
                      const url = window.URL.createObjectURL(new Blob([res.data], { type: "message/rfc822" }));
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = "email_proposition.eml";
                      document.body.appendChild(a);
                      a.click();
                      a.remove();
                      window.URL.revokeObjectURL(url);
                      return;
                    } catch {
                      // fallback below
                    }
                  }
                  const to = recruiterEmail ? encodeURIComponent(recruiterEmail) : "";
                  const subject = encodeURIComponent(editSubject);
                  const body = encodeURIComponent(editBody);
                  window.location.href = `mailto:${to}?subject=${subject}&body=${body}`;
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
          {candidateId && (
            <button
              onClick={handleDownloadAnonymizedCV}
              className="flex items-center gap-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <Download className="w-4 h-4" />
              CV anonymisé
            </button>
          )}
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {/* Destinataire */}
        <div className="border-b border-gray-200 dark:border-gray-700 px-6 py-3">
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">
            Destinataire
          </label>
          {recruiterEmail ? (
            <p className="text-gray-900 dark:text-white font-medium">{recruiterEmail}</p>
          ) : (
            <p className="text-amber-600 dark:text-amber-400 text-sm flex items-center gap-1">
              <AlertTriangle className="w-4 h-4" />
              Email du recruteur non trouvé — il sera à renseigner manuellement
            </p>
          )}
        </div>

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
