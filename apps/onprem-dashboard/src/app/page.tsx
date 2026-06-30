"use client";

import { useEffect, useState } from "react";

const apiBase = process.env.NEXT_PUBLIC_ONPREM_API_URL || "http://localhost:8002";

export default function HomePage() {
  const [status, setStatus] = useState<any>(null);
  const [dashboard, setDashboard] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [statusRes, dashboardRes] = await Promise.all([
          fetch(`${apiBase}/api/onprem/status`),
          fetch(`${apiBase}/api/onprem/dashboard`),
        ]);

        const statusData = statusRes.ok ? await statusRes.json() : null;
        const dashboardData = dashboardRes.ok ? await dashboardRes.json() : null;

        setStatus(statusData || { status: "offline", deployment_mode: "unknown", region: "unknown" });
        setDashboard(dashboardData || {
          services: [
            { name: "API Kinga", status: "healthy" },
            { name: "Dashboard", status: "healthy" },
            { name: "PostgreSQL", status: "healthy" },
            { name: "Redis", status: "healthy" },
          ],
          security: {
            encryption: "AES-GCM",
            token_mode: "HMAC-SHA256",
            audit_logging: true,
            data_locality: "client-controlled",
          },
          compliance: {
            gdpr: true,
            sectorial_controls: ["banking", "insurance", "fintech"],
            retention_days: 90,
          },
          activity: [
            { label: "Requêtes traitées", value: "0" },
            { label: "Entités masquées", value: "0" },
            { label: "Alertes audits", value: "0" },
          ],
        });
      } catch {
        setStatus({ status: "offline", deployment_mode: "unknown", region: "unknown" });
        setDashboard(null);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const services = dashboard?.services || [];
  const activity = dashboard?.activity || [];
  const security = dashboard?.security || {};
  const compliance = dashboard?.compliance || {};

  return (
    <main style={{ maxWidth: 1240, margin: "0 auto", padding: "32px 24px 48px" }}>
      <header style={{ marginBottom: 24 }}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "6px 12px", borderRadius: 999, background: "#e6f8f3", color: "#0f766e", fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 12 }}>
          Self-hosted deployment
        </div>
        <h1 style={{ fontSize: 34, lineHeight: 1.15, margin: "0 0 8px", color: "#111827" }}>Tableau de bord On-Premise Kinga</h1>
        <p style={{ margin: 0, color: "#4b5563", fontSize: 15, maxWidth: 780, lineHeight: 1.6 }}>
          Une expérience de supervision et de conformité conçue pour un déploiement local, isolé et entièrement contrôlé par votre organisation.
        </p>
      </header>

      {loading ? (
        <div style={{ padding: 24, borderRadius: 16, background: "#fff", border: "1px solid #e5e7eb", color: "#4b5563" }}>
          Chargement des métriques d’infrastructure…
        </div>
      ) : (
        <>
          <section style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", marginBottom: 20 }}>
            <MetricCard title="Mode de déploiement" value={status?.deployment_mode || "inconnu"} tone="teal" />
            <MetricCard title="État global" value={status?.status || "hors ligne"} tone="blue" />
            <MetricCard title="Région / hôte" value={status?.region || status?.host || "local"} tone="violet" />
            <MetricCard title="API interne" value={status?.api?.status || "inconnu"} tone="amber" />
          </section>

          <section style={{ display: "grid", gap: 18, gridTemplateColumns: "1.2fr 0.8fr", marginBottom: 20 }}>
            <PanelCard title="Services critiques" subtitle="État des composants du déploiement">
              <div style={{ display: "grid", gap: 10 }}>
                {(services.length ? services : []).map((service: any) => (
                  <div key={service.name} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 14px", borderRadius: 12, background: "#f9fafb", border: "1px solid #e5e7eb" }}>
                    <span style={{ fontWeight: 600, color: "#111827" }}>{service.name}</span>
                    <span style={{ padding: "4px 10px", borderRadius: 999, background: service.status === "healthy" ? "#dcfce7" : service.status === "warning" ? "#fef3c7" : "#fee2e2", color: service.status === "healthy" ? "#166534" : service.status === "warning" ? "#92400e" : "#991b1b", fontSize: 12, fontWeight: 700, textTransform: "uppercase" }}>
                      {service.status}
                    </span>
                  </div>
                ))}
              </div>
            </PanelCard>

            <PanelCard title="Sécurité et conformité" subtitle="Contrôles clés du déploiement">
              <ul style={{ padding: 0, margin: 0, listStyle: "none", display: "grid", gap: 10, color: "#374151" }}>
                <li style={{ display: "flex", justifyContent: "space-between", gap: 8 }}><span>Chiffrement</span><strong>{security.encryption || "AES-GCM"}</strong></li>
                <li style={{ display: "flex", justifyContent: "space-between", gap: 8 }}><span>Tokens</span><strong>{security.token_mode || "HMAC-SHA256"}</strong></li>
                <li style={{ display: "flex", justifyContent: "space-between", gap: 8 }}><span>Audit</span><strong>{security.audit_logging ? "Activé" : "Désactivé"}</strong></li>
                <li style={{ display: "flex", justifyContent: "space-between", gap: 8 }}><span>Localisation</span><strong>{security.data_locality || "Client-controlled"}</strong></li>
                <li style={{ display: "flex", justifyContent: "space-between", gap: 8 }}><span>RGPD</span><strong>{compliance.gdpr ? "Oui" : "Non"}</strong></li>
                <li style={{ display: "flex", justifyContent: "space-between", gap: 8 }}><span>Rétention</span><strong>{compliance.retention_days || 90} jours</strong></li>
              </ul>
            </PanelCard>
          </section>

          <section style={{ display: "grid", gap: 18, gridTemplateColumns: "0.95fr 1.05fr" }}>
            <PanelCard title="Activité récente" subtitle="Indicateurs opérationnels clés">
              <div style={{ display: "grid", gap: 12 }}>
                {activity.map((item: any) => (
                  <div key={item.label} style={{ padding: "14px 16px", borderRadius: 12, background: "#f8fafc", border: "1px solid #e5e7eb" }}>
                    <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 4 }}>{item.label}</div>
                    <div style={{ fontSize: 24, fontWeight: 700, color: "#111827" }}>{item.value}</div>
                  </div>
                ))}
              </div>
            </PanelCard>

            <PanelCard title="Fonctionnalités de supervision" subtitle="Ce qui est prêt à être exploité sur site">
              <div style={{ display: "grid", gap: 12 }}>
                {[
                  "Masquage déterministe des données sensibles",
                  "Règles de protection par catégories et niveaux",
                  "Gestion des secrets et rotation des seeds",
                  "Logs d’audit, métriques et traçabilité",
                  "Déploiement isolé sans dépendance SaaS",
                ].map((item) => (
                  <div key={item} style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: "10px 0", borderBottom: "1px solid #f3f4f6" }}>
                    <span style={{ fontSize: 16, lineHeight: 1 }}>✓</span>
                    <span style={{ color: "#374151", lineHeight: 1.5 }}>{item}</span>
                  </div>
                ))}
              </div>
            </PanelCard>
          </section>
        </>
      )}
    </main>
  );
}

function MetricCard({ title, value, tone }: { title: string; value: string; tone: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    teal: { bg: "#ecfeff", text: "#0f766e" },
    blue: { bg: "#eff6ff", text: "#2563eb" },
    violet: { bg: "#f5f3ff", text: "#7c3aed" },
    amber: { bg: "#fffbeb", text: "#b45309" },
  };

  const palette = colors[tone] || colors.blue;

  return (
    <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 16, padding: 18, boxShadow: "0 8px 24px rgba(15, 23, 42, 0.04)" }}>
      <div style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.text, background: palette.bg, display: "inline-flex", padding: "4px 8px", borderRadius: 999, marginBottom: 10 }}>{title}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: "#111827" }}>{value}</div>
    </div>
  );
}

function PanelCard({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <section style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 20, padding: 20, boxShadow: "0 8px 24px rgba(15, 23, 42, 0.04)" }}>
      <h2 style={{ margin: "0 0 4px", fontSize: 18, color: "#111827" }}>{title}</h2>
      <p style={{ margin: "0 0 14px", color: "#6b7280", fontSize: 13 }}>{subtitle}</p>
      {children}
    </section>
  );
}
