"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  createConversation,
  listConversations,
  listMessages,
  streamMessage,
  type ChatMessage,
  type Citation,
  type Conversation,
} from "@/features/chat/api";
import { getKnowledgeBase } from "@/features/knowledge/api";
import { Button } from "@/shared/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { PageContainer, PageHeader } from "@/shared/ui/app-shell";

type StreamCitation = {
  rank: number;
  title?: string;
  excerpt?: string;
  score?: number;
  document_id?: string;
  chunk_id?: string;
};

export default function ChatPage() {
  const { kbId } = useParams<{ kbId: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState("");
  const [streamCites, setStreamCites] = useState<StreamCitation[]>([]);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!localStorage.getItem("eaw_access_token")) router.replace("/login");
  }, [router]);

  const kb = useQuery({
    queryKey: ["knowledge-base", kbId],
    queryFn: () => getKnowledgeBase(kbId),
  });

  const conversations = useQuery({
    queryKey: ["conversations", kbId],
    queryFn: () => listConversations(kbId),
  });

  useEffect(() => {
    if (!activeId && conversations.data?.length) {
      setActiveId(conversations.data[0].id);
    }
  }, [conversations.data, activeId]);

  const messages = useQuery({
    queryKey: ["messages", activeId],
    queryFn: () => listMessages(activeId!),
    enabled: !!activeId,
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.data, streaming]);

  const createConv = useMutation({
    mutationFn: () => createConversation(kbId),
    onSuccess: (c: Conversation) => {
      qc.invalidateQueries({ queryKey: ["conversations", kbId] });
      setActiveId(c.id);
    },
  });

  const send = async () => {
    if (!input.trim() || busy) return;
    let convId = activeId;
    if (!convId) {
      const c = await createConversation(kbId);
      convId = c.id;
      setActiveId(c.id);
      await qc.invalidateQueries({ queryKey: ["conversations", kbId] });
    }
    const question = input.trim();
    setInput("");
    setBusy(true);
    setError(null);
    setStreaming("");
    setStreamCites([]);
    setConfidence(null);
    setSuggestions([]);

    // optimistic user bubble via refetch after stream; show streaming assistant
    try {
      await streamMessage(convId, question, {
        onToken: (d) => setStreaming((s) => s + d),
        onCitation: (c) =>
          setStreamCites((prev) => [
            ...prev,
            {
              rank: Number(c.rank || prev.length + 1),
              title: c.title as string | undefined,
              excerpt: c.excerpt as string | undefined,
              score: c.score as number | undefined,
              document_id: c.document_id as string | undefined,
              chunk_id: c.chunk_id as string | undefined,
            },
          ]),
        onConfidence: (c) => setConfidence(c),
        onSuggestions: (s) => setSuggestions(s),
        onError: (m) => setError(m),
        onDone: async () => {
          setStreaming("");
          await qc.invalidateQueries({ queryKey: ["messages", convId] });
          await qc.invalidateQueries({ queryKey: ["conversations", kbId] });
        },
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Chat failed");
    } finally {
      setBusy(false);
    }
  };

  const displayMessages: ChatMessage[] = messages.data || [];

  const sidebar = useMemo(
    () => conversations.data || [],
    [conversations.data]
  );

  return (
    <PageContainer wide className="flex min-h-[calc(100vh-3.5rem)] flex-col lg:min-h-screen">
      <PageHeader
        title={kb.data?.name || "Knowledge chat"}
        breadcrumb={
          <>
            <Link href="/knowledge" className="hover:text-indigo-300">
              Knowledge
            </Link>
            <span className="mx-1.5 text-white/20">/</span>
            <span>Chat</span>
          </>
        }
        description="Grounded answers with citations · refuses when context is weak"
        actions={
          <>
            <Link href={`/knowledge/${kbId}`}>
              <Button variant="outline" size="sm">
                Documents
              </Button>
            </Link>
            <Button size="sm" onClick={() => createConv.mutate()} disabled={busy}>
              New chat
            </Button>
          </>
        }
      />

      <div className="grid min-h-[70vh] flex-1 gap-4 lg:grid-cols-12">
        <Card className="lg:col-span-3">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Conversations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {sidebar.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => setActiveId(c.id)}
                className={`w-full rounded-xl border px-3 py-2.5 text-left text-sm transition ${
                  activeId === c.id
                    ? "border-indigo-500/40 bg-indigo-500/15 text-white"
                    : "border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.05]"
                }`}
              >
                <p className="truncate font-medium">{c.title || "Untitled"}</p>
              </button>
            ))}
            {sidebar.length === 0 && (
              <p className="text-xs text-muted-foreground">
                Start a conversation below.
              </p>
            )}
          </CardContent>
        </Card>

        <Card className="flex flex-col lg:col-span-6">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Enterprise chat</CardTitle>
            <CardDescription>Streaming · SSE · citation-backed</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col gap-3">
            <div className="flex-1 space-y-3 overflow-y-auto rounded-2xl border border-white/[0.06] bg-black/20 p-4">
              {displayMessages.map((m) => (
                <div
                  key={m.id}
                  className={`max-w-[90%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                    m.role === "user"
                      ? "ml-auto bg-gradient-to-br from-indigo-500 to-indigo-600 text-white shadow-lg shadow-indigo-500/20"
                      : "bg-white/[0.05] ring-1 ring-white/10"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{m.content}</p>
                  {m.role === "assistant" && m.confidence != null && (
                    <p className="mt-1.5 text-[10px] text-muted-foreground">
                      confidence {(m.confidence * 100).toFixed(0)}%
                      {m.latency_ms != null ? ` · ${m.latency_ms}ms` : ""}
                    </p>
                  )}
                </div>
              ))}
              {streaming && (
                <div className="max-w-[90%] rounded-2xl bg-white/[0.05] px-4 py-2.5 text-sm ring-1 ring-white/10">
                  <p className="whitespace-pre-wrap">{streaming}</p>
                  <span className="inline-block animate-pulse text-xs text-indigo-300">
                    ▍
                  </span>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {error && (
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
                {error}
              </div>
            )}

            {suggestions.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    type="button"
                    className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-xs text-muted-foreground transition hover:border-indigo-500/30 hover:text-foreground"
                    onClick={() => setInput(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}

            <div className="flex gap-2">
              <Input
                placeholder="Ask a question about your knowledge base…"
                value={input}
                disabled={busy}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
              />
              <Button onClick={send} disabled={busy || !input.trim()}>
                {busy ? "…" : "Send"}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Citations</CardTitle>
            <CardDescription>
              {confidence != null
                ? `Confidence ${(confidence * 100).toFixed(0)}%`
                : "Sources for the latest answer"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {streamCites.length === 0 &&
              !(displayMessages.at(-1)?.citations?.length) && (
                <p className="text-xs text-muted-foreground">
                  Citations appear when retrieval finds relevant chunks.
                </p>
              )}
            {streamCites.map((c) => (
              <div
                key={`${c.rank}-${c.chunk_id}`}
                className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-3 text-xs"
              >
                <p className="font-medium text-indigo-200">
                  [{c.rank}] {c.title || "Source"}
                </p>
                <p className="mt-1.5 leading-relaxed text-muted-foreground">
                  {c.excerpt}
                </p>
              </div>
            ))}
            {!streaming &&
              (displayMessages.at(-1)?.role === "assistant"
                ? displayMessages.at(-1)?.citations
                : []
              )?.map((c: Citation) => (
                <div
                  key={c.id}
                  className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-3 text-xs"
                >
                  <p className="font-medium text-indigo-200">[{c.rank}] Source</p>
                  <p className="mt-1.5 leading-relaxed text-muted-foreground">
                    {c.excerpt}
                  </p>
                </div>
              ))}
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  );
}
