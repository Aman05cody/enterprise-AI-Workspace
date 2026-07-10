"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { listOrganizations } from "@/features/auth/api";
import {
  connectSlack,
  disconnectSlack,
  listSlackChannels,
  listSlackConnectors,
  refreshSlackChannels,
  selectSlackChannels,
  slackChannelSummary,
  slackMeetingRecap,
  slackSearch,
  syncSlack,
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

export default function SlackConnectorPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [orgId, setOrgId] = useState<string | null>(null);
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [output, setOutput] = useState("");
  const [query, setQuery] = useState("What decisions were made recently?");
  const [activeChannel, setActiveChannel] = useState<string>("");

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
    queryKey: ["slack-connectors", orgId],
    queryFn: () => listSlackConnectors(orgId!),
    enabled: !!orgId,
  });
  const connector = connectors.data?.[0] ?? null;

  const channels = useQuery({
    queryKey: ["slack-channels", connector?.id],
    queryFn: () => listSlackChannels(connector!.id),
    enabled: !!connector,
  });

  useEffect(() => {
    if (channels.data) {
      setSelected(
        new Set(channels.data.filter((c) => c.sync_enabled).map((c) => c.id))
      );
      if (!activeChannel && channels.data[0]) setActiveChannel(channels.data[0].id);
    }
  }, [channels.data, activeChannel]);

  const connect = useMutation({
    mutationFn: () =>
      connectSlack({ organization_id: orgId!, bot_token: token }),
    onSuccess: () => {
      setToken("");
      qc.invalidateQueries({ queryKey: ["slack-connectors", orgId] });
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
          / Connectors / Slack
        </p>
        <h1 className="text-2xl font-semibold">Slack AI</h1>
        <p className="text-sm text-muted-foreground">
          Channel summaries · AI search · meeting recaps · history indexing
        </p>
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Connection</CardTitle>
            <CardDescription>
              Bot token with <code>channels:history</code>, <code>channels:read</code>,{" "}
              <code>groups:history</code>
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
                      refreshSlackChannels(connector.id).then(() =>
                        qc.invalidateQueries({
                          queryKey: ["slack-channels", connector.id],
                        })
                      )
                    }
                  >
                    Refresh channels
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() =>
                      disconnectSlack(connector.id).then(() =>
                        qc.invalidateQueries({
                          queryKey: ["slack-connectors", orgId],
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
                  <Label>Bot token</Label>
                  <Input
                    type="password"
                    placeholder="xoxb-…"
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
                  {connect.isPending ? "Connecting…" : "Connect Slack"}
                </Button>
              </>
            )}
            {error && <p className="text-sm text-destructive">{error}</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Channels</CardTitle>
            <CardDescription>Select channels to index into Slack Workspace KB</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="max-h-64 space-y-2 overflow-y-auto">
              {(channels.data || []).map((ch) => (
                <label
                  key={ch.id}
                  className="flex cursor-pointer gap-2 rounded-md border border-border px-3 py-2 text-sm"
                >
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={selected.has(ch.id)}
                    onChange={(e) => {
                      const next = new Set(selected);
                      if (e.target.checked) next.add(ch.id);
                      else next.delete(ch.id);
                      setSelected(next);
                    }}
                  />
                  <span className="font-medium">{ch.name}</span>
                </label>
              ))}
            </div>
            {connector && (
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() =>
                    selectSlackChannels(connector.id, Array.from(selected)).then(() =>
                      qc.invalidateQueries({
                        queryKey: ["slack-channels", connector.id],
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
                      await selectSlackChannels(connector.id, Array.from(selected));
                      const job = await syncSlack(connector.id);
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
            <CardDescription>Live channel tools + grounded search over indexed history</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="space-y-3">
              <div>
                <Label>Channel</Label>
                <select
                  className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={activeChannel}
                  onChange={(e) => setActiveChannel(e.target.value)}
                >
                  {(channels.data || []).map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!connector || !activeChannel}
                  onClick={async () => {
                    try {
                      const data = await slackChannelSummary(connector!.id, activeChannel);
                      setOutput(String(data.summary || JSON.stringify(data, null, 2)));
                    } catch (err: unknown) {
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      setError((err as any)?.response?.data?.error?.message || "Failed");
                    }
                  }}
                >
                  Channel summary
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!connector || !activeChannel}
                  onClick={async () => {
                    try {
                      const data = await slackMeetingRecap(connector!.id, activeChannel);
                      setOutput(String(data.recap || JSON.stringify(data, null, 2)));
                    } catch (err: unknown) {
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      setError((err as any)?.response?.data?.error?.message || "Failed");
                    }
                  }}
                >
                  Meeting recap
                </Button>
              </div>
              <div className="flex gap-2">
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="AI search indexed Slack…"
                />
                <Button
                  size="sm"
                  disabled={!connector}
                  onClick={async () => {
                    try {
                      const data = await slackSearch(connector!.id, query);
                      setOutput(String(data.answer || JSON.stringify(data, null, 2)));
                    } catch (err: unknown) {
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      setError((err as any)?.response?.data?.error?.message || "Failed");
                    }
                  }}
                >
                  Search
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
