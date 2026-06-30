"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CreditCard, Zap, Check, ArrowRight, Download, Loader2 } from "lucide-react";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface BillingData {
  plan: string;
  tokenLimit: number;
  tokenUsed: number;
  renewalDate: string;
  invoices: { id: string; amount: number; currency: string; status: string; period: string; createdAt: string }[];
}

const plans = [
  {
    id: "free",
    name: "Free",
    price: "0€",
    period: "/mois",
    tokens: "10 000",
    features: ["1 utilisateur", "10 000 tokens/mois", "Brouillage de base", "Support communautaire"],
  },
  {
    id: "starter",
    name: "Starter",
    price: "29€",
    period: "/mois",
    tokens: "50 000",
    features: ["5 utilisateurs", "50 000 tokens/mois", "Règles personnalisées", "Support email"],
  },
  {
    id: "pro",
    name: "Pro",
    price: "149€",
    period: "/mois",
    tokens: "200 000",
    features: ["Utilisateurs illimités", "200 000 tokens/mois", "API & webhooks", "Support prioritaire", "Audit avancé"],
    popular: true,
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: "999€",
    period: "/mois",
    tokens: "1 000 000",
    features: ["Tout de Pro", "1M tokens/mois", "SSO & 2FA", "SLA 99.9%", "Support dédié", "On-premise possible"],
  },
];

