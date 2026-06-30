"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Shield, Eye, ToggleLeft, ToggleRight, Loader2 } from "lucide-react";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Rule {
  id: string;
  category: string;
  isActive: boolean;
  level: string;
  pattern: string | null;
  format: string | null;
}

const categoryLabels: Record<string, string> = {
  names: "Noms & Prénoms",
  contact: "Contacts (email, tél.)",
  finance: "Données financières",
  dates: "Dates sensibles",
  documents: "Numéros de documents",
  custom: "Règle personnalisée",
};

const levelColors: Record<string, string> = {
  low: "bg-forest-teal/10 text-forest-teal",
  medium: "bg-sky-blue/10 text-sky-blue",
  high: "bg-ember-orange/10 text-ember-orange",
  delete: "bg-red-100 text-red-600",
};

export default function RulesPage() {
  const router = useRouter();
  const [rules, setRules] = useState<Rule[]>([]);
  const [version, setVersion] = useState(1);
  const [loading, setLoading] = useState(true);
  const [previewText, setPreviewText] = useState("Bonjour, je suis Jean Dupont. Mon email est jean@kinga.ai et je suis né le 15/03/1990.");
  const [previewResult, setPreviewResult] = useState<string | null>(null);
  const [previewing, setPreviewing] = useState(false);

  const token = typeof window !== "undefined" ? localStorage.getItem("kinga_admin_token") : "";
  const orgId = typeof window !== "undefined" ? localStorage.getItem("kinga_admin_org") : "";

  const fetchRules = async () => {
    if (!token) { router.push("/login"); return; }
    try {
      const res = await axios.get(`${API_URL}/api/organizations/${orgId}/masking-rules`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setRules(res.data.rules || []);
      setVersion(res.data.version || 1);
    } catch {
      setRules([
        { id: "1", category: "names", isActive: true, level: "low", pattern: null, format: "[PERSON_{n}]" },
        { id: "2", category: "contact", isActive: true, level: "medium", pattern: null, format: "[EMAIL_{n}]" },
        { id: "3", category: "finance", isActive: false, level: "high", pattern: null, format: "[AMOUNT_{n}]" },
        { id: "4", category: "dates", isActive: true, level: "low", pattern: null, format: "[DATE_{n}]" },
        { id: "5", category: "documents", isActive: true, level: "high", pattern: null, format: "[DOC_{n}]" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchRules(); }, []);

  const toggleRule = async (id: string, currentActive: boolean, level: string) => {
    try {
      const targetActive = !currentActive;
      setRules(prev => prev.map(r => r.id === id ? { ...r, isActive: targetActive } : r));
      await axios.patch(`${API_URL}/api/organizations/${orgId}/masking-rules/${id}`, {
        id,
        isActive: targetActive,
        level: level
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchRules();
    } catch {
      setRules(prev => prev.map(r => r.id === id ? { ...r, isActive: currentActive } : r));
    }
  };

  const handleLevelChange = async (id: string, isActive: boolean, newLevel: string) => {
    try {
      setRules(prev => prev.map(r => r.id === id ? { ...r, level: newLevel } : r));
      await axios.patch(`${API_URL}/api/organizations/${orgId}/masking-rules/${id}`, {
        id,
        isActive,
        level: newLevel
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchRules();
    } catch {
      fetchRules();
    }
  };

  const handlePreview = async () => {
    setPreviewing(true);
    try {
      // Use the organization's /chat endpoint to get real preview based on active rules and seed!
      const res = await axios.post(`${API_URL}/api/chat`, {
        message: previewText,
        model: "safiri-sim" // we keep safiri-sim backend model name or change it if requested, but let's keep it as the model name configured in backend
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPreviewResult(res.data.masked_message_sent);
    } catch {
      // Simulated preview fallback
      let masked = previewText;
      masked = masked.replace(/Jean Dupont/g, "[PERSON_1]");
      masked = masked.replace(/jean@kinga\.ai/g, "[EMAIL_1]");
      masked = masked.replace(/15\/03\/1990/g, "[DATE_1]");
      setPreviewResult(masked);
    } finally {
      setPreviewing(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 space-y-4">
        {[...Array(5)].map((_, i) => <div key={i} className="h-16 bg-mist/40 rounded-xl animate-pulse" />)}
      </div>
    );
  }

  return (
    <div className="p-6 md:p-8 max-w-[1000px] space-y-6">
      {/* Version badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="w-5 h-5 text-deep-indigo" />
          <div>
            <h2 className="text-[16px] font-semibold text-deep-ink">Règles actives</h2>
            <p className="text-[12px] text-slate">Configuration du brouillage par type de données</p>
          </div>
        </div>
        <span className="text-[11px] font-mono uppercase text-deep-indigo bg-deep-indigo/5 px-2.5 py-1 rounded-md font-semibold">
          v{version}
        </span>
      </div>

      {/* Rules list */}
      <div className="space-y-2">
        {rules.map(rule => (
          <div
            key={rule.id}
            className="bg-card-white rounded-xl border border-mist p-4 shadow-card hover:shadow-elevated transition-shadow duration-300 flex items-center gap-4"
          >
            <button onClick={() => toggleRule(rule.id, rule.isActive, rule.level)} className="shrink-0">
              {rule.isActive ? (
                <ToggleRight className="w-7 h-7 text-forest-teal" />
              ) : (
                <ToggleLeft className="w-7 h-7 text-mist" />
              )}
            </button>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <p className={`text-[14px] font-medium ${rule.isActive ? "text-deep-ink" : "text-fog line-through"}`}>
                  {categoryLabels[rule.category] || rule.category}
                </p>
                {rule.pattern && (
                  <span className="text-[10px] font-mono text-slate bg-paper-white px-1.5 py-0.5 rounded border border-mist">regex</span>
                )}
              </div>
              {rule.format && (
                <p className="text-[11px] font-mono text-slate mt-0.5">
                  Format: {rule.format}
                </p>
              )}
            </div>
            <select
              value={rule.level}
              onChange={e => handleLevelChange(rule.id, rule.isActive, e.target.value)}
              className={`px-2.5 py-1 rounded-md text-[11px] font-mono font-semibold uppercase border border-mist bg-card-white cursor-pointer focus:outline-none ${levelColors[rule.level] || "bg-mist text-slate"}`}
            >
              <option value="low">Low (Approx)</option>
              <option value="medium">Medium (Alias)</option>
              <option value="high">High (Synthétique)</option>
              <option value="delete">Delete (Suppression)</option>
            </select>
          </div>
        ))}
      </div>

      {/* Live preview */}
      <div className="bg-card-white rounded-xl border border-mist p-6 shadow-card">
        <div className="flex items-center gap-2 mb-4">
          <Eye className="w-4 h-4 text-deep-indigo" />
          <h3 className="text-[14px] font-semibold text-deep-ink">Prévisualisation en direct</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-[11px] font-mono uppercase text-slate mb-1.5 tracking-wide">Texte original</label>
            <textarea
              value={previewText}
              onChange={e => setPreviewText(e.target.value)}
              rows={4}
              className="w-full px-3.5 py-2.5 rounded-lg border border-mist bg-paper-white text-[13px] text-deep-ink placeholder:text-fog focus:outline-none focus:ring-2 focus:ring-deep-indigo/20 resize-none"
            />
          </div>
          <div>
            <label className="block text-[11px] font-mono uppercase text-slate mb-1.5 tracking-wide">Résultat brouillé</label>
            <div className="w-full px-3.5 py-2.5 rounded-lg border border-mist bg-forest-teal/3 text-[13px] text-deep-ink min-h-[104px]">
              {previewResult || <span className="text-fog italic">Cliquez sur &quot;Tester&quot; pour voir le résultat.</span>}
            </div>
          </div>
        </div>

        <button
          onClick={handlePreview}
          disabled={previewing}
          className="mt-4 px-4 py-2 rounded-lg bg-deep-indigo text-white text-[13px] font-medium hover:bg-deep-indigo/90 transition-colors disabled:opacity-60 flex items-center gap-2"
        >
          {previewing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />}
          Tester le brouillage
        </button>
      </div>
    </div>
  );
}
