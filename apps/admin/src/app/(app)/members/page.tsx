"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { UserPlus, MoreHorizontal, Search, ChevronDown, X, Loader2 } from "lucide-react";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Member {
  id: string;
  userId: string;
  email: string;
  name: string;
  role: string;
  createdAt: string;
}

export default function MembersPage() {
  const router = useRouter();
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [showInvite, setShowInvite] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("MEMBER");
  const [inviting, setInviting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const token = typeof window !== "undefined" ? localStorage.getItem("kinga_admin_token") : "";
  const orgId = typeof window !== "undefined" ? localStorage.getItem("kinga_admin_org") : "";

  const fetchMembers = async () => {
    if (!token) { router.push("/login"); return; }
    try {
      const res = await axios.get(`${API_URL}/api/organizations/${orgId}/members`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMembers(res.data);
    } catch {
      // Fallback mock
      setMembers([
        { id: "1", userId: "u1", email: "admin@kinga.ai", name: "Admin", role: "ADMIN", createdAt: new Date().toISOString() },
        { id: "2", userId: "u2", email: "manager@kinga.ai", name: "Manager", role: "MANAGER", createdAt: new Date().toISOString() },
        { id: "3", userId: "u3", email: "user@kinga.ai", name: "Utilisateur", role: "MEMBER", createdAt: new Date().toISOString() },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchMembers(); }, []);

  const handleInvite = async () => {
    setInviting(true);
    try {
      await axios.post(`${API_URL}/api/organizations/${orgId}/members`, {
        email: inviteEmail,
        role: inviteRole
      }, { headers: { Authorization: `Bearer ${token}` } });
      setShowInvite(false);
      setInviteEmail("");
      fetchMembers();
    } catch {}
    setInviting(false);
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await axios.patch(`${API_URL}/api/organizations/${orgId}/members/${userId}`, {
        role: newRole
      }, { headers: { Authorization: `Bearer ${token}` } });
      setEditingId(null);
      fetchMembers();
    } catch {}
  };

  const handleRemove = async (userId: string) => {
    if (!confirm("Retirer ce membre de l'organisation ?")) return;
    try {
      await axios.delete(`${API_URL}/api/organizations/${orgId}/members/${userId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchMembers();
    } catch {}
  };

  const filtered = members.filter(m => {
    const matchSearch = m.name.toLowerCase().includes(search.toLowerCase()) || m.email.toLowerCase().includes(search.toLowerCase());
    const matchRole = roleFilter === "all" || m.role === roleFilter;
    return matchSearch && matchRole;
  });

  const roleColors: Record<string, string> = {
    ADMIN: "bg-deep-indigo/10 text-deep-indigo",
    MANAGER: "bg-lavender/10 text-lavender",
    MEMBER: "bg-forest-teal/10 text-forest-teal",
  };

  if (loading) {
    return (
      <div className="p-8 space-y-4">
        {[...Array(4)].map((_, i) => <div key={i} className="h-16 bg-mist/40 rounded-xl animate-pulse" />)}
      </div>
    );
  }

  return (
    <div className="p-6 md:p-8 max-w-[1000px] space-y-6">
      {/* Top bar */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3 flex-1 min-w-[200px]">
          <div className="relative flex-1 max-w-[320px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-fog" />
            <input
              type="text"
              placeholder="Rechercher un membre..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-lg border border-mist bg-card-white text-[13px] text-deep-ink placeholder:text-fog focus:outline-none focus:ring-2 focus:ring-deep-indigo/20 focus:border-deep-indigo/40 transition-all"
            />
          </div>
          <select
            value={roleFilter}
            onChange={e => setRoleFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-mist bg-card-white text-[13px] text-deep-ink focus:outline-none focus:ring-2 focus:ring-deep-indigo/20"
          >
            <option value="all">Tous les rôles</option>
            <option value="ADMIN">Admin</option>
            <option value="MANAGER">Manager</option>
            <option value="MEMBER">Membre</option>
          </select>
        </div>
        <button
          onClick={() => setShowInvite(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-deep-indigo text-white text-[13px] font-medium hover:bg-deep-indigo/90 transition-colors"
        >
          <UserPlus className="w-4 h-4" />
          Inviter un membre
        </button>
      </div>

      {/* Invite Modal */}
      {showInvite && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={() => setShowInvite(false)}>
          <div className="bg-card-white rounded-xl border border-mist shadow-elevated p-6 w-full max-w-[420px] mx-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-[16px] font-semibold text-deep-ink">Inviter un membre</h3>
              <button onClick={() => setShowInvite(false)} className="p-1 rounded-md hover:bg-paper-white text-fog"><X className="w-4 h-4" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-[12px] font-medium text-graphite mb-1.5">Email</label>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={e => setInviteEmail(e.target.value)}
                  placeholder="membre@entreprise.com"
                  className="w-full px-3.5 py-2.5 rounded-lg border border-mist bg-paper-white text-[14px] text-deep-ink placeholder:text-fog focus:outline-none focus:ring-2 focus:ring-deep-indigo/20 focus:border-deep-indigo/40 transition-all"
                />
              </div>
              <div>
                <label className="block text-[12px] font-medium text-graphite mb-1.5">Rôle</label>
                <select
                  value={inviteRole}
                  onChange={e => setInviteRole(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-mist bg-paper-white text-[14px] text-deep-ink focus:outline-none focus:ring-2 focus:ring-deep-indigo/20"
                >
                  <option value="MEMBER">Membre</option>
                  <option value="MANAGER">Manager</option>
                  <option value="ADMIN">Admin</option>
                </select>
              </div>
              <button
                onClick={handleInvite}
                disabled={inviting || !inviteEmail}
                className="w-full py-2.5 rounded-lg bg-deep-indigo text-white text-[14px] font-medium hover:bg-deep-indigo/90 transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
              >
                {inviting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                {inviting ? "Envoi..." : "Envoyer l'invitation"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Members Table */}
      <div className="bg-card-white rounded-xl border border-mist shadow-card overflow-hidden">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-mist">
              <th className="px-5 py-3 text-[11px] font-mono uppercase text-slate tracking-wide">Membre</th>
              <th className="px-5 py-3 text-[11px] font-mono uppercase text-slate tracking-wide">Rôle</th>
              <th className="px-5 py-3 text-[11px] font-mono uppercase text-slate tracking-wide">Date d&apos;ajout</th>
              <th className="px-5 py-3 text-[11px] font-mono uppercase text-slate tracking-wide w-[100px]">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((member) => (
              <tr key={member.id} className="border-b border-mist/50 hover:bg-paper-white/60 transition-colors">
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-deep-indigo/10 flex items-center justify-center">
                      <span className="text-[12px] font-semibold text-deep-indigo">
                        {(member.name || member.email).charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div>
                      <p className="text-[13px] font-medium text-deep-ink">{member.name}</p>
                      <p className="text-[11px] text-slate">{member.email}</p>
                    </div>
                  </div>
                </td>
                <td className="px-5 py-3.5">
                  {editingId === member.userId ? (
                    <select
                      defaultValue={member.role}
                      onChange={e => handleRoleChange(member.userId, e.target.value)}
                      onBlur={() => setEditingId(null)}
                      autoFocus
                      className="px-2 py-1 rounded border border-deep-indigo/30 text-[12px] bg-card-white focus:outline-none"
                    >
                      <option value="MEMBER">Membre</option>
                      <option value="MANAGER">Manager</option>
                      <option value="ADMIN">Admin</option>
                    </select>
                  ) : (
                    <span className={`inline-flex px-2.5 py-1 rounded-md text-[11px] font-mono font-semibold uppercase ${roleColors[member.role] || "bg-mist text-slate"}`}>
                      {member.role}
                    </span>
                  )}
                </td>
                <td className="px-5 py-3.5 text-[12px] text-slate">
                  {new Date(member.createdAt).toLocaleDateString("fr-FR")}
                </td>
                <td className="px-5 py-3.5">
                  <div className="flex gap-1">
                    <button
                      onClick={() => setEditingId(member.userId)}
                      className="px-2 py-1 text-[11px] rounded-md text-slate hover:text-deep-indigo hover:bg-paper-white transition-colors"
                    >
                      Modifier
                    </button>
                    <button
                      onClick={() => handleRemove(member.userId)}
                      className="px-2 py-1 text-[11px] rounded-md text-slate hover:text-ember-orange hover:bg-ember-orange/5 transition-colors"
                    >
                      Retirer
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={4} className="px-5 py-12 text-center text-[13px] text-fog">
                  Aucun membre trouvé.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="text-[11px] text-fog text-center">
        {members.length} membre{members.length > 1 ? "s" : ""} dans l&apos;organisation
      </p>
    </div>
  );
}
