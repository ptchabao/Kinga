"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Shield, Eye, EyeOff, Loader2 } from "lucide-react";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AdminLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await axios.post(`${API_URL}/api/auth/login`, { email, password });
      const { token, user } = res.data;

      // Verify the user is an admin of at least one organization
      const profileRes = await axios.get(`${API_URL}/api/auth/profile`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      const role = profileRes.data.role;
      if (!role || role.toLowerCase() !== "admin") {
        setError("Accès refusé. Seuls les administrateurs peuvent accéder à cette console.");
        setLoading(false);
        return;
      }

      localStorage.setItem("kinga_admin_token", token);
      localStorage.setItem("kinga_admin_user", JSON.stringify(user));
      localStorage.setItem("kinga_admin_org", profileRes.data.orgId || "");
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Erreur de connexion.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-paper-white relative overflow-hidden">
      {/* Subtle grid background */}
      <div className="absolute inset-0 opacity-[0.03]" style={{
        backgroundImage: "linear-gradient(#111a4a 1px, transparent 1px), linear-gradient(90deg, #111a4a 1px, transparent 1px)",
        backgroundSize: "60px 60px"
      }} />

      <div className="w-full max-w-[420px] mx-4 relative z-10">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-11 h-11 rounded-xl bg-deep-indigo flex items-center justify-center shadow-sm">
            <Shield className="w-5.5 h-5.5 text-white" />
          </div>
          <div>
            <h1 className="text-[22px] font-semibold text-deep-ink tracking-[-0.3px]">
              Kinga
            </h1>
            <p className="text-[11px] font-mono uppercase tracking-widest text-slate -mt-0.5">
              Administration
            </p>
          </div>
        </div>

        {/* Card */}
        <div className="bg-card-white rounded-xl border border-mist shadow-card p-8">
          <h2 className="text-[18px] font-semibold text-deep-ink mb-1">
            Connexion administrateur
          </h2>
          <p className="text-[13px] text-slate mb-6">
            Accédez à la console d&apos;administration de votre organisation.
          </p>

          <form onSubmit={handleLogin} className="flex flex-col gap-4">
            <div>
              <label className="block text-[12px] font-medium text-graphite mb-1.5">
                Adresse email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@entreprise.com"
                required
                className="w-full px-3.5 py-2.5 rounded-lg border border-mist bg-paper-white text-[14px] text-deep-ink placeholder:text-fog focus:outline-none focus:ring-2 focus:ring-deep-indigo/20 focus:border-deep-indigo/40 transition-all"
              />
            </div>

            <div>
              <label className="block text-[12px] font-medium text-graphite mb-1.5">
                Mot de passe
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full px-3.5 py-2.5 rounded-lg border border-mist bg-paper-white text-[14px] text-deep-ink placeholder:text-fog focus:outline-none focus:ring-2 focus:ring-deep-indigo/20 focus:border-deep-indigo/40 transition-all pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-fog hover:text-slate transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="bg-ember-orange/8 border border-ember-orange/20 rounded-lg px-3.5 py-2.5 text-[13px] text-ember-orange font-medium">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-lg bg-deep-indigo text-white text-[14px] font-medium hover:bg-deep-indigo/90 transition-colors disabled:opacity-60 flex items-center justify-center gap-2 mt-1"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Vérification...
                </>
              ) : (
                "Se connecter"
              )}
            </button>
          </form>
        </div>

        <p className="text-center text-[11px] text-fog mt-6">
          Kinga · Console d&apos;administration sécurisée
        </p>
      </div>
    </div>
  );
}
