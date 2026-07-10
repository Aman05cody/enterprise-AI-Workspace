"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { listOrganizations } from "@/features/auth/api";
import {
  formatBytes,
  getAuditLogs,
  getDepartments,
  getMetrics,
  getOverview,
  getPopularDocuments,
  getSearchTrends,
  getStorage,
  getTopUsers,
  getUsage,
} from "@/features/analytics/api";
import { Button } from "@/shared/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/ui/card";
import { PageContainer, PageHeader } from "@/shared/ui/app-shell";

const COLORS = ["#818cf8", "#34d399", "#fbbf24", "#c084fc", "#f87171", "#22d3ee"];

function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div className="rounded-2xl border border-white/[0.07] bg-card/60 p-4 shadow-lg shadow-black/10 backdrop-blur">
      <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-1.5 text-2xl font-semibold tracking-tight">{value}</p>
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

export default function AnalyticsPage() {
  const router = useRouter();
  const [orgId, setOrgId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!localStorage.getItem("eaw_access_token")) router.replace("/login");
    const stored = localStorage.getItem("eaw_org_id");
    if (stored) setOrgId(stored);
  }, [router]);

  const orgs = useQuery({ queryKey: ["organizations"], queryFn: listOrganizations });
  useEffect(() => {
    if (!orgId && orgs.data?.length) {
      setOrgId(orgs.data[0].id);
      localStorage.setItem("eaw_org_id", orgs.data[0].id);
    }
  }, [orgs.data, orgId]);

  const overview = useQuery({
    queryKey: ["analytics-overview", orgId],
    queryFn: () => getOverview(orgId!),
    enabled: !!orgId,
    retry: false,
  });
  const usage = useQuery({
    queryKey: ["analytics-usage", orgId],
    queryFn: () => getUsage(orgId!),
    enabled: !!orgId,
    retry: false,
  });
  const popular = useQuery({
    queryKey: ["analytics-popular", orgId],
    queryFn: () => getPopularDocuments(orgId!),
    enabled: !!orgId,
    retry: false,
  });
  const depts = useQuery({
    queryKey: ["analytics-depts", orgId],
    queryFn: () => getDepartments(orgId!),
    enabled: !!orgId,
    retry: false,
  });
  const storage = useQuery({
    queryKey: ["analytics-storage", orgId],
    queryFn: () => getStorage(orgId!),
    enabled: !!orgId,
    retry: false,
  });
  const trends = useQuery({
    queryKey: ["analytics-trends", orgId],
    queryFn: () => getSearchTrends(orgId!),
    enabled: !!orgId,
    retry: false,
  });
  const topUsers = useQuery({
    queryKey: ["analytics-users", orgId],
    queryFn: () => getTopUsers(orgId!),
    enabled: !!orgId,
    retry: false,
  });
  const audits = useQuery({
    queryKey: ["analytics-audit", orgId],
    queryFn: () => getAuditLogs(orgId!),
    enabled: !!orgId,
    retry: false,
  });
  const metrics = useQuery({
    queryKey: ["metrics"],
    queryFn: getMetrics,
    refetchInterval: 15000,
  });

  useEffect(() => {
    if (overview.isError) {
      setError(
        "Analytics requires Manager+ role. Switch to an admin/owner account if needed."
      );
    } else {
      setError(null);
    }
  }, [overview.isError]);

  const ov = overview.data;
  const sourcePie =
    (storage.data?.by_source as { source_type: string; bytes: number; count: number }[]) ||
    [];

  return (
    <PageContainer wide>
      <PageHeader
        title="Admin analytics"
        description="Usage, storage, search trends, audit trail, and system health."
        actions={
          orgs.data ? (
            <select
              className="h-11 rounded-xl border border-white/10 bg-white/[0.03] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/30"
              value={orgId ?? ""}
              onChange={(e) => {
                setOrgId(e.target.value);
                localStorage.setItem("eaw_org_id", e.target.value);
              }}
            >
              {orgs.data.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name} ({o.my_role})
                </option>
              ))}
            </select>
          ) : undefined
        }
      />

      {error && (
        <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Members" value={ov?.members ?? "—"} />
        <Stat
          label="Active users (30d)"
          value={ov?.active_users ?? "—"}
          hint="From usage events"
        />
        <Stat label="Documents" value={ov?.documents ?? "—"} />
        <Stat
          label="Storage"
          value={ov ? formatBytes(ov.storage_bytes) : "—"}
        />
        <Stat label="Knowledge bases" value={ov?.knowledge_bases ?? "—"} />
        <Stat label="Chat messages (30d)" value={ov?.chat_messages ?? "—"} />
        <Stat label="Tokens in" value={ov?.tokens_in ?? "—"} />
        <Stat label="Tokens out" value={ov?.tokens_out ?? "—"} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Usage over time</CardTitle>
            <CardDescription>Events by day (uploads, chat, embed…)</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={usage.data || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="#94a3b8" />
                <YAxis tick={{ fontSize: 10 }} stroke="#94a3b8" />
                <Tooltip
                  contentStyle={{
                    background: "#0f172a",
                    border: "1px solid #334155",
                  }}
                />
                <Legend />
                <Line type="monotone" dataKey="total" stroke="#3b82f6" strokeWidth={2} />
                <Line type="monotone" dataKey="chat" stroke="#22c55e" strokeWidth={1.5} />
                <Line type="monotone" dataKey="upload" stroke="#f59e0b" strokeWidth={1.5} />
                <Line type="monotone" dataKey="embed" stroke="#a855f7" strokeWidth={1.5} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Storage by source</CardTitle>
            <CardDescription>Upload vs connectors</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={sourcePie}
                  dataKey="bytes"
                  nameKey="source_type"
                  outerRadius={90}
                  label={(e) => e.source_type}
                >
                  {sourcePie.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(v: number) => formatBytes(Number(v))}
                  contentStyle={{
                    background: "#0f172a",
                    border: "1px solid #334155",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Department activity</CardTitle>
            <CardDescription>Usage events last 30 days</CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={depts.data || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} stroke="#94a3b8" />
                <YAxis tick={{ fontSize: 10 }} stroke="#94a3b8" />
                <Tooltip
                  contentStyle={{
                    background: "#0f172a",
                    border: "1px solid #334155",
                  }}
                />
                <Bar dataKey="events" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Popular documents</CardTitle>
            <CardDescription>Most cited in chat answers</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {(popular.data || []).length === 0 && (
              <p className="text-sm text-muted-foreground">No citations yet.</p>
            )}
            {(popular.data || []).map((d) => (
              <div
                key={String(d.document_id)}
                className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
              >
                <span className="truncate pr-2">{String(d.title)}</span>
                <span className="text-xs text-muted-foreground">
                  {String(d.citations)} cites
                </span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Search trends</CardTitle>
            <CardDescription>Frequent chat query phrases</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {(trends.data || []).slice(0, 12).map((t) => (
              <div
                key={String(t.query)}
                className="flex justify-between gap-2 text-sm"
              >
                <span className="truncate text-muted-foreground">{String(t.query)}</span>
                <span>{String(t.count)}</span>
              </div>
            ))}
            {(trends.data || []).length === 0 && (
              <p className="text-sm text-muted-foreground">No query trends yet.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top users</CardTitle>
            <CardDescription>By usage events (30d)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {(topUsers.data || []).map((u) => (
              <div
                key={String(u.user_id)}
                className="flex justify-between text-sm"
              >
                <span>{String(u.full_name || u.email || u.user_id)}</span>
                <span className="text-muted-foreground">{String(u.events)}</span>
              </div>
            ))}
            {(topUsers.data || []).length === 0 && (
              <p className="text-sm text-muted-foreground">No usage yet.</p>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>System monitoring</CardTitle>
            <CardDescription>Dependency checks and queue depth</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-3">
            <div className="rounded-md border border-border p-3 text-sm">
              <p className="text-muted-foreground">Status</p>
              <p className="text-lg font-semibold">
                {String(metrics.data?.status || "…")}
              </p>
              <p className="text-xs text-muted-foreground">
                v{String((metrics.data as { version?: string })?.version || "")}
              </p>
            </div>
            <div className="rounded-md border border-border p-3 text-sm">
              <p className="mb-1 text-muted-foreground">Checks</p>
              <pre className="whitespace-pre-wrap text-xs">
                {JSON.stringify(metrics.data?.checks || {}, null, 2)}
              </pre>
            </div>
            <div className="rounded-md border border-border p-3 text-sm">
              <p className="mb-1 text-muted-foreground">Queues</p>
              <pre className="whitespace-pre-wrap text-xs">
                {JSON.stringify(metrics.data?.queues || {}, null, 2)}
              </pre>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Audit log</CardTitle>
              <CardDescription>Admin-only security trail</CardDescription>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => audits.refetch()}
            >
              Refresh
            </Button>
          </CardHeader>
          <CardContent className="max-h-80 space-y-2 overflow-y-auto">
            {(audits.data || []).map((a) => (
              <div
                key={a.id}
                className="rounded-md border border-border px-3 py-2 text-xs"
              >
                <div className="flex justify-between gap-2">
                  <span className="font-medium">{a.action}</span>
                  <span className="text-muted-foreground">
                    {new Date(a.created_at).toLocaleString()}
                  </span>
                </div>
                <p className="mt-1 text-muted-foreground">
                  actor {a.actor_user_id || "—"} · {a.resource_type || "—"}
                </p>
              </div>
            ))}
            {(audits.data || []).length === 0 && (
              <p className="text-sm text-muted-foreground">
                No audit events (or admin role required).
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  );
}
