"use client";

import { useEffect, useState } from "react";
import {
  Save,
  Loader2,
  Sun,
  Moon,
  Monitor,
  Lock,
  Building,
  User,
  Brain,
  Key,
  Shield,
  Check,
  AlertCircle,
  MapPin,
  Phone,
  Mail,
  FileText,
  ShieldCheck,
  ShieldOff,
} from "lucide-react";
import { getMe, updateSettings, changePassword, setup2FA, verify2FA, disable2FA, getAiProviders } from "@/lib/api";

interface SettingsData {
  first_name: string;
  last_name: string;
  company_name: string;
  theme: string;
  agency_address: string;
  agency_phone: string;
  agency_email: string;
  agency_siret: string;
  email_template: string;
  ai_provider: string;
  ai_model: string;
  ai_base_url: string;
  ai_temperature: number | null;
  ai_api_key_set: boolean;
  france_travail_client_id: string;
  france_travail_secret_set: boolean;
  hunter_api_key_set: boolean;
  smtp_host: string;
  smtp_port: number | null;
  smtp_user: string;
  smtp_password_set: boolean;
  smtp_use_tls: boolean;
  smtp_from: string;
  setup_completed: boolean;
  totp_enabled: boolean;
}

interface SettingsProps {
  onThemeChange: (theme: string) => void;
}

/* ─── 2FA Sub-component ──────────────────────────────────────────────── */
function TwoFactorSection({
  totpEnabled,
  onStatusChange,
  onError,
}: {
  totpEnabled: boolean;
  onStatusChange: (enabled: boolean) => void;
  onError: (msg: string) => void;
}) {
  const [step, setStep] = useState<"idle" | "setup" | "disable">("idle");
  const [qrCode, setQrCode] = useState<string | null>(null);
  const [secret, setSecret] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);

  const handleStartSetup = async () => {
    setLoading(true);
    try {
      const res = await setup2FA();
      setQrCode(res.data.qr_code);
      setSecret(res.data.secret);
      setStep("setup");
      setCode("");
    } catch (err: any) {
      onError(err.response?.data?.detail || "Erreur lors de la configuration 2FA");
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    if (code.length !== 6) return;
    setLoading(true);
    try {
      await verify2FA(code);
      onStatusChange(true);
      setStep("idle");
      setQrCode(null);
      setSecret(null);
      setCode("");
    } catch (err: any) {
      onError(err.response?.data?.detail || "Code invalide");
    } finally {
      setLoading(false);
    }
  };

  const handleDisable = async () => {
    if (code.length !== 6) return;
    setLoading(true);
    try {
      await disable2FA(code);
      onStatusChange(false);
      setStep("idle");
      setCode("");
    } catch (err: any) {
      onError(err.response?.data?.detail || "Code invalide");
    } finally {
      setLoading(false);
    }
  };

  if (step === "setup" && qrCode) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 mb-2">
          <Shield className="w-5 h-5 text-primary-500" />
          <p className="text-sm font-medium text-gray-900 dark:text-white">
            Configurer l&apos;authentification 2FA
          </p>
        </div>
        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 space-y-3">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            1. Scannez ce QR code avec votre application d&apos;authentification (Google Authenticator, Authy, etc.)
          </p>
          <div className="flex justify-center py-2">
            <img src={qrCode} alt="QR Code 2FA" className="w-48 h-48 rounded-lg" />
          </div>
          <details className="text-xs text-gray-500 dark:text-gray-400">
            <summary className="cursor-pointer hover:text-gray-700 dark:hover:text-gray-300">
              Ou entrez ce code manuellement
            </summary>
            <code className="block mt-1 bg-gray-200 dark:bg-gray-600 px-3 py-1.5 rounded font-mono text-sm break-all">
              {secret}
            </code>
          </details>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            2. Entrez le code à 6 chiffres affiché par l&apos;application :
          </p>
          <div className="flex items-center gap-3">
            <input
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              className="w-40 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-center text-lg tracking-widest font-mono focus:ring-2 focus:ring-primary-500 outline-none"
              placeholder="000000"
            />
            <button
              onClick={handleVerify}
              disabled={loading || code.length !== 6}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
              Activer
            </button>
            <button
              onClick={() => { setStep("idle"); setQrCode(null); setSecret(null); }}
              className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              Annuler
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (step === "disable") {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 mb-2">
          <ShieldOff className="w-5 h-5 text-red-500" />
          <p className="text-sm font-medium text-gray-900 dark:text-white">
            Désactiver la 2FA
          </p>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Entrez un code de votre application d&apos;authentification pour confirmer :
        </p>
        <div className="flex items-center gap-3">
          <input
            type="text"
            inputMode="numeric"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            className="w-40 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-center text-lg tracking-widest font-mono focus:ring-2 focus:ring-primary-500 outline-none"
            placeholder="000000"
          />
          <button
            onClick={handleDisable}
            disabled={loading || code.length !== 6}
            className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldOff className="w-4 h-4" />}
            Désactiver
          </button>
          <button
            onClick={() => { setStep("idle"); setCode(""); }}
            className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            Annuler
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Shield className="w-5 h-5 text-gray-500" />
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">
            Authentification à deux facteurs (2FA)
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {totpEnabled
              ? "Activée — Protection renforcée"
              : "Désactivée — Ajoutez une couche de sécurité"}
          </p>
        </div>
      </div>
      {totpEnabled ? (
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
            Actif
          </span>
          <button
            onClick={() => { setStep("disable"); setCode(""); }}
            className="text-xs text-red-600 dark:text-red-400 hover:underline"
          >
            Désactiver
          </button>
        </div>
      ) : (
        <button
          onClick={handleStartSetup}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-xs font-medium disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
          Activer
        </button>
      )}
    </div>
  );
}

