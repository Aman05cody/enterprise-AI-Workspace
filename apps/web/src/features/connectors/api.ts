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

export type ConnectorResource = {
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

// ── Notion ──────────────────────────────────────────────

export async function connectNotion(input: {
  organization_id: string;
  integration_token: string;
  display_name?: string;
}) {
  const { data } = await api.post<ApiEnvelope<Connector>>("/notion/connect", input);
  return data.data;
}

export async function listNotionConnectors(organizationId: string) {
  const { data } = await api.get<ApiEnvelope<Connector[]>>("/notion/connectors", {
    params: { organization_id: organizationId },
  });
  return data.data;
}

export async function disconnectNotion(connectorId: string) {
  await api.delete(`/notion/connectors/${connectorId}`);
}

export async function listNotionPages(connectorId: string) {
  const { data } = await api.get<ApiEnvelope<ConnectorResource[]>>(
    `/notion/connectors/${connectorId}/pages`
  );
  return data.data;
}

export async function refreshNotionPages(connectorId: string) {
  const { data } = await api.post<ApiEnvelope<ConnectorResource[]>>(
    `/notion/connectors/${connectorId}/refresh-pages`
  );
  return data.data;
}

export async function selectNotionPages(connectorId: string, resourceIds: string[]) {
  const { data } = await api.put<ApiEnvelope<ConnectorResource[]>>(
    `/notion/connectors/${connectorId}/pages/selection`,
    { resource_ids: resourceIds }
  );
  return data.data;
}

export async function syncNotion(connectorId: string, resourceId?: string) {
  const { data } = await api.post<ApiEnvelope<SyncJob>>(
    `/notion/connectors/${connectorId}/sync`,
    { resource_id: resourceId }
  );
  return data.data;
}

// ── Google Drive ────────────────────────────────────────

export async function connectDrive(input: {
  organization_id: string;
  access_token: string;
  refresh_token?: string;
  client_id?: string;
  client_secret?: string;
  display_name?: string;
}) {
  const { data } = await api.post<ApiEnvelope<Connector>>("/drive/connect", input);
  return data.data;
}

export async function listDriveConnectors(organizationId: string) {
  const { data } = await api.get<ApiEnvelope<Connector[]>>("/drive/connectors", {
    params: { organization_id: organizationId },
  });
  return data.data;
}

export async function disconnectDrive(connectorId: string) {
  await api.delete(`/drive/connectors/${connectorId}`);
}

export async function listDriveFolders(connectorId: string) {
  const { data } = await api.get<ApiEnvelope<ConnectorResource[]>>(
    `/drive/connectors/${connectorId}/folders`
  );
  return data.data;
}

export async function refreshDriveFolders(connectorId: string) {
  const { data } = await api.post<ApiEnvelope<ConnectorResource[]>>(
    `/drive/connectors/${connectorId}/refresh-folders`
  );
  return data.data;
}

export async function selectDriveFolders(connectorId: string, resourceIds: string[]) {
  const { data } = await api.put<ApiEnvelope<ConnectorResource[]>>(
    `/drive/connectors/${connectorId}/folders/selection`,
    { resource_ids: resourceIds }
  );
  return data.data;
}

export async function syncDrive(connectorId: string, resourceId?: string) {
  const { data } = await api.post<ApiEnvelope<SyncJob>>(
    `/drive/connectors/${connectorId}/sync`,
    { resource_id: resourceId }
  );
  return data.data;
}

// ── Slack ───────────────────────────────────────────────

export async function connectSlack(input: {
  organization_id: string;
  bot_token: string;
  display_name?: string;
}) {
  const { data } = await api.post<ApiEnvelope<Connector>>("/slack/connect", input);
  return data.data;
}

export async function listSlackConnectors(organizationId: string) {
  const { data } = await api.get<ApiEnvelope<Connector[]>>("/slack/connectors", {
    params: { organization_id: organizationId },
  });
  return data.data;
}

export async function disconnectSlack(connectorId: string) {
  await api.delete(`/slack/connectors/${connectorId}`);
}

export async function listSlackChannels(connectorId: string) {
  const { data } = await api.get<ApiEnvelope<ConnectorResource[]>>(
    `/slack/connectors/${connectorId}/channels`
  );
  return data.data;
}

export async function refreshSlackChannels(connectorId: string) {
  const { data } = await api.post<ApiEnvelope<ConnectorResource[]>>(
    `/slack/connectors/${connectorId}/refresh-channels`
  );
  return data.data;
}

export async function selectSlackChannels(connectorId: string, resourceIds: string[]) {
  const { data } = await api.put<ApiEnvelope<ConnectorResource[]>>(
    `/slack/connectors/${connectorId}/channels/selection`,
    { resource_ids: resourceIds }
  );
  return data.data;
}

export async function syncSlack(connectorId: string, resourceId?: string) {
  const { data } = await api.post<ApiEnvelope<SyncJob>>(
    `/slack/connectors/${connectorId}/sync`,
    { resource_id: resourceId }
  );
  return data.data;
}

export async function slackChannelSummary(
  connectorId: string,
  resourceId: string,
  limit = 100
) {
  const { data } = await api.post<ApiEnvelope<Record<string, unknown>>>(
    `/slack/connectors/${connectorId}/channel-summary`,
    { resource_id: resourceId, limit }
  );
  return data.data;
}

export async function slackMeetingRecap(
  connectorId: string,
  resourceId: string,
  threadTs?: string
) {
  const { data } = await api.post<ApiEnvelope<Record<string, unknown>>>(
    `/slack/connectors/${connectorId}/meeting-recap`,
    { resource_id: resourceId, thread_ts: threadTs }
  );
  return data.data;
}

export async function slackSearch(connectorId: string, query: string) {
  const { data } = await api.post<ApiEnvelope<Record<string, unknown>>>(
    `/slack/connectors/${connectorId}/search`,
    { query }
  );
  return data.data;
}

// ── Jira ────────────────────────────────────────────────

export async function connectJira(input: {
  organization_id: string;
  base_url: string;
  email: string;
  api_token: string;
  display_name?: string;
}) {
  const { data } = await api.post<ApiEnvelope<Connector>>("/jira/connect", input);
  return data.data;
}

export async function listJiraConnectors(organizationId: string) {
  const { data } = await api.get<ApiEnvelope<Connector[]>>("/jira/connectors", {
    params: { organization_id: organizationId },
  });
  return data.data;
}

export async function disconnectJira(connectorId: string) {
  await api.delete(`/jira/connectors/${connectorId}`);
}

export async function listJiraProjects(connectorId: string) {
  const { data } = await api.get<ApiEnvelope<ConnectorResource[]>>(
    `/jira/connectors/${connectorId}/projects`
  );
  return data.data;
}

export async function refreshJiraProjects(connectorId: string) {
  const { data } = await api.post<ApiEnvelope<ConnectorResource[]>>(
    `/jira/connectors/${connectorId}/refresh-projects`
  );
  return data.data;
}

export async function selectJiraProjects(connectorId: string, resourceIds: string[]) {
  const { data } = await api.put<ApiEnvelope<ConnectorResource[]>>(
    `/jira/connectors/${connectorId}/projects/selection`,
    { resource_ids: resourceIds }
  );
  return data.data;
}

export async function syncJira(connectorId: string, resourceId?: string) {
  const { data } = await api.post<ApiEnvelope<SyncJob>>(
    `/jira/connectors/${connectorId}/sync`,
    { resource_id: resourceId }
  );
  return data.data;
}

export async function jiraExplainStory(connectorId: string, issueKey: string) {
  const { data } = await api.post<ApiEnvelope<Record<string, unknown>>>(
    `/jira/connectors/${connectorId}/explain-story`,
    { issue_key: issueKey }
  );
  return data.data;
}

export async function jiraIssueSearch(connectorId: string, jql: string) {
  const { data } = await api.post<ApiEnvelope<Record<string, unknown>>>(
    `/jira/connectors/${connectorId}/issue-search`,
    { jql, max_results: 20 }
  );
  return data.data;
}

export async function jiraSprintSummary(
  connectorId: string,
  projectKey: string,
  boardId?: number
) {
  const { data } = await api.post<ApiEnvelope<Record<string, unknown>>>(
    `/jira/connectors/${connectorId}/sprint-summary`,
    { project_key: projectKey, board_id: boardId }
  );
  return data.data;
}

export async function jiraSearch(connectorId: string, query: string) {
  const { data } = await api.post<ApiEnvelope<Record<string, unknown>>>(
    `/jira/connectors/${connectorId}/search`,
    { query }
  );
  return data.data;
}
