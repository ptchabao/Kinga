"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Settings, Key, Globe, Save, Loader2, Copy, Check } from "lucide-react";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface OrgSettings {
  id: string;
  name: string;
  slug: string;
  domain: string;
  logoUrl: string | null;
  apiKeys: { id: string; name: string; key: string; createdAt: string }[];
}

export default function SettingsPage() {
  const router = useRouter();
  const [settings, setSettings] = useState<OrgSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [orgName, setOrgName] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const token = typeof window !== "undefined" ? localStorage.getItem("kinga_admin_token") : "";
  const orgId = typeof window !== "undefined" ? localStorage.getItem("kinga_admin_org") : "";

  useEffect(() => {
    if (!token) { router.push("/login"); return; }
    axios.get(`${API_URL}/api/organizations/${orgId}/settings`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => {
        setSettings(res.data);
        setOrgName(res.data.name);
      })
      .catch(() => {
        const fallback = {
          id: orgId || "org-1",
          name: "Mon organisation",
          slug: "mon-organisation",
          domain: "mon-organisation.kinga.ai",
          logoUrl: null,
          apiKeys: []
        };
        setSettings(fallback);
        setOrgName(fallback.name);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await axios.patch(`${API_URL}/api/organizations/${orgId}/settings`, {
        name: orgName
      }, { headers: { Authorization: `Bearer ${token}` } });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {}
    setSaving(false);
  };

  const copyToClipboard = (key: string, id: string) => {
    navigator.clipboard.writeText(key);
    setCopiedKey(id);
    setTimeout(() => setCopiedKey(null), 1500);
  };

  if (loading) {
    return (
      <div className="p-8 space-y-6">
        {[...Array(3)].map((_, i) => <div key={i} className="h-24 bg-mist/40 rounded-xl animate-pulse" />)}
      </div>
    );
  }

  if (!settings) return null;

  return (
    <div className="p-6 md:p-8 max-w-[800px] space-y-6">
      {/* General settings */}
      <div className="bg-card-white rounded-xl border border-mist p-6 shadow-card">
        <div className="flex items-center gap-2 mb-5">
          <Settings className="w-4.5 h-4.5 text-deep-indigo" />
          <h2 className="text-[15px] font-semibold text-deep-ink">Informations générales</h2>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-[12px] font-medium text-graphite mb-1.5">
              Nom de l&apos;organisation
            </label>
            <input
              type="text"
              value={orgName}
              onChange={e => setOrgName(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg border border-mist bg-paper-white text-[14px] text-deep-ink placeholder:text-fog focus:outline-none focus:ring-2 focus:ring-deep-indigo/20 focus:border-deep-indigo/40 transition-all"
            />
          </div>

          <div>
            <label className="block text-[12px] font-medium text-graphite mb-1.5">
              Slug
            </label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={settings.slug}
                disabled
                className="flex-1 px-3.5 py-2.5 rounded-lg border border-mist bg-mist/30 text-[14px] text-slate cursor-not-allowed"
              />
            </div>
          </div>

          <div>
            <label className="block text-[12px] font-medium text-graphite mb-1.5">
              Domaine personnalisé
            </label>
            <div className="flex items-center gap-2">
              <Globe className="w-4 h-4 text-fog" />
              <span className="text-[14px] text-slate font-mono">{settings.domain}</span>
            </div>
          </div>

          <button
            onClick={handleSave}
            disabled={saving || orgName === settings.name}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-deep-indigo text-white text-[13px] font-medium hover:bg-deep-indigo/90 transition-colors disabled:opacity-50"
          >
            {saving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : saved ? (
              <Check className="w-4 h-4" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            {saving ? "Enregistrement..." : saved ? "Enregistré !" : "Enregistrer"}
          </button>
        </div>
      </div>

      {/* API keys */}
      <div className="bg-card-white rounded-xl border border-mist p-6 shadow-card">
        <div className="flex items-center gap-2 mb-5">
          <Key className="w-4.5 h-4.5 text-deep-indigo" />
          <h2 className="text-[15px] font-semibold text-deep-ink">Clés API</h2>
        </div>

        {settings.apiKeys.length > 0 ? (
          <div className="space-y-2">
            {settings.apiKeys.map(k => (
              <div key={k.id} className="flex items-center justify-between px-4 py-3 rounded-lg border border-mist/50 hover:bg-paper-white transition-colors">
                <div>
                  <p className="text-[13px] font-medium text-deep-ink">{k.name}</p>
                  <p className="text-[11px] font-mono text-slate">{k.key}</p>
                </div>
                <button
                  onClick={() => copyToClipboard(k.key, k.id)}
                  className="p-2 rounded-lg hover:bg-paper-white text-fog hover:text-deep-indigo transition-colors"
                >
                  {copiedKey === k.id ? <Check className="w-4 h-4 text-forest-teal" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="px-4 py-8 text-center">
            <Key className="w-8 h-8 text-mist mx-auto mb-2" />
            <p className="text-[13px] text-fog">Aucune clé API configurée.</p>
            <p className="text-[11px] text-fog mt-1">Générez une clé API depuis la page Paramètres de l&apos;application principale.</p>
          </div>
        )}
      </div>

      {/* Privacy / Data retention */}
      <div className="bg-card-white rounded-xl border border-mist p-6 shadow-card">
        <h3 className="text-[15px] font-semibold text-deep-ink mb-4">Confidentialité & données</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[13px] font-medium text-deep-ink">Rétention des données</p>
              <p className="text-[11px] text-slate">Durée de conservation des conversations et logs.</p>
            </div>
            <select className="px-3 py-1.5 rounded-lg border border-mist bg-paper-white text-[12px] text-deep-ink focus:outline-none">
              <option>30 jours</option>
              <option>90 jours</option>
              <option>1 an</option>
              <option>Illimité</option>
            </select>
          </div>
          <div className="border-t border-mist/50" />
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[13px] font-medium text-deep-ink">Partage de données (opt-in)</p>
              <p className="text-[11px] text-slate">Partager des données anonymisées pour améliorer Kinga.</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" className="sr-only peer" />
              <div className="w-9 h-5 bg-mist peer-focus:outline-none rounded-full peer peer-checked:bg-forest-teal transition-colors after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-4"></div>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
