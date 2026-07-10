import { api, type ApiEnvelope } from "@/shared/api/client";

export type KnowledgeBase = {
  id: string;
  organization_id: string;
  department_id?: string | null;
  name: string;
  description?: string | null;
  settings: Record<string, unknown>;
  stats?: {
    document_count?: number;
    pending?: number;
    ready?: number;
    failed?: number;
    processing?: number;
    by_status?: Record<string, number>;
  } | null;
};

export type Document = {
  id: string;
  organization_id: string;
  knowledge_base_id: string;
  title: string;
  original_filename: string;
  content_type: string;
  file_size_bytes: number;
  checksum_sha256: string;
  status: string;
  source_type: string;
  current_version: number;
  chunk_count: number;
  error_message?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type DocumentPreview = {
  document_id: string;
  title: string;
  content_type: string;
  preview_text?: string | null;
  has_preview: boolean;
  status: string;
  current_version: number;
};

export async function listKnowledgeBases(organizationId: string) {
  const { data } = await api.get<ApiEnvelope<KnowledgeBase[]>>("/knowledge-bases", {
    params: { organization_id: organizationId },
  });
  return data.data;
}

export async function createKnowledgeBase(input: {
  organization_id: string;
  name: string;
  description?: string;
}) {
  const { data } = await api.post<ApiEnvelope<KnowledgeBase>>(
    "/knowledge-bases",
    input
  );
  return data.data;
}

export async function getKnowledgeBase(kbId: string) {
  const { data } = await api.get<ApiEnvelope<KnowledgeBase>>(
    `/knowledge-bases/${kbId}`
  );
  return data.data;
}

export async function listDocuments(
  kbId: string,
  params?: { q?: string; status?: string }
) {
  const { data } = await api.get<ApiEnvelope<Document[]>>(
    `/knowledge-bases/${kbId}/documents`,
    { params }
  );
  return { items: data.data, total: data.meta?.total ?? data.data.length };
}

export async function uploadDocument(
  kbId: string,
  file: File,
  title?: string
) {
  const form = new FormData();
  form.append("file", file);
  if (title) form.append("title", title);
  const { data } = await api.post<ApiEnvelope<Document>>(
    `/knowledge-bases/${kbId}/documents`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data.data;
}

export async function getDocumentPreview(documentId: string) {
  const { data } = await api.get<ApiEnvelope<DocumentPreview>>(
    `/documents/${documentId}/preview`
  );
  return data.data;
}

export async function deleteDocument(documentId: string) {
  await api.delete(`/documents/${documentId}`);
}

export async function searchDocuments(
  orgId: string,
  query: string,
  knowledgeBaseId?: string
) {
  const { data } = await api.post<
    ApiEnvelope<{ document: Document; snippet?: string }[]>
  >(`/organizations/${orgId}/documents/search`, {
    query,
    knowledge_base_id: knowledgeBaseId,
    limit: 20,
  });
  return data.data;
}

export function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export type IngestionJob = {
  id: string;
  document_id: string;
  status: string;
  stage?: string | null;
  progress_pct: number;
  error_message?: string | null;
  metrics?: Record<string, unknown>;
  created_at: string;
};

export type SemanticHit = {
  chunk_id: string;
  score: number;
  document_id?: string | null;
  title?: string | null;
  content_preview?: string | null;
  chunk_index?: number | null;
};

export async function listDocumentJobs(documentId: string) {
  const { data } = await api.get<ApiEnvelope<IngestionJob[]>>(
    `/documents/${documentId}/jobs`
  );
  return data.data;
}

export async function reprocessDocument(documentId: string) {
  const { data } = await api.post<ApiEnvelope<IngestionJob>>(
    `/documents/${documentId}/reprocess`
  );
  return data.data;
}

export async function semanticSearch(kbId: string, query: string, topK = 8) {
  const { data } = await api.post<ApiEnvelope<SemanticHit[]>>(
    `/knowledge-bases/${kbId}/semantic-search`,
    { query, top_k: topK }
  );
  return data.data;
}
