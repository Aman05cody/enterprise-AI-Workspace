import { api, type ApiEnvelope } from "@/shared/api/client";

export type Overview = {
  period_days: number;
  members: number;
  active_users: number;
  knowledge_bases: number;
  documents: number;
  storage_bytes: number;
  chat_messages: number;
  usage_by_type: Record<string, number>;
  tokens_in: number;
  tokens_out: number;
  tokens_total: number;
};

export type UsagePoint = {
  date: string;
  total: number;
  [key: string]: string | number;
};

export type AuditLog = {
  id: string;
  action: string;
  actor_user_id?: string | null;
  resource_type?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

export async function getOverview(orgId: string, days = 30) {
  const { data } = await api.get<ApiEnvelope<Overview>>(
    `/organizations/${orgId}/analytics/overview`,
    { params: { days } }
  );
  return data.data;
}

export async function getUsage(orgId: string, days = 14) {
  const { data } = await api.get<ApiEnvelope<UsagePoint[]>>(
    `/organizations/${orgId}/analytics/usage`,
    { params: { days } }
  );
  return data.data;
}

export async function getPopularDocuments(orgId: string) {
  const { data } = await api.get<ApiEnvelope<Record<string, unknown>[]>>(
    `/organizations/${orgId}/analytics/popular-documents`
  );
  return data.data;
}

export async function getDepartments(orgId: string) {
  const { data } = await api.get<ApiEnvelope<Record<string, unknown>[]>>(
    `/organizations/${orgId}/analytics/departments`
  );
  return data.data;
}

export async function getStorage(orgId: string) {
  const { data } = await api.get<ApiEnvelope<Record<string, unknown>>>(
    `/organizations/${orgId}/analytics/storage`
  );
  return data.data;
}

export async function getSearchTrends(orgId: string) {
  const { data } = await api.get<ApiEnvelope<Record<string, unknown>[]>>(
    `/organizations/${orgId}/analytics/search-trends`
  );
  return data.data;
}

export async function getTopUsers(orgId: string) {
  const { data } = await api.get<ApiEnvelope<Record<string, unknown>[]>>(
    `/organizations/${orgId}/analytics/top-users`
  );
  return data.data;
}

export async function getAuditLogs(orgId: string) {
  const { data } = await api.get<ApiEnvelope<AuditLog[]>>(
    `/organizations/${orgId}/audit-logs`,
    { params: { limit: 40 } }
  );
  return data.data;
}

export async function getMetrics() {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${base}/metrics`);
  if (!res.ok) throw new Error("Failed to load metrics");
  return res.json() as Promise<Record<string, unknown>>;
}

export function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}
