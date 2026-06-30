import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kinga — Administration",
  description: "Console d'administration pour Kinga. Gérez les membres, les règles de brouillage, la facturation et la sécurité.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
