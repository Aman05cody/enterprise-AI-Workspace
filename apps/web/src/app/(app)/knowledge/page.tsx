"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { listOrganizations } from "@/features/auth/api";
import {
  createKnowledgeBase,
  listKnowledgeBases,
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
import { MessageSquare } from "lucide-react";

export default function KnowledgePage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [orgId, setOrgId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!localStorage.getItem("eaw_access_token")) {
      router.replace("/login");
      return;
    }
    const stored = localStorage.getItem("eaw_org_id");
    if (stored) setOrgId(stored);
  }, [router]);

  const orgs = useQuery({
    queryKey: ["organizations"],
    queryFn: listOrganizations,
  });

  useEffect(() => {
    if (!orgId && orgs.data?.length) {
      setOrgId(orgs.data[0].id);
      localStorage.setItem("eaw_org_id", orgs.data[0].id);
    }
  }, [orgs.data, orgId]);

  const kbs = useQuery({
    queryKey: ["knowledge-bases", orgId],
    queryFn: () => listKnowledgeBases(orgId!),
    enabled: !!orgId,
  });

  const createKb = useMutation({
    mutationFn: () =>
      createKnowledgeBase({
        organization_id: orgId!,
        name,
        description: description || undefined,
      }),
    onSuccess: () => {
      setName("");
      setDescription("");
      qc.invalidateQueries({ queryKey: ["knowledge-bases", orgId] });
    },
    onError: (err: unknown) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((err as any)?.response?.data?.error?.message || "Failed");
    },
  });

  return (
    <PageContainer>
      <PageHeader
        title="Knowledge bases"
        description="Organize documents for grounded RAG chat with citations."
        actions={
          orgs.data && orgs.data.length > 0 ? (
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
                  {o.name}
                </option>
              ))}
            </select>
          ) : undefined
        }
      />

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Collections</CardTitle>
            <CardDescription>
              Each knowledge base is isolated and chat-ready once indexed.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {kbs.isLoading && (
              <div className="h-16 animate-pulse rounded-xl bg-white/5 shimmer" />
            )}
            {kbs.data?.length === 0 && (
              <div className="rounded-xl border border-dashed border-white/10 px-4 py-8 text-center text-sm text-muted-foreground">
                No knowledge bases yet. Create one on the right.
              </div>
            )}
            {kbs.data?.map((kb) => (
              <div
                key={kb.id}
                className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3.5 transition hover:border-indigo-500/25"
              >
                <div className="flex items-center justify-between gap-3">
                  <Link
                    href={`/knowledge/${kb.id}`}
                    className="min-w-0 flex-1 hover:text-indigo-300"
                  >
                    <p className="font-medium">{kb.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {kb.description || "No description"} ·{" "}
                      {kb.stats?.document_count ?? 0} docs
                    </p>
                  </Link>
                  <Link href={`/chat/${kb.id}`}>
                    <Button size="sm" variant="soft">
                      <MessageSquare className="h-3.5 w-3.5" />
                      Chat
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Create knowledge base</CardTitle>
            <CardDescription>Requires Manager+ role</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="HR Policies"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="desc">Description</Label>
              <Input
                id="desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional"
              />
            </div>
            {error && (
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
                {error}
              </div>
            )}
            <Button
              className="w-full"
              disabled={!orgId || !name.trim() || createKb.isPending}
              onClick={() => {
                setError(null);
                createKb.mutate();
              }}
            >
              {createKb.isPending ? "Creating…" : "Create knowledge base"}
            </Button>
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  );
}
