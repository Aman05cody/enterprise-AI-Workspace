import { api, type ApiEnvelope } from "@/shared/api/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Conversation = {
  id: string;
  knowledge_base_id: string;
  title?: string | null;
  memory_summary?: string | null;
  model?: string | null;
  updated_at?: string;
};

export type Citation = {
  id: string;
  document_id?: string | null;
  chunk_id?: string | null;
  score?: number | null;
  excerpt: string;
  rank: number;
};

export type ChatMessage = {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  confidence?: number | null;
  latency_ms?: number | null;
  model?: string | null;
  created_at: string;
  citations: Citation[];
};

export async function listConversations(kbId: string) {
  const { data } = await api.get<ApiEnvelope<Conversation[]>>(
    `/knowledge-bases/${kbId}/conversations`
  );
  return data.data;
}

export async function createConversation(kbId: string, title?: string) {
  const { data } = await api.post<ApiEnvelope<Conversation>>("/conversations", {
    knowledge_base_id: kbId,
    title,
  });
  return data.data;
}

export async function listMessages(conversationId: string) {
  const { data } = await api.get<ApiEnvelope<ChatMessage[]>>(
    `/conversations/${conversationId}/messages`
  );
  return data.data;
}

export async function sendMessage(conversationId: string, content: string) {
  const { data } = await api.post<
    ApiEnvelope<{
      message: ChatMessage;
      confidence?: number;
      suggestions: string[];
      insufficient_context: boolean;
    }>
  >(`/conversations/${conversationId}/messages`, { content });
  return data.data;
}

export type StreamHandlers = {
  onMeta?: (data: Record<string, unknown>) => void;
  onToken?: (delta: string) => void;
  onCitation?: (data: Record<string, unknown>) => void;
  onConfidence?: (confidence: number) => void;
  onSuggestions?: (suggestions: string[]) => void;
  onError?: (message: string) => void;
  onDone?: (data: Record<string, unknown>) => void;
};

export async function streamMessage(
  conversationId: string,
  content: string,
  handlers: StreamHandlers
) {
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("eaw_access_token")
      : null;

  const res = await fetch(
    `${API_URL}/api/v1/conversations/${conversationId}/messages:stream`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ content }),
    }
  );

  if (!res.ok || !res.body) {
    const text = await res.text();
    throw new Error(text || `Stream failed (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const lines = part.split("\n");
      let event = "message";
      let dataStr = "";
      for (const line of lines) {
        if (line.startsWith("event: ")) event = line.slice(7).trim();
        if (line.startsWith("data: ")) dataStr += line.slice(6);
      }
      if (!dataStr) continue;
      let data: Record<string, unknown> = {};
      try {
        data = JSON.parse(dataStr);
      } catch {
        continue;
      }
      if (event === "meta") handlers.onMeta?.(data);
      if (event === "token") handlers.onToken?.(String(data.delta || ""));
      if (event === "citation") handlers.onCitation?.(data);
      if (event === "confidence")
        handlers.onConfidence?.(Number(data.confidence || 0));
      if (event === "suggestions")
        handlers.onSuggestions?.((data.suggestions as string[]) || []);
      if (event === "error") handlers.onError?.(String(data.message || "error"));
      if (event === "done") handlers.onDone?.(data);
    }
  }
}
