"use client";

import { useEffect, useState } from "react";
import {
  Users,
  BarChart3,
  Mail,
  CheckCircle,
  TrendingUp,
  Loader2,
  Building,
  Clock,
  Cpu,
  Zap,
  DollarSign,
  AlertTriangle,
  Activity,
} from "lucide-react";
import { getDashboardStats, getApiMetrics } from "@/lib/api";

interface Stats {
  total_candidates: number;
  total_matchings: number;
  total_emails: number;
  emails_validated: number;
  average_score: number;
  recent_matchings: {
    id: string;
    candidate_name: string;
    job_title: string;
    company_name: string;
    score: number;
    date: string;
  }[];
}

interface ApiMetrics {
  total_calls: number;
  total_tokens_input: number;
  total_tokens_output: number;
  total_estimated_cost: number;
  average_latency_ms: number;
  error_count: number;
  error_rate: number;
  by_action: {
    action: string;
    count: number;
    tokens_input: number;
    tokens_output: number;
    estimated_cost: number;
    avg_latency_ms: number;
  }[];
  daily: { date: string; calls: number; cost: number }[];
  monthly_calls: number;
  monthly_cost: number;
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [metrics, setMetrics] = useState<ApiMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [statsRes, metricsRes] = await Promise.all([
          getDashboardStats(),
          getApiMetrics(),
        ]);
        setStats(statsRes.data);
        setMetrics(metricsRes.data);
      } catch (err) {
        if (process.env.NODE_ENV !== "production") console.debug("[silent catch]", err);
        // silent
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (err) {
      if (process.env.NODE_ENV !== "production") console.debug("[silent catch]", err);
      return iso;
    }
  };

  const getScoreBg = (score: number) => {
    if (score >= 75) return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
    if (score >= 50) return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";
    return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  const cards = [
    {
      label: "Candidats",
      value: stats?.total_candidates ?? 0,
      icon: Users,
      color: "bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400",
    },
    {
      label: "Matchings",
      value: stats?.total_matchings ?? 0,
      icon: BarChart3,
      color: "bg-purple-50 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400",
    },
    {
      label: "Emails générés",
      value: stats?.total_emails ?? 0,
      icon: Mail,
      color: "bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400",
    },
    {
      label: "Emails validés",
      value: stats?.emails_validated ?? 0,
      icon: CheckCircle,
      color: "bg-green-50 text-green-600 dark:bg-green-900/30 dark:text-green-400",
    },
  ];

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
        Dashboard
      </h2>

      {/* Cartes statistiques */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {cards.map((card) => (
          <div
            key={card.label}
            className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-gray-500 dark:text-gray-400">
                {card.label}
              </span>
              <div
                className={`w-9 h-9 rounded-lg flex items-center justify-center ${card.color}`}
              >
                <card.icon className="w-5 h-5" />
              </div>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {card.value}
            </p>
          </div>
        ))}
      </div>

      {/* Score moyen */}
      {(stats?.average_score ?? 0) > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 mb-8 max-w-xs">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary-50 dark:bg-primary-900/30 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Score moyen
              </p>
              <p className="text-xl font-bold text-gray-900 dark:text-white">
                {stats?.average_score}%
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Activité récente */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
        <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Activité récente
          </h3>
        </div>
        {stats?.recent_matchings && stats.recent_matchings.length > 0 ? (
          <div className="divide-y divide-gray-100 dark:divide-gray-700">
            {stats.recent_matchings.map((m) => (
              <div
                key={m.id}
                className="px-5 py-3 flex items-center justify-between"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {m.candidate_name}
                  </p>
                  <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    <span className="truncate">{m.job_title}</span>
                    {m.company_name && (
                      <>
                        <span>•</span>
                        <span className="flex items-center gap-1 truncate">
                          <Building className="w-3 h-3" />
                          {m.company_name}
                        </span>
                      </>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3 ml-4">
                  <span
                    className={`text-xs font-bold px-2 py-1 rounded ${getScoreBg(m.score)}`}
                  >
                    {m.score}%
                  </span>
                  <span className="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap">
                    {formatDate(m.date)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="px-5 py-12 text-center text-gray-400 dark:text-gray-500">
            <BarChart3 className="w-10 h-10 mx-auto mb-2 opacity-40" />
            <p className="text-sm">
              Aucune activité pour le moment. Lancez un matching !
            </p>
          </div>
        )}
      </div>

      {/* Métriques API IA */}
      {metrics && (
        <div className="mt-8">
          <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-primary-600" />
            Métriques API IA
          </h3>

          {/* Cartes métriques API */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Appels totaux</span>
                <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400">
                  <Zap className="w-5 h-5" />
                </div>
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{metrics.total_calls}</p>
              <p className="text-xs text-gray-400 mt-1">{metrics.monthly_calls} ce mois</p>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Tokens utilisés</span>
                <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-cyan-50 text-cyan-600 dark:bg-cyan-900/30 dark:text-cyan-400">
                  <Activity className="w-5 h-5" />
                </div>
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {((metrics.total_tokens_input + metrics.total_tokens_output) / 1000).toFixed(1)}k
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {(metrics.total_tokens_input / 1000).toFixed(1)}k in / {(metrics.total_tokens_output / 1000).toFixed(1)}k out
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Coût estimé</span>
                <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400">
                  <DollarSign className="w-5 h-5" />
                </div>
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{metrics.total_estimated_cost.toFixed(2)} €</p>
              <p className="text-xs text-gray-400 mt-1">{metrics.monthly_cost.toFixed(2)} € ce mois</p>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Latence moyenne</span>
                <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                  metrics.error_rate > 10
                    ? "bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400"
                    : "bg-orange-50 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400"
                }`}>
                  {metrics.error_rate > 10 ? <AlertTriangle className="w-5 h-5" /> : <Clock className="w-5 h-5" />}
                </div>
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{(metrics.average_latency_ms / 1000).toFixed(1)}s</p>
              <p className="text-xs text-gray-400 mt-1">
                {metrics.error_count} erreur(s) ({metrics.error_rate}%)
              </p>
            </div>
          </div>

          {/* Détail par action */}
          {metrics.by_action.length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 mb-6">
              <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
                <h4 className="text-sm font-semibold text-gray-900 dark:text-white">Détail par type d&apos;appel</h4>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-700">
                      <th className="px-5 py-3 text-left font-medium">Action</th>
                      <th className="px-5 py-3 text-right font-medium">Appels</th>
                      <th className="px-5 py-3 text-right font-medium">Tokens (in/out)</th>
                      <th className="px-5 py-3 text-right font-medium">Coût</th>
                      <th className="px-5 py-3 text-right font-medium">Latence moy.</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                    {metrics.by_action.map((a) => (
                      <tr key={a.action}>
                        <td className="px-5 py-3 font-medium text-gray-900 dark:text-white">
                          {a.action === "extract_cv" ? "Extraction CV" :
                           a.action === "matching" ? "Matching IA" :
                           a.action === "generate_email" ? "Génération email" : a.action}
                        </td>
                        <td className="px-5 py-3 text-right text-gray-600 dark:text-gray-400">{a.count}</td>
                        <td className="px-5 py-3 text-right text-gray-600 dark:text-gray-400">
                          {(a.tokens_input / 1000).toFixed(1)}k / {(a.tokens_output / 1000).toFixed(1)}k
                        </td>
                        <td className="px-5 py-3 text-right text-gray-600 dark:text-gray-400">{a.estimated_cost.toFixed(4)} €</td>
                        <td className="px-5 py-3 text-right text-gray-600 dark:text-gray-400">{(a.avg_latency_ms / 1000).toFixed(1)}s</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Graphique barres quotidien (simple CSS) */}
          {metrics.daily.length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
                Appels API — 7 derniers jours
              </h4>
              <div className="flex items-end gap-2 h-32">
                {(() => {
                  const peakCalls = Math.max(...metrics.daily.map((x) => x.calls), 1);
                  return metrics.daily.map((d) => {
                    const height = Math.max((d.calls / peakCalls) * 100, 4);
                    return (
                    <div key={d.date} className="flex-1 flex flex-col items-center gap-1">
                      <span className="text-xs text-gray-500 dark:text-gray-400">{d.calls}</span>
                      <div
                        className="w-full bg-primary-500 dark:bg-primary-600 rounded-t"
                        style={{ height: `${height}%` }}
                      />
                      <span className="text-[10px] text-gray-400">
                        {new Date(d.date).toLocaleDateString("fr-FR", { day: "numeric", month: "short" })}
                      </span>
                    </div>
                  );
                });
                })()}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
