import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kinga On-Premise Dashboard",
  description: "Tableau de bord self-hosted pour Kinga"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
