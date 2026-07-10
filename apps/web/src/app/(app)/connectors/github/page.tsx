"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { listOrganizations } from "@/features/auth/api";
import {
  chatWithRepo,
  connectGitHub,
  disconnectGitHub,
  explainArchitecture,
  explainFile,
  generateDocs,
  generateTests,
  listGitHubConnectors,
  listRepos,
  refreshRepos,
  reviewPull,
  selectRepos,
  syncGitHub,
  type RepoResource,
} from "@/features/github/api";
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

export default function GitHubConnectorPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [orgId, setOrgId] = useState<string | null>(null);
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [output, setOutput] = useState<string>("");
  const [owner, setOwner] = useState("");
  const [repo, setRepo] = useState("");
  const [path, setPath] = useState("README.md");
  const [prNumber, setPrNumber] = useState("1");
  const [question, setQuestion] = useState("How is the project structured?");

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
    queryKey: ["github-connectors", orgId],
    queryFn: () => listGitHubConnectors(orgId!),
    enabled: !!orgId,
  });

  const connector = connectors.data?.[0] ?? null;

  const repos = useQuery({
    queryKey: ["github-repos", connector?.id],
    queryFn: () => listRepos(connector!.id),
    enabled: !!connector,
  });

  useEffect(() => {
    if (repos.data) {
      setSelected(new Set(repos.data.filter((r) => r.sync_enabled).map((r) => r.id)));
    }
  }, [repos.data]);

  const connect = useMutation({
    mutationFn: () =>
      connectGitHub({
        organization_id: orgId!,
        personal_access_token: token,
      }),
    onSuccess: () => {
      setToken("");
      qc.invalidateQueries({ queryKey: ["github-connectors", orgId] });
    },
    onError: (err: unknown) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((err as any)?.response?.data?.error?.message || "Connect failed");
    },
  });

  const saveSelection = useMutation({
    mutationFn: () => selectRepos(connector!.id, Array.from(selected)),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["github-repos", connector?.id] }),
  });

  const sync = useMutation({
    mutationFn: () => syncGitHub(connector!.id),
    onSuccess: (job) => {
      setOutput(
        `Sync ${job.status}\n${JSON.stringify(job.stats || {}, null, 2)}\n${job.error_message || ""}`
      );
      qc.invalidateQueries({ queryKey: ["github-repos", connector?.id] });
      qc.invalidateQueries({ queryKey: ["knowledge-bases", orgId] });
    },
    onError: (err: unknown) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((err as any)?.response?.data?.error?.message || "Sync failed");
    },
  });

  const enabledRepos: RepoResource[] = useMemo(
    () => (repos.data || []).filter((r) => r.sync_enabled),
    [repos.data]
  );

  const runTool = async (kind: string) => {
    if (!connector) return;
    setError(null);
    try {
      if (kind === "review") {
        const data = await reviewPull({
          connector_id: connector.id,
          owner,
          repo,
          pull_number: Number(prNumber),
        });
        setOutput(String(data.review || JSON.stringify(data, null, 2)));
      } else if (kind === "explain") {
        const data = await explainFile({
          connector_id: connector.id,
          owner,
          repo,
          path,
        });
        setOutput(String(data.explanation || JSON.stringify(data, null, 2)));
      } else if (kind === "docs") {
        const data = await generateDocs({
          connector_id: connector.id,
          owner,
          repo,
          path,
        });
        setOutput(String(data.documentation || JSON.stringify(data, null, 2)));
      } else if (kind === "tests") {
        const data = await generateTests({
          connector_id: connector.id,
          owner,
          repo,
          path,
        });
        setOutput(String(data.tests || JSON.stringify(data, null, 2)));
      }
    } catch (err: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((err as any)?.response?.data?.error?.message || "Request failed");
    }
  };

  return (
    <PageContainer wide>
      <header className="mb-8 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-muted-foreground">
            <Link href="/dashboard" className="hover:text-primary">
              Dashboard
            </Link>{" "}
            / Connectors / GitHub
          </p>
          <h1 className="text-2xl font-semibold">GitHub Intelligence</h1>
          <p className="text-sm text-muted-foreground">
            Connect · index repos · chat · PR review · docs/tests generation
          </p>
        </div>
        {orgs.data && (
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
        )}
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Connection</CardTitle>
            <CardDescription>
              Use a classic PAT with <code>repo</code> scope (admin only)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {connector ? (
              <div className="space-y-3">
                <p className="text-sm">
                  <span className="font-medium">{connector.display_name}</span>{" "}
                  <span className="text-muted-foreground">· {connector.status}</span>
                </p>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => refreshRepos(connector.id).then(() =>
                      qc.invalidateQueries({ queryKey: ["github-repos", connector.id] })
                    )}
                  >
                    Refresh repos
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() =>
                      disconnectGitHub(connector.id).then(() =>
                        qc.invalidateQueries({ queryKey: ["github-connectors", orgId] })
                      )
                    }
                  >
                    Disconnect
                  </Button>
                </div>
              </div>
            ) : (
              <>
                <div className="space-y-2">
                  <Label htmlFor="pat">Personal access token</Label>
                  <Input
                    id="pat"
                    type="password"
                    placeholder="ghp_…"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                  />
                </div>
                <Button
                  disabled={!orgId || token.length < 8 || connect.isPending}
                  onClick={() => {
                    setError(null);
                    connect.mutate();
                  }}
                >
                  {connect.isPending ? "Connecting…" : "Connect GitHub"}
                </Button>
              </>
            )}
            {error && <p className="text-sm text-destructive">{error}</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Repositories</CardTitle>
            <CardDescription>Select repos to index into knowledge bases</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {!connector && (
              <p className="text-sm text-muted-foreground">Connect GitHub first.</p>
            )}
            <div className="max-h-64 space-y-2 overflow-y-auto">
              {(repos.data || []).map((r) => (
                <label
                  key={r.id}
                  className="flex cursor-pointer items-start gap-2 rounded-md border border-border px-3 py-2 text-sm"
                >
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={selected.has(r.id)}
                    onChange={(e) => {
                      const next = new Set(selected);
                      if (e.target.checked) next.add(r.id);
                      else next.delete(r.id);
                      setSelected(next);
                    }}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="font-medium">{r.name}</span>
                    {r.knowledge_base_id && (
                      <span className="ml-2 text-xs text-emerald-400">indexed</span>
                    )}
                    <span className="block truncate text-xs text-muted-foreground">
                      {String(r.metadata?.language || "—")} ·{" "}
                      {r.metadata?.private ? "private" : "public"}
                    </span>
                  </span>
                </label>
              ))}
            </div>
            {connector && (
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={saveSelection.isPending}
                  onClick={() => saveSelection.mutate()}
                >
                  Save selection
                </Button>
                <Button
                  size="sm"
                  disabled={sync.isPending || selected.size === 0}
                  onClick={() => {
                    setError(null);
                    saveSelection.mutate(undefined, {
                      onSuccess: () => sync.mutate(),
                    });
                  }}
                >
                  {sync.isPending ? "Syncing…" : "Sync & index"}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Intelligence tools</CardTitle>
            <CardDescription>
              Live GitHub API + LLM (or grounded repo chat after sync)
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label>Owner</Label>
                  <Input value={owner} onChange={(e) => setOwner(e.target.value)} placeholder="octocat" />
                </div>
                <div>
                  <Label>Repo</Label>
                  <Input value={repo} onChange={(e) => setRepo(e.target.value)} placeholder="hello-world" />
                </div>
              </div>
              <div>
                <Label>Path</Label>
                <Input value={path} onChange={(e) => setPath(e.target.value)} />
              </div>
              <div>
                <Label>PR number</Label>
                <Input value={prNumber} onChange={(e) => setPrNumber(e.target.value)} />
              </div>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={() => runTool("explain")}>
                  Explain file
                </Button>
                <Button size="sm" variant="outline" onClick={() => runTool("docs")}>
                  Generate docs
                </Button>
                <Button size="sm" variant="outline" onClick={() => runTool("tests")}>
                  Generate tests
                </Button>
                <Button size="sm" variant="outline" onClick={() => runTool("review")}>
                  Review PR
                </Button>
              </div>

              <div className="border-t border-border pt-3">
                <Label>Repo chat / architecture (synced repos)</Label>
                <div className="mt-2 space-y-2">
                  {enabledRepos.map((r) => (
                    <div key={r.id} className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={async () => {
                          try {
                            const data = await explainArchitecture(r.id);
                            setOutput(String(data.answer || JSON.stringify(data, null, 2)));
                          } catch (err: unknown) {
                            // eslint-disable-next-line @typescript-eslint/no-explicit-any
                            setError((err as any)?.response?.data?.error?.message || "Failed");
                          }
                        }}
                      >
                        Architecture · {r.name}
                      </Button>
                      {r.knowledge_base_id && (
                        <Link href={`/chat/${r.knowledge_base_id}`}>
                          <Button size="sm">Open chat UI</Button>
                        </Link>
                      )}
                    </div>
                  ))}
                </div>
                <div className="mt-3 flex gap-2">
                  <Input
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Ask about a synced repo…"
                  />
                  <Button
                    size="sm"
                    disabled={!enabledRepos[0]}
                    onClick={async () => {
                      try {
                        const data = await chatWithRepo(enabledRepos[0].id, question);
                        setOutput(String(data.answer || JSON.stringify(data, null, 2)));
                      } catch (err: unknown) {
                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                        setError((err as any)?.response?.data?.error?.message || "Failed");
                      }
                    }}
                  >
                    Ask
                  </Button>
                </div>
              </div>
            </div>
            <div>
              <Label>Output</Label>
              <pre className="mt-2 max-h-[420px] overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-background/50 p-3 text-xs text-muted-foreground">
                {output || "Results appear here."}
              </pre>
            </div>
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  );
}
