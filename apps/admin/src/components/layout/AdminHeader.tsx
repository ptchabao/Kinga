"use client";

import { ShieldCheck } from "lucide-react";
import { usePathname } from "next/navigation";

const pageTitles: Record<string, string> = {
  "/dashboard": "Tableau de bord",
  "/members": "Gestion des membres",
  "/rules": "Règles de brouillage",
  "/audit": "Sécurité & Audit",
  "/billing": "Facturation",
  "/settings": "Paramètres",
};

export function AdminHeader() {
  const pathname = usePathname();
  const title = Object.entries(pageTitles).find(([k]) => pathname.startsWith(k))?.[1] || "Administration";

  return (
    <header className="h-[56px] flex items-center justify-between px-6 border-b border-mist bg-card-white/80 backdrop-blur-sm">
      <div className="flex items-center gap-3">
        <h1 className="text-[16px] font-semibold text-deep-ink tracking-[-0.2px]">{title}</h1>
      </div>
      <div className="flex items-center gap-2 text-[12px] text-slate">
        <ShieldCheck className="w-3.5 h-3.5 text-forest-teal" />
        <span className="font-mono uppercase tracking-wide">Admin</span>
      </div>
    </header>
  );
}
