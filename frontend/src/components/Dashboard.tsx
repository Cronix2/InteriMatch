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
} from "lucide-react";
import { getDashboardStats } from "@/lib/api";

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

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await getDashboardStats();
        setStats(res.data);
      } catch {
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
    } catch {
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
    </div>
  );
}
