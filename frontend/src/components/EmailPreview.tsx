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
  ChevronDown,
  Search,
  Users,
  X,
  RefreshCw,
} from "lucide-react";
import { generateEmail, updateEmail, getMe, downloadAnonymizedCV, downloadEmailEml, lookupRecruiter, getCompanyContacts, getCompanyContactsByName, updateEmailRecipients } from "@/lib/api";

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
  const [selectedRecipients, setSelectedRecipients] = useState<string[]>([]);
  const [companyContacts, setCompanyContacts] = useState<
    { email: string; first_name: string; last_name: string; position: string; department: string; confidence: number; company_name?: string }[]
  >([]);
  const [contactsLoading, setContactsLoading] = useState(false);
  const [contactsError, setContactsError] = useState<string | null>(null);
  const [showContactDropdown, setShowContactDropdown] = useState(false);
  const [companyDomain, setCompanyDomain] = useState<string | null>(null);
  const [companyName, setCompanyName] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
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

  // Close dropdown on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowContactDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const loadCompanyContacts = async (domain?: string, company?: string) => {
    if (!domain && !company) return;
    setContactsLoading(true);
    setContactsError(null);
    try {
      let res;
      if (company) {
        // Primary path: 3-step flow via company name
        // Backend cleans name → Hunter resolves domain → Hunter returns contacts
        console.log("[Hunter] 3-step lookup for company name:", company);
        res = await getCompanyContactsByName(company);
        const payload = res.data;
        // New response format: {cleaned_name, domain, contacts}
        const contacts = Array.isArray(payload) ? payload : (payload.contacts || []);
        const resolvedDomain = payload.domain || null;
        const cleanedName = payload.cleaned_name || company;
        console.log("[Hunter] Cleaned:", cleanedName, "→ Domain:", resolvedDomain, "→ Contacts:", contacts.length);
        setCompanyContacts(contacts);
        if (resolvedDomain) setCompanyDomain(resolvedDomain);
        if (cleanedName) setCompanyName(cleanedName);
      } else if (domain) {
        // Fallback: search by domain directly
        console.log("[Hunter] Loading contacts for domain:", domain);
        res = await getCompanyContacts(domain);
        const data = Array.isArray(res.data) ? res.data : [];
        setCompanyContacts(data);
      }
    } catch (err: any) {
      console.error("[Hunter] Error loading contacts:", err);
      setContactsError(err?.response?.data?.detail || "Erreur lors du chargement des contacts");
    } finally {
      setContactsLoading(false);
    }
  };

  const toggleRecipient = (email: string) => {
    setSelectedRecipients((prev) => {
      const next = prev.includes(email) ? prev.filter((e) => e !== email) : [...prev, email];
      // Persist to backend
      if (emailData) {
        updateEmailRecipients(emailData.id, next.join(", ")).catch(() => {});
      }
      return next;
    });
  };

  const removeRecipient = (email: string) => {
    setSelectedRecipients((prev) => {
      const next = prev.filter((e) => e !== email);
      if (emailData) {
        updateEmailRecipients(emailData.id, next.join(", ")).catch(() => {});
      }
      return next;
    });
  };

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

        // Lookup recruiter info once (reuse for email + domain)
        let recruiterContact: Record<string, string> = {};
        let offerCompanyName: string | null = null;
        if (jobOfferId) {
          try {
            const rRes = await lookupRecruiter(jobOfferId);
            recruiterContact = rRes.data.contact || {};
            offerCompanyName = rRes.data.company_name || null;
            if (!rEmail) {
              const ce = recruiterContact.contact_email;
              if (ce && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(ce)) rEmail = ce;
            }
          } catch {
            // silently fail
          }
        }

        setRecruiterEmail(rEmail);
        if (rEmail) setSelectedRecipients([rEmail]);

        // 3-step contact lookup:
        // 1) Clean company name (done by backend)
        // 2) Hunter resolves company name → domain
        // 3) Hunter returns contacts at that domain
        //
        // Always prefer company name from the job offer — the backend
        // cleans it (strips "- voir rce …" etc.) and lets Hunter resolve
        // the real domain.
        if (offerCompanyName) {
          setCompanyName(offerCompanyName);
          loadCompanyContacts(undefined, offerCompanyName);
        }

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
          const to = selectedRecipients.length > 0 ? encodeURIComponent(selectedRecipients.join(", ")) : "";
          const subject = encodeURIComponent(editSubject);
          const body = encodeURIComponent(editBody);
          window.location.href = `mailto:${to}?subject=${subject}&body=${body}`;
        }
      } else {
        const to = selectedRecipients.length > 0 ? encodeURIComponent(selectedRecipients.join(", ")) : "";
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
                  const to = selectedRecipients.length > 0 ? encodeURIComponent(selectedRecipients.join(", ")) : "";
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
        {/* Destinataire(s) */}
        <div className="border-b border-gray-200 dark:border-gray-700 px-6 py-3">
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">
            Destinataire(s)
          </label>

          {/* Selected recipients chips */}
          <div className="flex flex-wrap items-center gap-2 min-h-[32px]" ref={dropdownRef}>
            {selectedRecipients.map((email) => {
              const contactInfo = companyContacts.find((c) => c.email === email);
              const hasName = contactInfo && (`${contactInfo.first_name} ${contactInfo.last_name}`.trim());
              return (
                <span
                  key={email}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 rounded-full text-sm font-medium"
                  title={contactInfo?.position ? `${contactInfo.position} — ${email}` : email}
                >
                  <span>
                    {hasName ? `${contactInfo.first_name} ${contactInfo.last_name}`.trim() : email}
                    {contactInfo?.position && (
                      <span className="text-xs text-primary-500 dark:text-primary-300 ml-1">
                        ({contactInfo.position})
                      </span>
                    )}
                    {hasName && (
                      <span className="text-xs text-primary-400 dark:text-primary-500 ml-1">
                        &lt;{email}&gt;
                      </span>
                    )}
                  </span>
                  <button
                    onClick={() => removeRecipient(email)}
                    className="hover:text-red-500 transition-colors flex-shrink-0"
                  >
                  <X className="w-3.5 h-3.5" />
                </button>
              </span>
              );
            })}

            {selectedRecipients.length === 0 && !companyContacts.length && (
              <p className="text-amber-600 dark:text-amber-400 text-sm flex items-center gap-1">
                <AlertTriangle className="w-4 h-4" />
                Email du recruteur non trouvé — il sera à renseigner manuellement
              </p>
            )}

            {/* Dropdown trigger */}
            <div className="relative">
              <button
                onClick={() => {
                  setShowContactDropdown(!showContactDropdown);
                  if (!showContactDropdown && companyContacts.length === 0 && !contactsLoading) {
                    if (companyDomain) {
                      loadCompanyContacts(companyDomain);
                    } else if (companyName) {
                      loadCompanyContacts(undefined, companyName);
                    }
                  }
                }}
                className="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <Users className="w-3.5 h-3.5" />
                {companyContacts.length > 0
                  ? `${companyContacts.length} contacts`
                  : "Contacts"}
                <ChevronDown className="w-3.5 h-3.5" />
              </button>

              {showContactDropdown && (
                <div className="absolute top-full left-0 mt-1 w-96 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg z-50 max-h-72 overflow-y-auto">
                  {contactsLoading ? (
                    <div className="flex flex-col items-center justify-center py-6">
                      <Loader2 className="w-5 h-5 animate-spin text-primary-500" />
                      <span className="mt-2 text-sm text-gray-500">
                        Recherche des contacts{companyName ? ` pour ${companyName}` : ""}...
                      </span>
                      <span className="text-xs text-gray-400 mt-1">Résolution du domaine via Hunter.io</span>
                    </div>
                  ) : companyContacts.length === 0 ? (
                    <div className="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
                      <Search className="w-5 h-5 mx-auto mb-2 text-gray-400" />
                      {contactsError ? (
                        <p className="text-red-500 dark:text-red-400 mb-2">{contactsError}</p>
                      ) : companyDomain || companyName ? (
                        <>
                          <p className="mb-1">Aucun contact trouvé pour <strong>{companyName || companyDomain}</strong>.</p>
                          {companyDomain && (
                            <p className="text-xs text-gray-400">Domaine résolu : {companyDomain}</p>
                          )}
                        </>
                      ) : (
                        <p className="mb-1">Aucun nom d&apos;entreprise détecté pour cette offre.</p>
                      )}
                      {(companyDomain || companyName) && (
                        <button
                          onClick={() => loadCompanyContacts(companyDomain || undefined, companyDomain ? undefined : companyName || undefined)}
                          className="mt-2 px-3 py-1.5 text-xs font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                        >
                          <RefreshCw className="w-3 h-3 inline mr-1" />
                          Réessayer
                        </button>
                      )}
                    </div>
                  ) : (
                    <div className="py-1">
                      <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-100 dark:border-gray-700">
                        Contacts — {companyContacts[0]?.company_name || companyName || companyDomain}
                        {companyDomain && (
                          <span className="ml-1 normal-case font-normal text-gray-400">({companyDomain})</span>
                        )}
                      </div>
                      {companyContacts.map((contact) => {
                        const isSelected = selectedRecipients.includes(contact.email);
                        return (
                          <button
                            key={contact.email}
                            onClick={() => toggleRecipient(contact.email)}
                            className={`w-full text-left px-3 py-2.5 flex items-center gap-3 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors ${
                              isSelected ? "bg-primary-50 dark:bg-primary-900/20" : ""
                            }`}
                          >
                            <div className={`w-5 h-5 flex-shrink-0 rounded border-2 flex items-center justify-center transition-colors ${
                              isSelected
                                ? "bg-primary-600 border-primary-600"
                                : "border-gray-300 dark:border-gray-600"
                            }`}>
                              {isSelected && <CheckCircle className="w-3.5 h-3.5 text-white" />}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                                {contact.first_name} {contact.last_name}
                                {contact.position && (
                                  <span className="ml-1 text-xs text-gray-500 dark:text-gray-400">
                                    — {contact.position}
                                  </span>
                                )}
                              </p>
                              <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                {contact.email}
                                {contact.department && (
                                  <span className="ml-1 px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-[10px]">
                                    {contact.department}
                                  </span>
                                )}
                              </p>
                            </div>
                            <span className="text-[10px] text-gray-400">{contact.confidence}%</span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
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
