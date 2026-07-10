"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { listOrganizations } from "@/features/auth/api";
import {
  connectNotion,
  disconnectNotion,
  listNotionConnectors,
  listNotionPages,
  refreshNotionPages,
  selectNotionPages,
  syncNotion,
} from "@/features/connectors/api";
import { Button } from "@/shared/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/ui/card";
import { PageContainer, PageHeader } from "@/shared/ui/app-shell";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";

export default function NotionConnectorPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [orgId, setOrgId] = useState<string | null>(null);
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [output, setOutput] = useState("");

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

  const connectors = useQuery({
    queryKey: ["notion-connectors", orgId],
    queryFn: () => listNotionConnectors(orgId!),
    enabled: !!orgId,
  });
  const connector = connectors.data?.[0] ?? null;

  const pages = useQuery({
    queryKey: ["notion-pages", connector?.id],
    queryFn: () => listNotionPages(connector!.id),
    enabled: !!connector,
  });

  useEffect(() => {
    if (pages.data) {
      setSelected(new Set(pages.data.filter((p) => p.sync_enabled).map((p) => p.id)));
    }
  }, [pages.data]);

  const connect = useMutation({
    mutationFn: () =>
      connectNotion({ organization_id: orgId!, integration_token: token }),
    onSuccess: () => {
      setToken("");
      qc.invalidateQueries({ queryKey: ["notion-connectors", orgId] });
    },
    onError: (err: unknown) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((err as any)?.response?.data?.error?.message || "Connect failed");
    },
  });

  return (
    <PageContainer>
      <header className="mb-8">
        <p className="text-sm text-muted-foreground">
          <Link href="/dashboard" className="hover:text-primary">
            Dashboard
          </Link>{" "}
          / Connectors / Notion
        </p>
        <h1 className="text-2xl font-semibold">Notion Sync</h1>
        <p className="text-sm text-muted-foreground">
          Connect an internal integration, select pages, index into knowledge
        </p>
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Connection</CardTitle>
            <CardDescription>
              Create a Notion internal integration and share pages with it
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {connector ? (
              <>
                <p className="text-sm">
                  <span className="font-medium">{connector.display_name}</span> ·{" "}
                  {connector.status}
                </p>
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      refreshNotionPages(connector.id).then(() =>
                        qc.invalidateQueries({
                          queryKey: ["notion-pages", connector.id],
                        })
                      )
                    }
                  >
                    Refresh pages
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() =>
                      disconnectNotion(connector.id).then(() =>
                        qc.invalidateQueries({
                          queryKey: ["notion-connectors", orgId],
                        })
                      )
                    }
                  >
                    Disconnect
                  </Button>
                </div>
              </>
            ) : (
              <>
                <div className="space-y-2">
                  <Label htmlFor="token">Integration token</Label>
                  <Input
                    id="token"
                    type="password"
                    placeholder="secret_…"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                  />
                </div>
                <Button
                  disabled={!orgId || token.length < 10 || connect.isPending}
                  onClick={() => {
                    setError(null);
                    connect.mutate();
                  }}
                >
                  {connect.isPending ? "Connecting…" : "Connect Notion"}
                </Button>
              </>
            )}
            {error && <p className="text-sm text-destructive">{error}</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Pages</CardTitle>
            <CardDescription>Select pages to sync into “Notion Workspace” KB</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="max-h-72 space-y-2 overflow-y-auto">
              {(pages.data || []).map((p) => (
                <label
                  key={p.id}
                  className="flex cursor-pointer gap-2 rounded-md border border-border px-3 py-2 text-sm"
                >
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={selected.has(p.id)}
                    onChange={(e) => {
                      const next = new Set(selected);
                      if (e.target.checked) next.add(p.id);
                      else next.delete(p.id);
                      setSelected(next);
                    }}
                  />
                  <span>
                    <span className="font-medium">{p.name}</span>
                    {p.knowledge_base_id && (
                      <span className="ml-2 text-xs text-emerald-400">synced</span>
                    )}
                  </span>
                </label>
              ))}
              {connector && (pages.data || []).length === 0 && (
                <p className="text-xs text-muted-foreground">
                  No pages found. Share pages with the integration, then refresh.
                </p>
              )}
            </div>
            {connector && (
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() =>
                    selectNotionPages(connector.id, Array.from(selected)).then(() =>
                      qc.invalidateQueries({ queryKey: ["notion-pages", connector.id] })
                    )
                  }
                >
                  Save selection
                </Button>
                <Button
                  size="sm"
                  disabled={selected.size === 0}
                  onClick={async () => {
                    setError(null);
                    try {
                      await selectNotionPages(connector.id, Array.from(selected));
                      const job = await syncNotion(connector.id);
                      setOutput(
                        `Sync ${job.status}\n${JSON.stringify(job.stats || {}, null, 2)}`
                      );
                      qc.invalidateQueries({ queryKey: ["notion-pages", connector.id] });
                      qc.invalidateQueries({ queryKey: ["knowledge-bases", orgId] });
                    } catch (err: unknown) {
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      setError((err as any)?.response?.data?.error?.message || "Sync failed");
                    }
                  }}
                >
                  Sync & index
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {output && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Sync result</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="whitespace-pre-wrap text-xs text-muted-foreground">{output}</pre>
            <div className="mt-3">
              <Link href="/knowledge">
                <Button size="sm" variant="outline">
                  Open knowledge bases
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}
    </PageContainer>
  );
}
