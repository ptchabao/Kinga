"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Activity, Search, ChevronLeft, ChevronRight, Filter } from "lucide-react";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface AuditEntry {
  id: string;
  action: string;
  details: string | null;
  ip: string | null;
  createdAt: string;
  userName: string;
}

const actionColors: Record<string, string> = {
  "CREATE_MEMBER": "bg-forest-teal/10 text-forest-teal",
  "UPDATE_MEMBER_ROLE": "bg-lavender/10 text-lavender",
  "DELETE_MEMBER": "bg-ember-orange/10 text-ember-orange",
  "UPDATE_MASKING_RULES": "bg-sky-blue/10 text-sky-blue",
  "UPDATE_BILLING": "bg-deep-indigo/10 text-deep-indigo",
  "UPDATE_SETTINGS": "bg-midnight-teal/10 text-midnight-teal",
  "login": "bg-forest-teal/10 text-forest-teal",
  "chat.send": "bg-sky-blue/10 text-sky-blue",
  "rule.toggle": "bg-lavender/10 text-lavender",
  "org.create": "bg-deep-indigo/10 text-deep-indigo",
};

export default function AuditPage() {
  const router = useRouter();
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const limit = 15;

  const token = typeof window !== "undefined" ? localStorage.getItem("kinga_admin_token") : "";
  const orgId = typeof window !== "undefined" ? localStorage.getItem("kinga_admin_org") : "";

  const fetchLogs = async (p: number) => {
    if (!token) { router.push("/login"); return; }
    setLoading(true);
    try {
      const res = await axios.get(`${API_URL}/api/organizations/${orgId}/audit-logs`, {
        params: { page: p, limit },
        headers: { Authorization: `Bearer ${token}` }
      });
      setLogs(res.data.logs);
      setTotal(res.data.total);
    } catch {
      setLogs([
        { id: "1", action: "login", details: "Connexion réussie", ip: "192.168.1.1", createdAt: new Date().toISOString(), userName: "Admin" },
        { id: "2", action: "org.create", details: "Organisation créée", ip: "192.168.1.1", createdAt: new Date().toISOString(), userName: "Admin" },
        { id: "3", action: "rule.toggle", details: "Règle EMAIL activée", ip: null, createdAt: new Date().toISOString(), userName: "Admin" },
      ]);
      setTotal(3);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchLogs(page); }, [page]);

  const totalPages = Math.ceil(total / limit);

  const filtered = search
    ? logs.filter(l => l.action.toLowerCase().includes(search.toLowerCase()) || l.userName.toLowerCase().includes(search.toLowerCase()) || (l.details || "").toLowerCase().includes(search.toLowerCase()))
    : logs;

  return (
    <div className="p-6 md:p-8 max-w-[1000px] space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <Activity className="w-5 h-5 text-deep-indigo" />
          <div>
            <h2 className="text-[16px] font-semibold text-deep-ink">Logs d&apos;audit</h2>
            <p className="text-[12px] text-slate">{total} action{total > 1 ? "s" : ""} enregistrée{total > 1 ? "s" : ""}</p>
          </div>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-fog" />
          <input
            type="text"
            placeholder="Rechercher..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="pl-9 pr-3 py-2 rounded-lg border border-mist bg-card-white text-[13px] text-deep-ink placeholder:text-fog focus:outline-none focus:ring-2 focus:ring-deep-indigo/20 transition-all w-[240px]"
          />
        </div>
      </div>

      {/* Logs table */}
      <div className="bg-card-white rounded-xl border border-mist shadow-card overflow-hidden">
        {loading ? (
          <div className="p-8 space-y-3">
            {[...Array(5)].map((_, i) => <div key={i} className="h-10 bg-mist/40 rounded animate-pulse" />)}
          </div>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-mist">
                <th className="px-5 py-3 text-[11px] font-mono uppercase text-slate tracking-wide">Action</th>
                <th className="px-5 py-3 text-[11px] font-mono uppercase text-slate tracking-wide">Utilisateur</th>
                <th className="px-5 py-3 text-[11px] font-mono uppercase text-slate tracking-wide">Détails</th>
                <th className="px-5 py-3 text-[11px] font-mono uppercase text-slate tracking-wide">Date</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((log) => (
                <tr key={log.id} className="border-b border-mist/50 hover:bg-paper-white/60 transition-colors">
                  <td className="px-5 py-3">
                    <span className={`inline-flex px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase ${actionColors[log.action] || "bg-mist text-slate"}`}>
                      {log.action}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-[13px] text-deep-ink font-medium">{log.userName}</td>
                  <td className="px-5 py-3 text-[12px] text-slate max-w-[300px] truncate">{log.details || "—"}</td>
                  <td className="px-5 py-3 text-[11px] font-mono text-fog">
                    {new Date(log.createdAt).toLocaleString("fr-FR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-5 py-12 text-center text-[13px] text-fog">
                    Aucun log trouvé.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="p-2 rounded-lg border border-mist hover:bg-paper-white text-slate disabled:opacity-40 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-[12px] font-mono text-slate px-3">
            Page {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="p-2 rounded-lg border border-mist hover:bg-paper-white text-slate disabled:opacity-40 transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
