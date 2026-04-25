"use client";

import { useState } from "react";
import {
  Building,
  Key,
  Brain,
  Mail,
  ArrowRight,
  ArrowLeft,
  Check,
  Loader2,
  Rocket,
} from "lucide-react";
import { updateSettings } from "@/lib/api";
import { getApiErrorDetail } from "@/lib/utils";

interface SetupWizardProps {
  onComplete: () => void;
}

const STEPS = [
  { key: "company", label: "Entreprise", icon: Building },
  { key: "france_travail", label: "France Travail", icon: Key },
  { key: "ai", label: "Intelligence Artificielle", icon: Brain },
  { key: "hunter", label: "Hunter.io", icon: Mail },
] as const;

export default function SetupWizard({ onComplete }: SetupWizardProps) {
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Company
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [agencyPhone, setAgencyPhone] = useState("");
  const [agencyEmail, setAgencyEmail] = useState("");

  // France Travail
  const [ftClientId, setFtClientId] = useState("");
  const [ftSecret, setFtSecret] = useState("");

  // AI
  const [aiModel, setAiModel] = useState("alfred-4.2");
  const [aiBaseUrl, setAiBaseUrl] = useState(
    "https://trust.liveintelligence.orange-business.com/api/v2"
  );
  const [aiApiKey, setAiApiKey] = useState("");

  // Hunter
  const [hunterApiKey, setHunterApiKey] = useState("");

  const inputCls =
    "w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder:text-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none";
  const labelCls =
    "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1";

  const handleSaveStep = async () => {
    setSaving(true);
    setError(null);
    try {
      const currentStep = STEPS[step].key;
      if (currentStep === "company") {
        if (!firstName.trim() || !lastName.trim() || !companyName.trim()) {
          setError("Prénom, nom et nom de l'entreprise sont obligatoires.");
          setSaving(false);
          return;
        }
        await updateSettings({
          first_name: firstName,
          last_name: lastName,
          company_name: companyName,
          agency_phone: agencyPhone,
          agency_email: agencyEmail,
        });
      } else if (currentStep === "france_travail") {
        if (!ftClientId.trim() || !ftSecret.trim()) {
          setError(
            "Le Client ID et le Client Secret France Travail sont obligatoires."
          );
          setSaving(false);
          return;
        }
        await updateSettings({
          france_travail_client_id: ftClientId,
          france_travail_client_secret: ftSecret,
        });
      } else if (currentStep === "ai") {
        const data: any = { ai_model: aiModel, ai_base_url: aiBaseUrl };
        if (aiApiKey) data.ai_api_key = aiApiKey;
        await updateSettings(data);
      } else if (currentStep === "hunter") {
        if (hunterApiKey.trim()) {
          await updateSettings({ hunter_api_key: hunterApiKey });
        }
      }

      // Next step or complete
      if (step < STEPS.length - 1) {
        setStep(step + 1);
      } else {
        onComplete();
      }
    } catch (err: unknown) {
      setError(
        getApiErrorDetail(err, "Erreur lors de la sauvegarde")
      );
    } finally {
      setSaving(false);
    }
  };

  const renderStepContent = () => {
    const currentStep = STEPS[step].key;

    if (currentStep === "company") {
      return (
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Ces informations seront utilisées dans les emails envoyés aux
            recruteurs.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>
                Prénom <span className="text-red-500">*</span>
              </label>
              <input
                className={inputCls}
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                placeholder="Jean"
              />
            </div>
            <div>
              <label className={labelCls}>
                Nom <span className="text-red-500">*</span>
              </label>
              <input
                className={inputCls}
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder="Dupont"
              />
            </div>
          </div>
          <div>
            <label className={labelCls}>
              Nom de l&apos;entreprise <span className="text-red-500">*</span>
            </label>
            <input
              className={inputCls}
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="Mon Agence Intérim SAS"
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Téléphone</label>
              <input
                className={inputCls}
                value={agencyPhone}
                onChange={(e) => setAgencyPhone(e.target.value)}
                placeholder="01 23 45 67 89"
              />
            </div>
            <div>
              <label className={labelCls}>Email de l&apos;agence</label>
              <input
                type="email"
                className={inputCls}
                value={agencyEmail}
                onChange={(e) => setAgencyEmail(e.target.value)}
                placeholder="contact@agence.fr"
              />
            </div>
          </div>
        </div>
      );
    }

    if (currentStep === "france_travail") {
      return (
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Créez un compte développeur sur{" "}
            <a
              href="https://francetravail.io"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary-600 hover:underline font-medium"
            >
              francetravail.io
            </a>{" "}
            pour obtenir vos identifiants API (gratuit).
          </p>
          <div>
            <label className={labelCls}>
              Client ID <span className="text-red-500">*</span>
            </label>
            <input
              className={inputCls}
              value={ftClientId}
              onChange={(e) => setFtClientId(e.target.value)}
              placeholder="Identifiant client France Travail"
            />
          </div>
          <div>
            <label className={labelCls}>
              Client Secret <span className="text-red-500">*</span>
            </label>
            <input
              type="password"
              className={inputCls}
              value={ftSecret}
              onChange={(e) => setFtSecret(e.target.value)}
              placeholder="Secret client France Travail"
            />
          </div>
        </div>
      );
    }

    if (currentStep === "ai") {
      return (
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Configurez le modèle d&apos;IA utilisé pour l&apos;analyse des CV et le
            matching. Les valeurs par défaut fonctionnent avec Paradigm
            (Orange).
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Modèle</label>
              <input
                className={inputCls}
                value={aiModel}
                onChange={(e) => setAiModel(e.target.value)}
                placeholder="alfred-4.2"
              />
            </div>
            <div>
              <label className={labelCls}>Endpoint (URL de base)</label>
              <input
                className={inputCls}
                value={aiBaseUrl}
                onChange={(e) => setAiBaseUrl(e.target.value)}
                placeholder="https://api.openai.com/v1"
              />
            </div>
          </div>
          <div>
            <label className={labelCls}>Clé API IA</label>
            <input
              type="password"
              className={inputCls}
              value={aiApiKey}
              onChange={(e) => setAiApiKey(e.target.value)}
              placeholder="Laisser vide si pas nécessaire"
            />
          </div>
        </div>
      );
    }

    if (currentStep === "hunter") {
      return (
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            <strong>Optionnel.</strong> Hunter.io permet de trouver
            automatiquement l&apos;email du recruteur quand il n&apos;est pas dans
            l&apos;offre.{" "}
            <a
              href="https://hunter.io"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary-600 hover:underline font-medium"
            >
              Créer un compte gratuit
            </a>{" "}
            (50 recherches/mois).
          </p>
          <div>
            <label className={labelCls}>Clé API Hunter.io</label>
            <input
              type="password"
              className={inputCls}
              value={hunterApiKey}
              onChange={(e) => setHunterApiKey(e.target.value)}
              placeholder="Laisser vide pour ignorer"
            />
          </div>
        </div>
      );
    }

    return null;
  };

  const CurrentIcon = STEPS[step].icon;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center p-6">
      <div className="w-full max-w-xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary-100 dark:bg-primary-900/30 mb-4">
            <Rocket className="w-8 h-8 text-primary-600 dark:text-primary-400" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Bienvenue sur InteriMatch
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Configurons votre espace de travail en quelques étapes
          </p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {STEPS.map((s, i) => {
            const Icon = s.icon;
            return (
              <div key={s.key} className="flex items-center gap-2">
                <div
                  className={`flex items-center justify-center w-9 h-9 rounded-full text-sm font-medium transition-colors ${
                    i < step
                      ? "bg-green-500 text-white"
                      : i === step
                      ? "bg-primary-600 text-white"
                      : "bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400"
                  }`}
                >
                  {i < step ? <Check className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                </div>
                {i < STEPS.length - 1 && (
                  <div
                    className={`w-8 h-0.5 ${
                      i < step
                        ? "bg-green-500"
                        : "bg-gray-200 dark:bg-gray-700"
                    }`}
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Card */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm p-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary-100 dark:bg-primary-900/30">
              <CurrentIcon className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {STEPS[step].label}
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Étape {step + 1} sur {STEPS.length}
              </p>
            </div>
          </div>

          {renderStepContent()}

          {error && (
            <div className="mt-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3 text-sm text-red-700 dark:text-red-400">
              {error}
            </div>
          )}

          {/* Navigation */}
          <div className="flex items-center justify-between mt-8 pt-6 border-t border-gray-100 dark:border-gray-700">
            {step > 0 ? (
              <button
                onClick={() => {
                  setStep(step - 1);
                  setError(null);
                }}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                Retour
              </button>
            ) : (
              <div />
            )}
            <button
              onClick={handleSaveStep}
              disabled={saving}
              className="flex items-center gap-2 px-6 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium disabled:opacity-50"
            >
              {saving ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : step < STEPS.length - 1 ? (
                <>
                  Suivant
                  <ArrowRight className="w-4 h-4" />
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  Terminer
                </>
              )}
            </button>
          </div>
        </div>

        {/* Skip option for optional steps */}
        {(STEPS[step].key === "ai" || STEPS[step].key === "hunter") && (
          <div className="text-center mt-4">
            <button
              onClick={() => {
                if (step < STEPS.length - 1) {
                  setStep(step + 1);
                  setError(null);
                } else {
                  onComplete();
                }
              }}
              className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
            >
              Passer cette étape →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}