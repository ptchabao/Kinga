"use client";

import {
  LayoutDashboard, Users, Shield, Activity, Settings,
  ChevronLeft, Menu, LogOut, ShieldCheck
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { cn } from "../../lib/utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function AdminSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [orgName, setOrgName] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem("kinga_admin_user");
    if (stored) {
      try { setUser(JSON.parse(stored)); } catch { }
    }
    const token = localStorage.getItem("kinga_admin_token");
    if (!token) {
      router.push("/login");
      return;
    }
    // Fetch org name
    fetch(`${API_URL}/api/auth/profile`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(data => {
        setOrgName(data.orgName || "Mon organisation");
        setUser(data);
      })
      .catch(() => {
        localStorage.removeItem("kinga_admin_token");
        router.push("/login");
      });
  }, [pathname]);

  const handleLogout = () => {
    localStorage.removeItem("kinga_admin_token");
    localStorage.removeItem("kinga_admin_user");
    localStorage.removeItem("kinga_admin_org");
    router.push("/login");
  };

  const links = [
    { name: "Tableau de bord", href: "/dashboard", icon: LayoutDashboard },
    { name: "Membres", href: "/members", icon: Users },
    { name: "Règles de brouillage", href: "/rules", icon: Shield },
    { name: "Sécurité & Audit", href: "/audit", icon: Activity },
    { name: "Paramètres", href: "/settings", icon: Settings },
  ];

  return (
    <aside
      className={cn(
        "flex flex-col bg-card-white border-r border-mist transition-all duration-300 relative z-40",
        isCollapsed ? "w-[72px]" : "w-[260px]"
      )}
    >
      {/* Logo */}
      <div className="h-[64px] flex items-center justify-between px-4 border-b border-mist">
        {!isCollapsed && (
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-lg bg-deep-indigo flex items-center justify-center shadow-sm">
              <ShieldCheck className="w-4 h-4 text-white" />
            </div>
            <div className="flex flex-col">
              <span className="font-semibold text-[15px] text-deep-ink tracking-[-0.2px] whitespace-nowrap leading-tight">
                Kinga Admin
              </span>
              <span className="text-[10px] font-mono text-slate uppercase tracking-wider">
                Console
              </span>
            </div>
          </div>
        )}
        {isCollapsed && (
          <div className="w-full flex justify-center">
            <div className="w-8 h-8 rounded-lg bg-deep-indigo flex items-center justify-center">
              <ShieldCheck className="w-4 h-4 text-white" />
            </div>
          </div>
        )}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className={cn(
            "p-1.5 rounded-lg hover:bg-paper-white text-slate transition-colors",
            isCollapsed && "absolute -right-3 bg-card-white border border-mist shadow-card rounded-full z-50"
          )}
        >
          {isCollapsed ? <Menu className="w-3.5 h-3.5" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Org name */}
      {!isCollapsed && orgName && (
        <div className="px-4 py-3 border-b border-mist/50">
          <p className="text-[11px] font-mono uppercase text-fog tracking-wide">Organisation</p>
          <p className="text-[13px] font-medium text-deep-ink truncate">{orgName}</p>
        </div>
      )}

      {/* Nav */}
      <div className="flex-1 py-4 flex flex-col gap-1 px-3">
        {links.map((link) => {
          const Icon = link.icon;
          const isActive = pathname.startsWith(link.href);
          return (
            <Link
              key={link.name}
              href={link.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group relative text-[14px]",
                isActive
                  ? "bg-paper-white text-deep-indigo font-medium shadow-hairline"
                  : "text-slate hover:text-deep-ink hover:bg-paper-white"
              )}
            >
              <Icon className={cn("w-[18px] h-[18px] shrink-0", isActive ? "text-deep-indigo" : "text-fog group-hover:text-carbon")} />
              {!isCollapsed && <span className="whitespace-nowrap">{link.name}</span>}

              {isCollapsed && (
                <div className="absolute left-full ml-3 px-2.5 py-1.5 bg-card-white border border-mist text-deep-ink text-xs rounded-lg opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50 shadow-card font-medium">
                  {link.name}
                </div>
              )}
            </Link>
          );
        })}
      </div>

      {/* Admin badge + Logout */}
      {!isCollapsed && user && (
        <div className="p-3 mx-3 mb-2 rounded-lg bg-deep-indigo/5 border border-deep-indigo/10">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-6 h-6 rounded-full bg-deep-indigo flex items-center justify-center">
              <span className="text-[10px] font-bold text-white">
                {(user.name || user.email || "A").charAt(0).toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[12px] font-medium text-deep-ink truncate">{user.name || user.email}</p>
              <p className="text-[10px] font-mono text-deep-indigo uppercase">Administrateur</p>
            </div>
          </div>
        </div>
      )}

      <div className="px-3 pb-3 pt-1">
        <button
          onClick={handleLogout}
          className={cn(
            "flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate hover:text-ember-orange hover:bg-ember-orange/5 transition-colors text-[14px] w-full text-left",
            isCollapsed && "justify-center"
          )}
        >
          <LogOut className="w-[18px] h-[18px] shrink-0 text-fog" />
          {!isCollapsed && <span>Déconnexion</span>}
        </button>
      </div>
    </aside>
  );
}
