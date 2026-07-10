"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { listOrganizations } from "@/features/auth/api";
import {
  connectDrive,
  disconnectDrive,
  listDriveConnectors,
  listDriveFolders,
  refreshDriveFolders,
  selectDriveFolders,
  syncDrive,
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

export default function DriveConnectorPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [orgId, setOrgId] = useState<string | null>(null);
  const [accessToken, setAccessToken] = useState("");
  const [refreshToken, setRefreshToken] = useState("");
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
    queryKey: ["drive-connectors", orgId],
    queryFn: () => listDriveConnectors(orgId!),
    enabled: !!orgId,
  });
  const connector = connectors.data?.[0] ?? null;

  const folders = useQuery({
    queryKey: ["drive-folders", connector?.id],
    queryFn: () => listDriveFolders(connector!.id),
    enabled: !!connector,
  });

  useEffect(() => {
    if (folders.data) {
      setSelected(
        new Set(folders.data.filter((f) => f.sync_enabled).map((f) => f.id))
      );
    }
  }, [folders.data]);

  const connect = useMutation({
    mutationFn: () =>
      connectDrive({
        organization_id: orgId!,
        access_token: accessToken,
        refresh_token: refreshToken || undefined,
      }),
    onSuccess: () => {
      setAccessToken("");
      setRefreshToken("");
      qc.invalidateQueries({ queryKey: ["drive-connectors", orgId] });
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
          / Connectors / Google Drive
        </p>
        <h1 className="text-2xl font-semibold">Google Drive Sync</h1>
        <p className="text-sm text-muted-foreground">
          Connect with an OAuth access token, select folders, auto-index files
        </p>
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Connection</CardTitle>
            <CardDescription>
              OAuth access token with Drive readonly scope (admin only)
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
                      refreshDriveFolders(connector.id).then(() =>
                        qc.invalidateQueries({
                          queryKey: ["drive-folders", connector.id],
                        })
                      )
                    }
                  >
                    Refresh folders
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() =>
                      disconnectDrive(connector.id).then(() =>
                        qc.invalidateQueries({
                          queryKey: ["drive-connectors", orgId],
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
                  <Label htmlFor="at">Access token</Label>
                  <Input
                    id="at"
                    type="password"
                    value={accessToken}
                    onChange={(e) => setAccessToken(e.target.value)}
                    placeholder="ya29.…"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="rt">Refresh token (optional)</Label>
                  <Input
                    id="rt"
                    type="password"
                    value={refreshToken}
                    onChange={(e) => setRefreshToken(e.target.value)}
                  />
                </div>
                <Button
                  disabled={!orgId || accessToken.length < 10 || connect.isPending}
                  onClick={() => {
                    setError(null);
                    connect.mutate();
                  }}
                >
                  {connect.isPending ? "Connecting…" : "Connect Drive"}
                </Button>
              </>
            )}
            {error && <p className="text-sm text-destructive">{error}</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Folders</CardTitle>
            <CardDescription>
              Selected folders are walked recursively for indexable files
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="max-h-72 space-y-2 overflow-y-auto">
              {(folders.data || []).map((f) => (
                <label
                  key={f.id}
                  className="flex cursor-pointer gap-2 rounded-md border border-border px-3 py-2 text-sm"
                >
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={selected.has(f.id)}
                    onChange={(e) => {
                      const next = new Set(selected);
                      if (e.target.checked) next.add(f.id);
                      else next.delete(f.id);
                      setSelected(next);
                    }}
                  />
                  <span>
                    <span className="font-medium">{f.name}</span>
                    <span className="ml-2 text-xs text-muted-foreground">
                      {f.resource_type}
                    </span>
                    {f.knowledge_base_id && (
                      <span className="ml-2 text-xs text-emerald-400">synced</span>
                    )}
                  </span>
                </label>
              ))}
            </div>
            {connector && (
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() =>
                    selectDriveFolders(connector.id, Array.from(selected)).then(() =>
                      qc.invalidateQueries({
                        queryKey: ["drive-folders", connector.id],
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
                    setError(null);
                    try {
                      await selectDriveFolders(connector.id, Array.from(selected));
                      const job = await syncDrive(connector.id);
                      setOutput(
                        `Sync ${job.status}\n${JSON.stringify(job.stats || {}, null, 2)}`
                      );
                      qc.invalidateQueries({
                        queryKey: ["drive-folders", connector.id],
                      });
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
            <Link href="/knowledge" className="mt-3 inline-block">
              <Button size="sm" variant="outline">
                Open knowledge bases
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}
    </PageContainer>
  );
}
