"use client";

import { useCallback, useEffect, useState } from "react";
import AuthScreen from "@/components/AuthScreen";
import Sidebar, { type Page } from "@/components/Sidebar";
import Dashboard from "@/components/Dashboard";
import MatchFlow from "@/components/MatchFlow";
import History from "@/components/History";
import Settings from "@/components/Settings";
import { getMe } from "@/lib/api";

function applyThemeClass(theme: string) {
  const root = document.documentElement;
  if (theme === "dark") {
    root.classList.add("dark");
  } else if (theme === "light") {
    root.classList.remove("dark");
  } else {
    // system
    if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }
}

export default function Home() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authChecked, setAuthChecked] = useState(false);
  const [page, setPage] = useState<Page>("dashboard");

  useEffect(() => {
    const token = localStorage.getItem("interimatch_token");
    if (!token) {
      setAuthChecked(true);
      return;
    }
    // Vérifier la validité du token auprès du backend
    getMe()
      .then(() => setIsAuthenticated(true))
      .catch((err) => {
        if (err.response?.status === 401) {
          localStorage.removeItem("interimatch_token");
        } else {
          // Erreur serveur (500, réseau…) : garder la session
          setIsAuthenticated(true);
        }
      })
      .finally(() => setAuthChecked(true));

    // Appliquer le thème sauvé
    const saved = localStorage.getItem("interimatch_theme") || "system";
    applyThemeClass(saved);

    // Écouter les changements système
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => {
      if ((localStorage.getItem("interimatch_theme") || "system") === "system") {
        applyThemeClass("system");
      }
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const handleThemeChange = useCallback((theme: string) => {
    localStorage.setItem("interimatch_theme", theme);
    applyThemeClass(theme);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("interimatch_token");
    setIsAuthenticated(false);
    setPage("dashboard");
  };

  if (!authChecked) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50 dark:bg-gray-950">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <AuthScreen onAuthenticated={() => setIsAuthenticated(true)} />;
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950">
      <Sidebar
        currentPage={page}
        onNavigate={setPage}
        onLogout={handleLogout}
      />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-6 py-8">
          {page === "dashboard" && <Dashboard />}
          {page === "match" && <MatchFlow />}
          {page === "history" && <History />}
          {page === "settings" && <Settings onThemeChange={handleThemeChange} />}
        </div>
      </main>
    </div>
  );
}
