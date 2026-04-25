"use client";

import { useState } from "react";
import {
  Loader2,
  Shield,
  ShieldCheck,
  ShieldOff,
} from "lucide-react";
import { setup2FA, verify2FA, disable2FA } from "@/lib/api";
import { getApiErrorDetail } from "@/lib/utils";

interface TwoFactorSectionProps {
  totpEnabled: boolean;
  onStatusChange: (enabled: boolean) => void;
  onError: (msg: string) => void;
}

export default function TwoFactorSection({
  totpEnabled,
  onStatusChange,
  onError,
}: TwoFactorSectionProps) {
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
    } catch (err: unknown) {
      onError(getApiErrorDetail(err, "Erreur lors de la configuration 2FA"));
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
    } catch (err: unknown) {
      onError(getApiErrorDetail(err, "Code invalide"));
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
    } catch (err: unknown) {
      onError(getApiErrorDetail(err, "Code invalide"));
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
