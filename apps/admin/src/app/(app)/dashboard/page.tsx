"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Users, Zap, Shield, AlertTriangle, TrendingUp, Activity } from "lucide-react";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface DashboardData {
  membersCount: number;
  tokenUsed: number;
  tokenLimit: number;
  plan: string;
  activityCount: number;
  maskingRate: number;
  securityAlerts: { id: string; type: string; message: string; createdAt: string }[];
  chartData: { date: string; requests: number; tokens: number }[];
}

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("kinga_admin_token");
    const orgId = localStorage.getItem("kinga_admin_org");
    if (!token) { router.push("/login"); return; }

    axios.get(`${API_URL}/api/organizations/${orgId}/dashboard`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => setData(res.data))
      .catch(() => {
        // Fallback simulated data
        setData({
          membersCount: 3,
          tokenUsed: 4200,
          tokenLimit: 10000,
          plan: "free",
          activityCount: 27,
          maskingRate: 84.5,
          securityAlerts: [
            { id: "1", type: "warning", message: "Règle EMAIL désactivée temporairement", createdAt: new Date().toISOString() }
          ],
          chartData: [
            { date: "24 Juin", requests: 12, tokens: 4800 },
            { date: "23 Juin", requests: 8, tokens: 3200 },
            { date: "22 Juin", requests: 15, tokens: 6000 },
            { date: "21 Juin", requests: 5, tokens: 2000 },
          ]
        });
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="p-8 space-y-6">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-24 bg-mist/40 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (!data) return null;

  const tokenPercentage = (data.tokenUsed / data.tokenLimit) * 100;

  const stats = [
    {
      label: "Membres",
      value: data.membersCount,
      icon: Users,
      color: "text-deep-indigo",
      bg: "bg-deep-indigo/5"
    },
    {
      label: "Tokens utilisés",
      value: `${data.tokenUsed.toLocaleString("fr-FR")} / ${data.tokenLimit.toLocaleString("fr-FR")}`,
      icon: Zap,
      color: "text-ember-orange",
      bg: "bg-ember-orange/5"
    },
    {
      label: "Taux de brouillage",
      value: `${data.maskingRate}%`,
      icon: Shield,
      color: "text-forest-teal",
      bg: "bg-forest-teal/5"
    },
    {
      label: "Actions auditées",
      value: data.activityCount,
      icon: Activity,
      color: "text-lavender",
      bg: "bg-lavender/5"
    },
  ];

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-[1200px]">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="bg-card-white rounded-xl border border-mist p-5 shadow-card hover:shadow-elevated transition-shadow duration-300">
              <div className="flex items-center justify-between mb-3">
                <span className="text-[12px] font-mono uppercase text-slate tracking-wide">{stat.label}</span>
                <div className={`w-8 h-8 rounded-lg ${stat.bg} flex items-center justify-center`}>
                  <Icon className={`w-4 h-4 ${stat.color}`} />
                </div>
              </div>
              <p className="text-[22px] font-semibold text-deep-ink tracking-[-0.5px]">
                {stat.value}
              </p>
            </div>
          );
        })}
      </div>

      {/* Token usage bar */}
      <div className="bg-card-white rounded-xl border border-mist p-6 shadow-card">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-[14px] font-semibold text-deep-ink">Utilisation des tokens</h3>
          <span className="text-[11px] font-mono uppercase text-deep-indigo bg-deep-indigo/5 px-2 py-1 rounded-md font-semibold">
            {data.plan}
          </span>
        </div>
        <div className="w-full bg-mist h-2.5 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500 bg-gradient-to-r from-deep-indigo to-sky-blue"
            style={{ width: `${Math.min(tokenPercentage, 100)}%` }}
          />
        </div>
        <p className="text-[12px] text-slate mt-2">
          {data.tokenUsed.toLocaleString("fr-FR")} tokens utilisés sur {data.tokenLimit.toLocaleString("fr-FR")}
        </p>
      </div>

      {/* Activity chart (simple bar representation) */}
      <div className="bg-card-white rounded-xl border border-mist p-6 shadow-card">
        <h3 className="text-[14px] font-semibold text-deep-ink mb-4">Activité récente</h3>
        <div className="flex items-end gap-3 h-[120px]">
          {data.chartData.map((point, idx) => {
            const maxTokens = Math.max(...data.chartData.map(d => d.tokens));
            const height = maxTokens > 0 ? (point.tokens / maxTokens) * 100 : 0;
            return (
              <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                <span className="text-[10px] font-mono text-slate">{point.requests} req</span>
                <div className="w-full rounded-t-md bg-deep-indigo/10 relative" style={{ height: `${height}%`, minHeight: 8 }}>
                  <div className="absolute inset-0 rounded-t-md bg-gradient-to-t from-deep-indigo/60 to-deep-indigo/20" />
                </div>
                <span className="text-[10px] text-fog">{point.date}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Security alerts */}
      {data.securityAlerts.length > 0 && (
        <div className="bg-card-white rounded-xl border border-ember-orange/20 p-6 shadow-card">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-4 h-4 text-ember-orange" />
            <h3 className="text-[14px] font-semibold text-deep-ink">Alertes de sécurité</h3>
          </div>
          <div className="space-y-2">
            {data.securityAlerts.map((alert) => (
              <div key={alert.id} className="flex items-center gap-3 px-4 py-3 rounded-lg bg-ember-orange/5 border border-ember-orange/10">
                <div className="w-2 h-2 rounded-full bg-ember-orange shrink-0" />
                <p className="text-[13px] text-graphite flex-1">{alert.message}</p>
                <span className="text-[10px] font-mono text-fog">
                  {new Date(alert.createdAt).toLocaleDateString("fr-FR")}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick links */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: "Gérer les membres", href: "/members", icon: Users, desc: "Inviter, modifier les rôles" },
          { label: "Configurer les règles", href: "/rules", icon: Shield, desc: "Brouillage des données" },
          { label: "Voir les factures", href: "/billing", icon: TrendingUp, desc: "Plans et paiements" },
        ].map((link) => {
          const Icon = link.icon;
          return (
            <a
              key={link.label}
              href={link.href}
              className="bg-card-white rounded-xl border border-mist p-5 shadow-card hover:shadow-elevated hover:border-deep-indigo/20 transition-all duration-300 group"
            >
              <Icon className="w-5 h-5 text-fog group-hover:text-deep-indigo transition-colors mb-2" />
              <p className="text-[14px] font-medium text-deep-ink">{link.label}</p>
              <p className="text-[12px] text-slate mt-0.5">{link.desc}</p>
            </a>
          );
        })}
      </div>
    </div>
  );
}
