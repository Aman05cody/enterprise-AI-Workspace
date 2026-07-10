import { api, type ApiEnvelope } from "@/shared/api/client";

export type Connector = {
  id: string;
  organization_id: string;
  type: string;
  status: string;
  display_name: string;
  config: Record<string, unknown>;
  last_synced_at?: string | null;
};

export type RepoResource = {
  id: string;
  connector_id: string;
  external_id: string;
  name: string;
  resource_type: string;
  sync_enabled: boolean;
  metadata: Record<string, unknown>;
  knowledge_base_id?: string | null;
  last_synced_at?: string | null;
};

export type SyncJob = {
  id: string;
  connector_id: string;
  status: string;
  stats: Record<string, unknown>;
  error_message?: string | null;
};

export async function listGitHubConnectors(organizationId: string) {
  const { data } = await api.get<ApiEnvelope<Connector[]>>("/github/connectors", {
    params: { organization_id: organizationId },
  });
  return data.data;
}

export async function connectGitHub(input: {
  organization_id: string;
  personal_access_token: string;
  display_name?: string;
}) {
  const { data } = await api.post<ApiEnvelope<Connector>>("/github/connect", input);
  return data.data;
}

export async function disconnectGitHub(connectorId: string) {
  await api.delete(`/github/connectors/${connectorId}`);
}

export async function listRepos(connectorId: string) {
  const { data } = await api.get<ApiEnvelope<RepoResource[]>>(
    `/github/connectors/${connectorId}/repos`
  );
  return data.data;
}

export async function refreshRepos(connectorId: string) {
  const { data } = await api.post<ApiEnvelope<RepoResource[]>>(
    `/github/connectors/${connectorId}/refresh-repos`
  );
  return data.data;
}

export async function selectRepos(connectorId: string, resourceIds: string[]) {
  const { data } = await api.put<ApiEnvelope<RepoResource[]>>(
    `/github/connectors/${connectorId}/repos/selection`,
    { resource_ids: resourceIds }
  );
  return data.data;
}

export async function syncGitHub(connectorId: string, resourceId?: string) {
  const { data } = await api.post<ApiEnvelope<SyncJob>>(
    `/github/connectors/${connectorId}/sync`,
    { resource_id: resourceId }
  );
  return data.data;
}

export async function reviewPull(input: {
  connector_id: string;
  owner: string;
  repo: string;
  pull_number: number;
}) {
  const { data } = await api.post<ApiEnvelope<Record<string, unknown>>>(
    "/github/pulls/review",
    input
  );
  return data.data;
}

export async function explainFile(input: {
  connector_id: string;
  owner: string;
  repo: string;
  path: string;
  ref?: string;
  focus?: string;
}) {
  const { data } = await api.post<ApiEnvelope<Record<string, unknown>>>(
    "/github/explain",
    input
  );
  return data.data;
}

export async function generateDocs(input: {
  connector_id: string;
  owner: string;
  repo: string;
  path: string;
}) {
  const { data } = await api.post<ApiEnvelope<Record<string, unknown>>>(
    "/github/generate-docs",
    input
  );
  return data.data;
}

export async function generateTests(input: {
  connector_id: string;
  owner: string;
  repo: string;
  path: string;
}) {
  const { data } = await api.post<ApiEnvelope<Record<string, unknown>>>(
    "/github/generate-tests",
    input
  );
  return data.data;
}

export async function explainArchitecture(resourceId: string) {
  const { data } = await api.post<ApiEnvelope<Record<string, unknown>>>(
    `/github/repos/${resourceId}/architecture`
  );
  return data.data;
}

export async function chatWithRepo(
  resourceId: string,
  question: string,
  conversationId?: string
) {
  const { data } = await api.post<ApiEnvelope<Record<string, unknown>>>(
    `/github/repos/${resourceId}/chat`,
    { question, conversation_id: conversationId }
  );
  return data.data;
}