export default function Settings({ onThemeChange }: SettingsProps) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Profil
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [email, setEmail] = useState("");

  // Thème
  const [theme, setTheme] = useState("system");

  // Sécurité
  const [currentPwd, setCurrentPwd] = useState("");
  const [newPwd, setNewPwd] = useState("");
  const [confirmPwd, setConfirmPwd] = useState("");
  const [pwdSaving, setPwdSaving] = useState(false);

  // IA
  const [aiProvider, setAiProvider] = useState("custom");
  const [aiProviders, setAiProviders] = useState<
    { id: string; label: string; base_url: string; default_model: string; requires_key: boolean; docs: string }[]
  >([]);
  const [aiModel, setAiModel] = useState("");
  const [aiBaseUrl, setAiBaseUrl] = useState("");
  const [aiTemp, setAiTemp] = useState("");
  const [aiApiKey, setAiApiKey] = useState("");
  const [aiKeySet, setAiKeySet] = useState(false);

  // France Travail
  const [ftClientId, setFtClientId] = useState("");
  const [ftSecret, setFtSecret] = useState("");
  const [ftSecretSet, setFtSecretSet] = useState(false);

  // Agence
  const [agencyAddress, setAgencyAddress] = useState("");
  const [agencyPhone, setAgencyPhone] = useState("");
  const [agencyEmail, setAgencyEmail] = useState("");
  const [agencySiret, setAgencySiret] = useState("");

  // Modèle d'email
  const [emailTemplate, setEmailTemplate] = useState("");

  // Hunter.io
  const [hunterApiKey, setHunterApiKey] = useState("");
  const [hunterKeySet, setHunterKeySet] = useState(false);

  // SMTP
  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState<string>("");
  const [smtpUser, setSmtpUser] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [smtpPasswordSet, setSmtpPasswordSet] = useState(false);
  const [smtpUseTls, setSmtpUseTls] = useState(true);
  const [smtpFrom, setSmtpFrom] = useState("");

  // 2FA
  const [totpEnabled, setTotpEnabled] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await getMe();
        const u = res.data;
        setEmail(u.email);
        const s: SettingsData = u.settings;
        setFirstName(s.first_name);
        setLastName(s.last_name);
        setCompanyName(s.company_name);
        setTheme(s.theme);
        setAiModel(s.ai_model);
        setAiBaseUrl(s.ai_base_url || "");
        setAiTemp(s.ai_temperature != null ? String(s.ai_temperature) : "");
        setAiKeySet(s.ai_api_key_set);
        setAiProvider(s.ai_provider || "custom");
        setFtClientId(s.france_travail_client_id);
        setFtSecretSet(s.france_travail_secret_set);
        setAgencyAddress(s.agency_address || "");
        setAgencyPhone(s.agency_phone || "");
        setAgencyEmail(s.agency_email || "");
        setAgencySiret(s.agency_siret || "");
        setEmailTemplate(s.email_template || "");
        setHunterKeySet(s.hunter_api_key_set);
        setSmtpHost(s.smtp_host || "");
        setSmtpPort(s.smtp_port != null ? String(s.smtp_port) : "");
        setSmtpUser(s.smtp_user || "");
        setSmtpPasswordSet(s.smtp_password_set);
        setSmtpUseTls(s.smtp_use_tls);
        setSmtpFrom(s.smtp_from || "");
        setTotpEnabled(s.totp_enabled);
      } catch {
        setError("Impossible de charger les paramètres");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  // Charge la liste des providers IA disponibles (presets)
  useEffect(() => {
    getAiProviders()
      .then((res) => setAiProviders(res.data || []))
      .catch(() => {});
  }, []);

  const flash = (msg: string) => {
    setSuccess(msg);
    setError(null);
    setTimeout(() => setSuccess(null), 3000);
  };

  const flashError = (msg: string) => {
    setError(msg);
    setSuccess(null);
    setTimeout(() => setError(null), 5000);
  };

  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      await updateSettings({
        email,
        first_name: firstName,
        last_name: lastName,
        company_name: companyName,
      });
      flash("Profil mis à jour");
    } catch (err: any) {
      flashError(err.response?.data?.detail || "Erreur de sauvegarde");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveTheme = async (t: string) => {
    setTheme(t);
    onThemeChange(t);
    try {
      await updateSettings({ theme: t });
    } catch {
      // silent
    }
  };

  const handleChangePassword = async () => {
    if (newPwd !== confirmPwd) {
      flashError("Les mots de passe ne correspondent pas");
      return;
    }
    setPwdSaving(true);
    try {
      await changePassword(currentPwd, newPwd);
      flash("Mot de passe mis à jour");
      setCurrentPwd("");
      setNewPwd("");
      setConfirmPwd("");
    } catch (err: any) {
      flashError(
        err.response?.data?.detail || "Erreur lors du changement de mot de passe"
      );
    } finally {
      setPwdSaving(false);
    }
  };

  const handleSaveAI = async () => {
    setSaving(true);
    try {
      const data: any = {
        ai_provider: aiProvider,
        ai_model: aiModel,
        ai_base_url: aiBaseUrl,
      };
      if (aiTemp) data.ai_temperature = parseFloat(aiTemp);
      if (aiApiKey) data.ai_api_key = aiApiKey;
      await updateSettings(data);
      if (aiApiKey) {
        setAiKeySet(true);
        setAiApiKey("");
      }
      flash("Paramètres IA sauvegardés");
    } catch {
      flashError("Erreur de sauvegarde IA");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveFT = async () => {
    setSaving(true);
    try {
      const data: any = { france_travail_client_id: ftClientId };
      if (ftSecret) data.france_travail_client_secret = ftSecret;
      await updateSettings(data);
      if (ftSecret) {
        setFtSecretSet(true);
        setFtSecret("");
      }
      flash("Paramètres France Travail sauvegardés");
    } catch {
      flashError("Erreur de sauvegarde");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveHunter = async () => {
    setSaving(true);
    try {
      const data: any = {};
      if (hunterApiKey) data.hunter_api_key = hunterApiKey;
      await updateSettings(data);
      if (hunterApiKey) {
        setHunterKeySet(true);
        setHunterApiKey("");
      }
      flash("Clé Hunter.io sauvegardée");
    } catch {
      flashError("Erreur de sauvegarde");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveSmtp = async () => {
    setSaving(true);
    try {
      const data: any = {
        smtp_host: smtpHost.trim(),
        smtp_user: smtpUser.trim(),
        smtp_use_tls: smtpUseTls,
        smtp_from: smtpFrom.trim(),
      };
      if (smtpPort.trim() !== "") {
        const p = parseInt(smtpPort, 10);
        if (Number.isNaN(p) || p < 1 || p > 65535) {
          flashError("Port SMTP invalide");
          setSaving(false);
          return;
        }
        data.smtp_port = p;
      } else {
        data.smtp_port = null;
      }
      if (smtpPassword) data.smtp_password = smtpPassword;
      await updateSettings(data);
      if (smtpPassword) {
        setSmtpPasswordSet(true);
        setSmtpPassword("");
      }
      flash("Paramètres SMTP sauvegardés");
    } catch {
      flashError("Erreur de sauvegarde");
    } finally {
      setSaving(false);
    }
  };

  const handleApplySmtpPreset = (preset: "gmail" | "ovh" | "outlook" | "ionos") => {
    if (preset === "gmail") {
      setSmtpHost("smtp.gmail.com");
      setSmtpPort("587");
      setSmtpUseTls(true);
    } else if (preset === "ovh") {
      setSmtpHost("ssl0.ovh.net");
      setSmtpPort("587");
      setSmtpUseTls(true);
    } else if (preset === "outlook") {
      setSmtpHost("smtp.office365.com");
      setSmtpPort("587");
      setSmtpUseTls(true);
    } else if (preset === "ionos") {
      setSmtpHost("smtp.ionos.fr");
      setSmtpPort("465");
      setSmtpUseTls(true);
    }
  };

  const handleSaveAgency = async () => {
    setSaving(true);
    try {
      await updateSettings({
        agency_address: agencyAddress,
        agency_phone: agencyPhone,
        agency_email: agencyEmail,
        agency_siret: agencySiret,
      });
      flash("Coordonnées de l'agence sauvegardées");
    } catch {
      flashError("Erreur de sauvegarde");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveEmailTemplate = async () => {
    setSaving(true);
    try {
      await updateSettings({ email_template: emailTemplate });
      flash("Modèle d'email sauvegardé");
    } catch {
      flashError("Erreur de sauvegarde");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  const sectionCls =
    "bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6";
  const labelCls = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1";
  const inputCls =
    "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none";
  const btnPrimary =
    "flex items-center gap-2 px-5 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium disabled:opacity-50";

  return (
    <div className="max-w-3xl">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
        Paramètres
      </h2>

      {/* Flash messages */}
      {success && (
        <div className="mb-4 flex items-center gap-2 px-4 py-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-sm text-green-700 dark:text-green-400">
          <Check className="w-4 h-4" />
          {success}
        </div>
      )}
      {error && (
        <div className="mb-4 flex items-center gap-2 px-4 py-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-400">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      <div className="space-y-6">
        {/* ─── Profil ─────────────────────────────────── */}
        <div className={sectionCls}>
          <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <User className="w-5 h-5" />
            Profil
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
            <div>
              <label className={labelCls}>Prénom</label>
              <input
                className={inputCls}
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                placeholder="Prénom"
              />
            </div>
            <div>
              <label className={labelCls}>Nom</label>
              <input
                className={inputCls}
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder="Nom"
              />
            </div>
          </div>
          <div className="mb-4">
            <label className={labelCls}>Email</label>
            <input
              className={inputCls}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="votre@email.com"
            />
          </div>
          <div className="mb-4">
            <label className={labelCls}>
              <span className="flex items-center gap-1">
                <Building className="w-4 h-4" />
                Nom de l&apos;entreprise (pour les mails)
              </span>
            </label>
            <input
              className={inputCls}
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="Ex: InteriMatch SAS"
            />
          </div>
          <button onClick={handleSaveProfile} disabled={saving} className={btnPrimary}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Enregistrer
          </button>
        </div>

        {/* ─── Coordonnées Agence ─────────────────────── */}
        <div className={sectionCls}>
          <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Building className="w-5 h-5" />
            Coordonnées de l&apos;agence
            <span className="text-xs font-normal text-gray-500 dark:text-gray-400 ml-1">
              (utilisées dans les emails)
            </span>
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
            <div>
              <label className={labelCls}>
                <span className="flex items-center gap-1"><Phone className="w-3.5 h-3.5" /> Téléphone</span>
              </label>
              <input
                className={inputCls}
                value={agencyPhone}
                onChange={(e) => setAgencyPhone(e.target.value)}
                placeholder="01 23 45 67 89"
              />
            </div>
            <div>
              <label className={labelCls}>
                <span className="flex items-center gap-1"><Mail className="w-3.5 h-3.5" /> Email de l&apos;agence</span>
              </label>
              <input
                type="email"
                className={inputCls}
                value={agencyEmail}
                onChange={(e) => setAgencyEmail(e.target.value)}
                placeholder="contact@agence.fr"
              />
            </div>
          </div>
          <div className="mb-4">
            <label className={labelCls}>
              <span className="flex items-center gap-1"><MapPin className="w-3.5 h-3.5" /> Adresse</span>
            </label>
            <input
              className={inputCls}
              value={agencyAddress}
              onChange={(e) => setAgencyAddress(e.target.value)}
              placeholder="12 rue de la Paix, 75002 Paris"
            />
          </div>
          <div className="mb-4">
            <label className={labelCls}>SIRET</label>
            <input
              className={inputCls}
              value={agencySiret}
              onChange={(e) => setAgencySiret(e.target.value)}
              placeholder="123 456 789 00010"
            />
          </div>
          <button onClick={handleSaveAgency} disabled={saving} className={btnPrimary}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Enregistrer
          </button>
        </div>

        {/* ─── Modèle d'email ─────────────────────────── */}
        <div className={sectionCls}>
          <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Modèle d&apos;email
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
            Personnalisez le modèle utilisé par l&apos;IA pour générer les emails.
            Laissez vide pour utiliser le modèle par défaut.
            Variables disponibles : {"{nom_agence}"}, {"{telephone}"}, {"{email_agence}"}, {"{adresse}"}, {"{nom_recruteur}"}
          </p>
          <textarea
            className={`${inputCls} resize-y`}
            rows={10}
            value={emailTemplate}
            onChange={(e) => setEmailTemplate(e.target.value)}
            placeholder={`Objet : Proposition de candidature — {poste} chez {entreprise}\n\nBonjour,\n\nNous avons le plaisir de vous proposer un profil correspond parfaitement à votre offre de {poste}.\n\n[Description des compétences et expériences du candidat]\n\nNous serions ravis d'échanger avec vous pour organiser un entretien.\n\nCordialement,\n{nom_recruteur}\n{nom_agence}\nTél : {telephone}\n{email_agence}`}
          />
          <div className="mt-4">
            <button onClick={handleSaveEmailTemplate} disabled={saving} className={btnPrimary}>
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Enregistrer
            </button>
          </div>
        </div>

        {/* ─── Apparence ──────────────────────────────── */}
        <div className={sectionCls}>
          <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Sun className="w-5 h-5" />
            Apparence
          </h3>
          <div className="flex gap-3">
            {[
              { key: "light", label: "Clair", icon: Sun },
              { key: "dark", label: "Sombre", icon: Moon },
              { key: "system", label: "Système", icon: Monitor },
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => handleSaveTheme(key)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-medium transition-colors ${
                  theme === key
                    ? "border-primary-500 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400"
                    : "border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* ─── Sécurité ──────────────────────────────── */}
        <div className={sectionCls}>
          <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Lock className="w-5 h-5" />
            Sécurité
          </h3>
          <div className="space-y-3 mb-4">
            <div>
              <label className={labelCls}>Mot de passe actuel</label>
              <input
                type="password"
                className={inputCls}
                value={currentPwd}
                onChange={(e) => setCurrentPwd(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className={labelCls}>Nouveau mot de passe</label>
                <input
                  type="password"
                  className={inputCls}
                  value={newPwd}
                  onChange={(e) => setNewPwd(e.target.value)}
                />
              </div>
              <div>
                <label className={labelCls}>Confirmer</label>
                <input
                  type="password"
                  className={inputCls}
                  value={confirmPwd}
                  onChange={(e) => setConfirmPwd(e.target.value)}
                />
              </div>
            </div>
          </div>
          <button
            onClick={handleChangePassword}
            disabled={pwdSaving || !currentPwd || !newPwd}
            className={btnPrimary}
          >
            {pwdSaving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Lock className="w-4 h-4" />
            )}
            Changer le mot de passe
          </button>

          {/* 2FA section */}
          <div className="mt-6 pt-4 border-t border-gray-100 dark:border-gray-700">
            <TwoFactorSection
              totpEnabled={totpEnabled}
              onStatusChange={(enabled) => {
                setTotpEnabled(enabled);
                flash(enabled ? "2FA activée" : "2FA désactivée");
              }}
              onError={flashError}
            />
          </div>
        </div>

        {/* ─── Paramètres IA ─────────────────────────── */}
        <div className={sectionCls}>
          <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Brain className="w-5 h-5" />
            Paramètres IA
            {aiKeySet && (
              <span className="ml-auto text-xs font-medium px-2.5 py-1 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 flex items-center gap-1">
                <Check className="w-3 h-3" /> Configuré
              </span>
            )}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
            <div className="sm:col-span-2">
              <label className={labelCls}>Fournisseur IA</label>
              <select
                className={inputCls}
                value={aiProvider}
                onChange={(e) => {
                  const newProv = e.target.value;
                  setAiProvider(newProv);
                  // Auto-remplit URL/modèle si vides ou si l'utilisateur change de preset
                  const preset = aiProviders.find((p) => p.id === newProv);
                  if (preset && newProv !== "custom") {
                    if (!aiBaseUrl || aiProviders.some((p) => p.base_url === aiBaseUrl)) {
                      setAiBaseUrl(preset.base_url);
                    }
                    if (!aiModel || aiProviders.some((p) => p.default_model === aiModel)) {
                      setAiModel(preset.default_model);
                    }
                  }
                }}
              >
                {aiProviders.length === 0 && <option value="custom">Personnalisé</option>}
                {aiProviders.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                    {p.requires_key ? "" : " — sans clé"}
                  </option>
                ))}
              </select>
              {(() => {
                const preset = aiProviders.find((p) => p.id === aiProvider);
                if (!preset || !preset.docs) return null;
                return (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Doc / clé API :{" "}
                    <a
                      href={preset.docs}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline dark:text-blue-400"
                    >
                      {preset.docs}
                    </a>
                  </p>
                );
              })()}
            </div>
            <div>
              <label className={labelCls}>Modèle</label>
              <input
                className={inputCls}
                value={aiModel}
                onChange={(e) => setAiModel(e.target.value)}
                placeholder={
                  aiProviders.find((p) => p.id === aiProvider)?.default_model ||
                  "Ex: alfred-4.2"
                }
              />
            </div>
            <div>
              <label className={labelCls}>Température</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="2"
                className={inputCls}
                value={aiTemp}
                onChange={(e) => setAiTemp(e.target.value)}
                placeholder="0.3"
              />
            </div>
          </div>
          <div className="mb-4">
            <label className={labelCls}>Endpoint (URL de base)</label>
            <input
              className={inputCls}
              value={aiBaseUrl}
              onChange={(e) => setAiBaseUrl(e.target.value)}
              placeholder={
                aiProviders.find((p) => p.id === aiProvider)?.base_url ||
                "Ex: https://api.openai.com/v1"
              }
            />
          </div>
          <div className="mb-4">
            <label className={labelCls}>
              Clé API IA {aiKeySet && <span className="text-green-600 dark:text-green-400 text-xs ml-1">✓ configurée</span>}
            </label>
            <input
              type="password"
              className={inputCls}
              value={aiApiKey}
              onChange={(e) => setAiApiKey(e.target.value)}
              placeholder={aiKeySet ? "••••••••• (laisser vide pour garder)" : "Entrer la clé API"}
            />
          </div>
          <button onClick={handleSaveAI} disabled={saving} className={btnPrimary}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Enregistrer
          </button>
        </div>

        {/* ─── France Travail API ─────────────────────── */}
        <div className={sectionCls}>
          <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Key className="w-5 h-5" />
            API France Travail
            {(ftClientId || ftSecretSet) && (
              <span className="ml-auto text-xs font-medium px-2.5 py-1 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 flex items-center gap-1">
                <Check className="w-3 h-3" /> Configuré
              </span>
            )}
          </h3>
          <div className="space-y-4 mb-4">
            <div>
              <label className={labelCls}>Client ID</label>
              <input
                className={inputCls}
                value={ftClientId}
                onChange={(e) => setFtClientId(e.target.value)}
                placeholder="Identifiant client France Travail"
              />
            </div>
            <div>
              <label className={labelCls}>
                Client Secret{" "}
                {ftSecretSet && <span className="text-green-600 dark:text-green-400 text-xs ml-1">✓ configuré</span>}
              </label>
              <input
                type="password"
                className={inputCls}
                value={ftSecret}
                onChange={(e) => setFtSecret(e.target.value)}
                placeholder={
                  ftSecretSet
                    ? "••••••••• (laisser vide pour garder)"
                    : "Secret client France Travail"
                }
              />
            </div>
          </div>
          <button onClick={handleSaveFT} disabled={saving} className={btnPrimary}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Enregistrer
          </button>
        </div>

        {/* ─── Hunter.io API ──────────────────────────── */}
        <div className={sectionCls}>
          <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Mail className="w-5 h-5" />
            Hunter.io (recherche d&apos;emails)
            {hunterKeySet && (
              <span className="ml-auto text-xs font-medium px-2.5 py-1 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 flex items-center gap-1">
                <Check className="w-3 h-3" /> Configuré
              </span>
            )}
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
            Permet de trouver automatiquement l&apos;email du recruteur quand il n&apos;est pas disponible dans l&apos;offre.
            Créez un compte sur{" "}
            <a href="https://hunter.io" target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">
              hunter.io
            </a>{" "}
            pour obtenir une clé API (50 recherches/mois gratuites).
          </p>
          <div className="mb-4">
            <label className={labelCls}>
              Clé API Hunter.io{" "}
              {hunterKeySet && <span className="text-green-600 dark:text-green-400 text-xs ml-1">✓ configurée</span>}
            </label>
            <input
              type="password"
              className={inputCls}
              value={hunterApiKey}
              onChange={(e) => setHunterApiKey(e.target.value)}
              placeholder={
                hunterKeySet
                  ? "••••••••• (laisser vide pour garder)"
                  : "Entrer la clé API Hunter.io"
              }
            />
          </div>
          <button onClick={handleSaveHunter} disabled={saving} className={btnPrimary}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Enregistrer
          </button>
        </div>

        {/* ─── SMTP (envoi des mails) ─────────────────── */}
        <div className={sectionCls}>
          <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Mail className="w-5 h-5" />
            Envoi par email (SMTP)
            {smtpHost && smtpPasswordSet && smtpFrom && (
              <span className="ml-auto text-xs font-medium px-2.5 py-1 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 flex items-center gap-1">
                <Check className="w-3 h-3" /> Configuré
              </span>
            )}
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
            Configurez votre serveur SMTP pour envoyer directement les mails au recruteur depuis l&apos;app.
            Astuce : pour Gmail, créez un{" "}
            <a href="https://support.google.com/accounts/answer/185833" target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">
              mot de passe d&apos;application
            </a>{" "}
            (ne fonctionne qu&apos;avec la 2FA activée). Pas de service payant nécessaire.
          </p>
          <div className="flex flex-wrap gap-2 mb-4">
            <button type="button" onClick={() => handleApplySmtpPreset("gmail")} className="px-3 py-1.5 text-xs rounded-md border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700">
              Préréglage Gmail
            </button>
            <button type="button" onClick={() => handleApplySmtpPreset("outlook")} className="px-3 py-1.5 text-xs rounded-md border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700">
              Outlook 365
            </button>
            <button type="button" onClick={() => handleApplySmtpPreset("ovh")} className="px-3 py-1.5 text-xs rounded-md border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700">
              OVH
            </button>
            <button type="button" onClick={() => handleApplySmtpPreset("ionos")} className="px-3 py-1.5 text-xs rounded-md border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700">
              IONOS
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className={labelCls}>Serveur SMTP</label>
              <input type="text" className={inputCls} value={smtpHost} onChange={(e) => setSmtpHost(e.target.value)} placeholder="smtp.exemple.com" />
            </div>
            <div>
              <label className={labelCls}>Port</label>
              <input type="number" className={inputCls} value={smtpPort} onChange={(e) => setSmtpPort(e.target.value)} placeholder="587" />
            </div>
            <div>
              <label className={labelCls}>Identifiant (utilisateur)</label>
              <input type="text" className={inputCls} value={smtpUser} onChange={(e) => setSmtpUser(e.target.value)} placeholder="vous@exemple.com" />
            </div>
            <div>
              <label className={labelCls}>
                Mot de passe
                {smtpPasswordSet && <span className="text-green-600 dark:text-green-400 text-xs ml-1">✓ configuré</span>}
              </label>
              <input
                type="password"
                className={inputCls}
                value={smtpPassword}
                onChange={(e) => setSmtpPassword(e.target.value)}
                placeholder={smtpPasswordSet ? "••••••••• (laisser vide pour garder)" : "Mot de passe SMTP"}
              />
            </div>
            <div className="md:col-span-2">
              <label className={labelCls}>Adresse d&apos;expéditeur (From)</label>
              <input type="email" className={inputCls} value={smtpFrom} onChange={(e) => setSmtpFrom(e.target.value)} placeholder="contact@votre-agence.com" />
            </div>
            <div className="md:col-span-2">
              <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <input type="checkbox" checked={smtpUseTls} onChange={(e) => setSmtpUseTls(e.target.checked)} className="w-4 h-4" />
                Utiliser TLS / STARTTLS (recommandé)
              </label>
            </div>
          </div>
          <button onClick={handleSaveSmtp} disabled={saving} className={btnPrimary}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  );
}
