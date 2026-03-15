import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "InteriMatch AI",
  description:
    "Application métier pour les entreprises d'intérim — matching CV / offres d'emploi avec IA",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body className="min-h-screen bg-gray-50">{children}</body>
    </html>
  );
}
