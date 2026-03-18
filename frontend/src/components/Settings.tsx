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
} from "lucide-react";
import { getMe, updateSettings, changePassword } from "@/lib/api";

interface SettingsData {
  first_name: string;
  last_name: string;
  company_name: string;
  theme: string;
  ai_model: string;
  ai_base_url: string;
  ai_temperature: number | null;
  ai_api_key_set: boolean;
  france_travail_client_id: string;
  france_travail_secret_set: boolean;
  totp_enabled: boolean;
}

interface SettingsProps {
  onThemeChange: (theme: string) => void;
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
  const [aiModel, setAiModel] = useState("");
  const [aiBaseUrl, setAiBaseUrl] = useState("");
  const [aiTemp, setAiTemp] = useState("");
  const [aiApiKey, setAiApiKey] = useState("");
  const [aiKeySet, setAiKeySet] = useState(false);

  // France Travail
  const [ftClientId, setFtClientId] = useState("");
  const [ftSecret, setFtSecret] = useState("");
  const [ftSecretSet, setFtSecretSet] = useState(false);

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
        setFtClientId(s.france_travail_client_id);
        setFtSecretSet(s.france_travail_secret_set);
        setTotpEnabled(s.totp_enabled);
      } catch {
        setError("Impossible de charger les paramètres");
      } finally {
        setLoading(false);
      }
    };
    load();
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
      const data: any = { ai_model: aiModel, ai_base_url: aiBaseUrl };
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

          {/* 2FA placeholder */}
          <div className="mt-6 pt-4 border-t border-gray-100 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-gray-500" />
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    Authentification à deux facteurs (2FA)
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {totpEnabled
                      ? "Activé — Protection renforcée"
                      : "Désactivé — Bientôt disponible"}
                  </p>
                </div>
              </div>
              <span
                className={`text-xs font-medium px-2.5 py-1 rounded-full ${
                  totpEnabled
                    ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                    : "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400"
                }`}
              >
                {totpEnabled ? "Actif" : "Bientôt"}
              </span>
            </div>
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
            <div>
              <label className={labelCls}>Modèle</label>
              <input
                className={inputCls}
                value={aiModel}
                onChange={(e) => setAiModel(e.target.value)}
                placeholder="Ex: alfred-4.2"
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
              placeholder="Ex: https://api.openai.com/v1"
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
      </div>
    </div>
  );
}
