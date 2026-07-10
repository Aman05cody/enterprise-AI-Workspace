"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { listOrganizations } from "@/features/auth/api";
import {
  connectJira,
  disconnectJira,
  jiraExplainStory,
  jiraIssueSearch,
  jiraSearch,
  jiraSprintSummary,
  listJiraConnectors,
  listJiraProjects,
  refreshJiraProjects,
  selectJiraProjects,
  syncJira,
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

export default function JiraConnectorPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [orgId, setOrgId] = useState<string | null>(null);
  const [baseUrl, setBaseUrl] = useState("https://your-domain.atlassian.net");
  const [email, setEmail] = useState("");
  const [apiToken, setApiToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [output, setOutput] = useState("");
  const [issueKey, setIssueKey] = useState("PROJ-1");
  const [jql, setJql] = useState("project = PROJ ORDER BY updated DESC");
  const [projectKey, setProjectKey] = useState("PROJ");
  const [query, setQuery] = useState("What are the open blockers?");

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
    queryKey: ["jira-connectors", orgId],
    queryFn: () => listJiraConnectors(orgId!),
    enabled: !!orgId,
  });
  const connector = connectors.data?.[0] ?? null;

  const projects = useQuery({
    queryKey: ["jira-projects", connector?.id],
    queryFn: () => listJiraProjects(connector!.id),
    enabled: !!connector,
  });

  useEffect(() => {
    if (projects.data) {
      setSelected(
        new Set(projects.data.filter((p) => p.sync_enabled).map((p) => p.id))
      );
    }
  }, [projects.data]);

  const connect = useMutation({
    mutationFn: () =>
      connectJira({
        organization_id: orgId!,
        base_url: baseUrl,
        email,
        api_token: apiToken,
      }),
    onSuccess: () => {
      setApiToken("");
      qc.invalidateQueries({ queryKey: ["jira-connectors", orgId] });
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
          / Connectors / Jira
        </p>
        <h1 className="text-2xl font-semibold">Jira AI</h1>
        <p className="text-sm text-muted-foreground">
          Sprint summaries · issue search · story explanation · indexed RAG search
        </p>
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Connection</CardTitle>
            <CardDescription>Atlassian Cloud email + API token</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
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
                      refreshJiraProjects(connector.id).then(() =>
                        qc.invalidateQueries({
                          queryKey: ["jira-projects", connector.id],
                        })
                      )
                    }
                  >
                    Refresh projects
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() =>
                      disconnectJira(connector.id).then(() =>
                        qc.invalidateQueries({
                          queryKey: ["jira-connectors", orgId],
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
                  <Label>Base URL</Label>
                  <Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input value={email} onChange={(e) => setEmail(e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>API token</Label>
                  <Input
                    type="password"
                    value={apiToken}
                    onChange={(e) => setApiToken(e.target.value)}
                  />
                </div>
                <Button
                  disabled={
                    !orgId || !email || apiToken.length < 8 || connect.isPending
                  }
                  onClick={() => {
                    setError(null);
                    connect.mutate();
                  }}
                >
                  {connect.isPending ? "Connecting…" : "Connect Jira"}
                </Button>
              </>
            )}
            {error && <p className="text-sm text-destructive">{error}</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Projects</CardTitle>
            <CardDescription>Select projects to index issues</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="max-h-64 space-y-2 overflow-y-auto">
              {(projects.data || []).map((p) => (
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
                  <span className="font-medium">{p.name}</span>
                </label>
              ))}
            </div>
            {connector && (
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() =>
                    selectJiraProjects(connector.id, Array.from(selected)).then(() =>
                      qc.invalidateQueries({
                        queryKey: ["jira-projects", connector.id],
                      })
                    )
                  }
                >
                  Save selection
                </Button>
                <Button
                  size="sm"
                  disabled={selected.size === 0}
                  onClick={async () => {
                    try {
                      await selectJiraProjects(connector.id, Array.from(selected));
                      const job = await syncJira(connector.id);
                      setOutput(
                        `Sync ${job.status}\n${JSON.stringify(job.stats || {}, null, 2)}`
                      );
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

        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>AI tools</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="space-y-3">
              <div className="flex gap-2">
                <Input
                  value={issueKey}
                  onChange={(e) => setIssueKey(e.target.value)}
                  placeholder="ISSUE-KEY"
                />
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!connector}
                  onClick={async () => {
                    try {
                      const data = await jiraExplainStory(connector!.id, issueKey);
                      setOutput(String(data.explanation || JSON.stringify(data, null, 2)));
                    } catch (err: unknown) {
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      setError((err as any)?.response?.data?.error?.message || "Failed");
                    }
                  }}
                >
                  Explain story
                </Button>
              </div>
              <div className="flex gap-2">
                <Input value={jql} onChange={(e) => setJql(e.target.value)} />
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!connector}
                  onClick={async () => {
                    try {
                      const data = await jiraIssueSearch(connector!.id, jql);
                      setOutput(
                        `${data.overview || ""}\n\n${JSON.stringify(data.issues || [], null, 2)}`
                      );
                    } catch (err: unknown) {
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      setError((err as any)?.response?.data?.error?.message || "Failed");
                    }
                  }}
                >
                  JQL search
                </Button>
              </div>
              <div className="flex gap-2">
                <Input
                  value={projectKey}
                  onChange={(e) => setProjectKey(e.target.value)}
                  placeholder="Project key"
                />
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!connector}
                  onClick={async () => {
                    try {
                      const data = await jiraSprintSummary(connector!.id, projectKey);
                      setOutput(String(data.summary || JSON.stringify(data, null, 2)));
                    } catch (err: unknown) {
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      setError((err as any)?.response?.data?.error?.message || "Failed");
                    }
                  }}
                >
                  Sprint summary
                </Button>
              </div>
              <div className="flex gap-2">
                <Input value={query} onChange={(e) => setQuery(e.target.value)} />
                <Button
                  size="sm"
                  disabled={!connector}
                  onClick={async () => {
                    try {
                      const data = await jiraSearch(connector!.id, query);
                      setOutput(String(data.answer || JSON.stringify(data, null, 2)));
                    } catch (err: unknown) {
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      setError((err as any)?.response?.data?.error?.message || "Failed");
                    }
                  }}
                >
                  AI search
                </Button>
              </div>
            </div>
            <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-background/50 p-3 text-xs text-muted-foreground">
              {output || "Results appear here."}
            </pre>
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  );
}
