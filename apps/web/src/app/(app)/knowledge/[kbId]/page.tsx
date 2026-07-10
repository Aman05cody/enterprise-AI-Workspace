"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  deleteDocument,
  formatBytes,
  getDocumentPreview,
  getKnowledgeBase,
  listDocuments,
  reprocessDocument,
  semanticSearch,
  uploadDocument,
  type Document,
  type SemanticHit,
} from "@/features/knowledge/api";
import { Button } from "@/shared/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { PageContainer, PageHeader } from "@/shared/ui/app-shell";

const ALLOWED =
  ".pdf,.docx,.txt,.md,.csv,.pptx,application/pdf,text/plain,text/markdown,text/csv";

export default function KnowledgeBaseDetailPage() {
  const params = useParams<{ kbId: string }>();
  const kbId = params.kbId;
  const router = useRouter();
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [previewTitle, setPreviewTitle] = useState("");
  const [semanticQ, setSemanticQ] = useState("");
  const [hits, setHits] = useState<SemanticHit[] | null>(null);

  useEffect(() => {
    if (!localStorage.getItem("eaw_access_token")) {
      router.replace("/login");
    }
  }, [router]);

  const kb = useQuery({
    queryKey: ["knowledge-base", kbId],
    queryFn: () => getKnowledgeBase(kbId),
    refetchInterval: (query) => {
      const stats = query.state.data?.stats;
      const pending =
        (stats?.pending ?? 0) + (stats?.processing ?? 0);
      return pending > 0 ? 3000 : false;
    },
  });

  const docs = useQuery({
    queryKey: ["documents", kbId, q],
    queryFn: () => listDocuments(kbId, q ? { q } : undefined),
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? [];
      const busy = items.some(
        (d) => d.status === "pending" || d.status === "processing"
      );
      return busy ? 3000 : false;
    },
  });

  const upload = useMutation({
    mutationFn: (file: File) => uploadDocument(kbId, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents", kbId] });
      qc.invalidateQueries({ queryKey: ["knowledge-base", kbId] });
    },
    onError: (err: unknown) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((err as any)?.response?.data?.error?.message || "Upload failed");
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents", kbId] });
      qc.invalidateQueries({ queryKey: ["knowledge-base", kbId] });
    },
  });

  const reprocess = useMutation({
    mutationFn: (id: string) => reprocessDocument(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents", kbId] });
      qc.invalidateQueries({ queryKey: ["knowledge-base", kbId] });
    },
    onError: (err: unknown) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((err as any)?.response?.data?.error?.message || "Reprocess failed");
    },
  });

  const statusColor = (status: string) => {
    switch (status) {
      case "ready":
        return "text-emerald-400";
      case "pending":
        return "text-amber-400";
      case "processing":
        return "text-sky-400";
      case "failed":
        return "text-destructive";
      default:
        return "text-muted-foreground";
    }
  };

  const openPreview = async (doc: Document) => {
    try {
      const p = await getDocumentPreview(doc.id);
      setPreviewTitle(p.title);
      setPreview(
        p.preview_text || "No text preview available for this file type."
      );
    } catch {
      setPreview("Failed to load preview");
    }
  };

  const runSemantic = async () => {
    if (!semanticQ.trim()) return;
    try {
      const results = await semanticSearch(kbId, semanticQ.trim());
      setHits(results);
    } catch (err: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((err as any)?.response?.data?.error?.message || "Search failed");
    }
  };

  return (
    <PageContainer>
      <PageHeader
        title={kb.data?.name || "Loading…"}
        breadcrumb={
          <>
            <Link href="/knowledge" className="hover:text-indigo-300">
              Knowledge
            </Link>
            <span className="mx-1.5 text-white/20">/</span>
            <span>{kb.data?.name || "…"}</span>
          </>
        }
        description={`${kb.data?.stats?.document_count ?? 0} documents · ${kb.data?.stats?.ready ?? 0} ready · ${kb.data?.stats?.pending ?? 0} pending · ${kb.data?.stats?.processing ?? 0} processing`}
        actions={
          <Link href={`/chat/${kbId}`}>
            <Button>Open chat</Button>
          </Link>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Upload & index</CardTitle>
            <CardDescription>
              Auto-ingest: extract → chunk → embed → vector index
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="file">File</Label>
              <Input
                id="file"
                type="file"
                accept={ALLOWED}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (!f) return;
                  setError(null);
                  upload.mutate(f);
                  e.target.value = "";
                }}
              />
            </div>
            {upload.isPending && (
              <p className="text-sm text-muted-foreground">
                Uploading & indexing…
              </p>
            )}
            {error && <p className="text-sm text-destructive">{error}</p>}
            <div className="space-y-2">
              <Label htmlFor="search">Filter list</Label>
              <Input
                id="search"
                placeholder="Search title or content…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </div>
            <div className="space-y-2 border-t border-border pt-4">
              <Label htmlFor="semantic">Semantic search</Label>
              <Input
                id="semantic"
                placeholder="Ask about indexed knowledge…"
                value={semanticQ}
                onChange={(e) => setSemanticQ(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && runSemantic()}
              />
              <Button
                className="w-full"
                variant="secondary"
                onClick={runSemantic}
                disabled={!semanticQ.trim()}
              >
                Search vectors
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Documents</CardTitle>
            <CardDescription>
              Status updates automatically while processing
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {docs.isLoading && (
              <p className="text-sm text-muted-foreground">Loading…</p>
            )}
            {docs.data?.items.length === 0 && (
              <p className="text-sm text-muted-foreground">No documents yet.</p>
            )}
            {docs.data?.items.map((doc) => (
              <div
                key={doc.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-secondary/30 px-4 py-3"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{doc.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {doc.original_filename} · {formatBytes(doc.file_size_bytes)} ·
                    v{doc.current_version} · chunks {doc.chunk_count} ·{" "}
                    <span className={statusColor(doc.status)}>{doc.status}</span>
                  </p>
                  {doc.error_message && (
                    <p className="mt-1 text-xs text-destructive">
                      {doc.error_message}
                    </p>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => openPreview(doc)}
                  >
                    Preview
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={reprocess.isPending}
                    onClick={() => reprocess.mutate(doc.id)}
                  >
                    Reprocess
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => remove.mutate(doc.id)}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {hits && (
        <Card className="mt-6">
          <CardHeader className="flex flex-row items-start justify-between">
            <div>
              <CardTitle>Semantic results</CardTitle>
              <CardDescription>
                Dense retrieval with tenant + KB filters
              </CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setHits(null)}>
              Close
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {hits.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No hits — index documents to `ready` first.
              </p>
            )}
            {hits.map((h) => (
              <div
                key={h.chunk_id}
                className="rounded-lg border border-border bg-background/50 p-3"
              >
                <div className="mb-1 flex justify-between text-xs text-muted-foreground">
                  <span>{h.title || "Untitled"} · chunk {h.chunk_index ?? "—"}</span>
                  <span>score {h.score.toFixed(3)}</span>
                </div>
                <p className="text-sm text-muted-foreground">
                  {h.content_preview}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {preview !== null && (
        <Card className="mt-6">
          <CardHeader className="flex flex-row items-start justify-between">
            <div>
              <CardTitle>Preview — {previewTitle}</CardTitle>
              <CardDescription>Extracted text (best effort)</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setPreview(null)}>
              Close
            </Button>
          </CardHeader>
          <CardContent>
            <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-md bg-background/60 p-4 text-sm text-muted-foreground">
              {preview}
            </pre>
          </CardContent>
        </Card>
      )}
    </PageContainer>
  );
}