export default function BillingPage() {
  const router = useRouter();
  const [data, setData] = useState<BillingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState<string | null>(null);

  const token = typeof window !== "undefined" ? localStorage.getItem("kinga_admin_token") : "";
  const orgId = typeof window !== "undefined" ? localStorage.getItem("kinga_admin_org") : "";

  useEffect(() => {
    if (!token) { router.push("/login"); return; }
    axios.get(`${API_URL}/api/organizations/${orgId}/billing`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => setData(res.data))
      .catch(() => {
        setData({
          plan: "free",
          tokenLimit: 10000,
          tokenUsed: 4200,
          renewalDate: "2026-07-24T12:00:00Z",
          invoices: []
        });
      })
      .finally(() => setLoading(false));
  }, []);

  const handlePlanChange = async (planId: string) => {
    setUpgrading(planId);
    try {
      await axios.patch(`${API_URL}/api/organizations/${orgId}/billing`, {
        plan: planId
      }, { headers: { Authorization: `Bearer ${token}` } });
      // Refresh
      const res = await axios.get(`${API_URL}/api/organizations/${orgId}/billing`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setData(res.data);
    } catch {}
    setUpgrading(null);
  };

  if (loading) {
    return (
      <div className="p-8 space-y-6">
        {[...Array(3)].map((_, i) => <div key={i} className="h-32 bg-mist/40 rounded-xl animate-pulse" />)}
      </div>
    );
  }

  if (!data) return null;

  const tokenPercentage = (data.tokenUsed / data.tokenLimit) * 100;

  return (
    <div className="p-6 md:p-8 max-w-[1100px] space-y-8">
      {/* Current usage */}
      <div className="bg-card-white rounded-xl border border-mist p-6 shadow-card">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Zap className="w-5 h-5 text-ember-orange" />
            <h2 className="text-[16px] font-semibold text-deep-ink">Utilisation en temps réel</h2>
          </div>
          <span className="text-[11px] font-mono uppercase text-deep-indigo bg-deep-indigo/5 px-2.5 py-1 rounded-md font-semibold">
            {data.plan}
          </span>
        </div>
        <div className="w-full bg-mist h-3 rounded-full overflow-hidden mb-2">
          <div
            className="h-full rounded-full transition-all duration-500 bg-gradient-to-r from-deep-indigo to-sky-blue"
            style={{ width: `${Math.min(tokenPercentage, 100)}%` }}
          />
        </div>
        <div className="flex justify-between text-[12px] text-slate">
          <span>{data.tokenUsed.toLocaleString("fr-FR")} tokens utilisés</span>
          <span>{data.tokenLimit.toLocaleString("fr-FR")} tokens disponibles</span>
        </div>
        <p className="text-[11px] text-fog mt-2">
          Renouvellement le {new Date(data.renewalDate).toLocaleDateString("fr-FR")}
        </p>
      </div>

      {/* Plans grid */}
      <div>
        <h3 className="text-[16px] font-semibold text-deep-ink mb-4">Choisir un plan</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {plans.map(plan => {
            const isCurrent = data.plan === plan.id;
            const isPopular = (plan as any).popular;
            return (
              <div
                key={plan.id}
                className={`relative bg-card-white rounded-xl border p-5 transition-all duration-300 ${
                  isCurrent
                    ? "border-deep-indigo shadow-elevated ring-1 ring-deep-indigo/20"
                    : isPopular
                    ? "border-ember-orange/30 shadow-card hover:shadow-elevated"
                    : "border-mist shadow-card hover:shadow-elevated"
                }`}
              >
                {isPopular && (
                  <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-ember-orange text-white text-[10px] font-mono uppercase rounded-full tracking-wider">
                    Populaire
                  </div>
                )}
                {isCurrent && (
                  <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-deep-indigo text-white text-[10px] font-mono uppercase rounded-full tracking-wider">
                    Actuel
                  </div>
                )}
                <h4 className="text-[15px] font-semibold text-deep-ink mt-1">{plan.name}</h4>
                <div className="flex items-baseline gap-0.5 mt-2 mb-3">
                  <span className="text-[28px] font-bold text-deep-ink tracking-[-1px]">{plan.price}</span>
                  <span className="text-[12px] text-slate">{plan.period}</span>
                </div>
                <p className="text-[11px] font-mono text-slate mb-4">{plan.tokens} tokens/mois</p>
                <ul className="space-y-1.5 mb-5">
                  {plan.features.map(f => (
                    <li key={f} className="flex items-center gap-2 text-[12px] text-graphite">
                      <Check className="w-3.5 h-3.5 text-forest-teal shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <button
                  onClick={() => !isCurrent && handlePlanChange(plan.id)}
                  disabled={isCurrent || upgrading === plan.id}
                  className={`w-full py-2 rounded-lg text-[13px] font-medium transition-colors flex items-center justify-center gap-2 ${
                    isCurrent
                      ? "bg-mist text-slate cursor-default"
                      : "bg-deep-indigo text-white hover:bg-deep-indigo/90"
                  } disabled:opacity-60`}
                >
                  {upgrading === plan.id ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : isCurrent ? (
                    "Plan actuel"
                  ) : (
                    <>Sélectionner <ArrowRight className="w-3.5 h-3.5" /></>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Invoices */}
      {data.invoices.length > 0 && (
        <div className="bg-card-white rounded-xl border border-mist p-6 shadow-card">
          <h3 className="text-[14px] font-semibold text-deep-ink mb-4">Historique des factures</h3>
          <div className="space-y-2">
            {data.invoices.map(inv => (
              <div key={inv.id} className="flex items-center justify-between px-4 py-3 rounded-lg border border-mist/50 hover:bg-paper-white transition-colors">
                <div className="flex items-center gap-3">
                  <CreditCard className="w-4 h-4 text-fog" />
                  <div>
                    <p className="text-[13px] font-medium text-deep-ink">{inv.amount.toFixed(2)} {inv.currency}</p>
                    <p className="text-[11px] text-slate">{inv.period}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded ${
                    inv.status === "paid" ? "bg-forest-teal/10 text-forest-teal" : "bg-ember-orange/10 text-ember-orange"
                  }`}>
                    {inv.status === "paid" ? "Payée" : inv.status}
                  </span>
                  <button className="p-1 rounded hover:bg-paper-white text-fog hover:text-deep-indigo transition-colors">
                    <Download className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
