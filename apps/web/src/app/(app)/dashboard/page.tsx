"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  Building2,
  FileText,
  Github,
  HardDrive,
  Plus,
  Slack,
  Sparkles,
  Trello,
} from "lucide-react";
import {
  clearSession,
  createOrganization,
  getMe,
  listOrganizations,
  type Organization,
} from "@/features/auth/api";
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
import { Badge } from "@/shared/ui/badge";
import { PageContainer, PageHeader } from "@/shared/ui/app-shell";

const quickLinks = [
  {
    href: "/knowledge",
    title: "Knowledge bases",
    desc: "Upload docs, search, and chat",
    icon: BookOpen,
    tone: "from-indigo-500/20 to-indigo-600/5 text-indigo-300",
  },
  {
    href: "/analytics",
    title: "Analytics",
    desc: "Usage, storage, audit trail",
    icon: BarChart3,
    tone: "from-violet-500/20 to-violet-600/5 text-violet-300",
  },
  {
    href: "/connectors/github",
    title: "GitHub",
    desc: "Repos, PR review, code chat",
    icon: Github,
    tone: "from-slate-400/20 to-slate-500/5 text-slate-200",
  },
  {
    href: "/connectors/notion",
    title: "Notion",
    desc: "Sync pages into knowledge",
    icon: FileText,
    tone: "from-stone-400/20 to-stone-500/5 text-stone-200",
  },
  {
    href: "/connectors/drive",
    title: "Google Drive",
    desc: "Folder sync and index",
    icon: HardDrive,
    tone: "from-sky-500/20 to-sky-600/5 text-sky-300",
  },
  {
    href: "/connectors/slack",
    title: "Slack",
    desc: "Summaries and channel search",
    icon: Slack,
    tone: "from-fuchsia-500/20 to-fuchsia-600/5 text-fuchsia-300",
  },
  {
    href: "/connectors/jira",
    title: "Jira",
    desc: "Sprints and issue intelligence",
    icon: Trello,
    tone: "from-blue-500/20 to-blue-600/5 text-blue-300",
  },
];

export default function DashboardPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [workspaceName, setWorkspaceName] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!localStorage.getItem("eaw_access_token")) {
      router.replace("/login");
    }
  }, [router]);

  const me = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    retry: false,
  });

  const orgs = useQuery({
    queryKey: ["organizations"],
    queryFn: listOrganizations,
    enabled: !!me.data,
  });

  const createOrg = useMutation({
    mutationFn: () => createOrganization({ name: workspaceName }),
    onSuccess: (org: Organization) => {
      localStorage.setItem("eaw_org_id", org.id);
      setWorkspaceName("");
      qc.invalidateQueries({ queryKey: ["organizations"] });
    },
    onError: (err: unknown) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError(
        (err as any)?.response?.data?.error?.message ||
          "Failed to create workspace"
      );
    },
  });

  if (me.isError) {
    clearSession();
    router.replace("/login");
    return null;
  }

  const firstName = me.data?.full_name?.split(" ")[0] || "there";

  return (
    <PageContainer>
      {/* Hero banner */}
      <div className="relative mb-8 overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-indigo-500/15 via-card/80 to-violet-500/10 p-6 sm:p-8">
        <div className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-indigo-500/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-12 left-1/3 h-32 w-32 rounded-full bg-violet-500/15 blur-3xl" />
        <div className="relative flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/5 px-3 py-1 text-xs text-muted-foreground ring-1 ring-white/10">
              <Sparkles className="h-3 w-3 text-indigo-300" />
              Enterprise AI Workspace
            </div>
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              Welcome back, {me.isLoading ? "…" : firstName}
            </h1>
            <p className="max-w-lg text-sm text-muted-foreground">
              {me.data?.email || "Loading your account…"} — manage workspaces,
              knowledge, and connectors from one place.
            </p>
          </div>
          <Link href="/knowledge">
            <Button>
              Open knowledge
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Building2 className="h-4 w-4 text-indigo-300" />
              <CardTitle>Your workspaces</CardTitle>
            </div>
            <CardDescription>
              Multi-tenant isolation with RBAC roles. Click to set active
              workspace.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {orgs.isLoading && (
              <div className="h-16 animate-pulse rounded-xl bg-white/5 shimmer" />
            )}
            {orgs.data?.length === 0 && (
              <div className="rounded-xl border border-dashed border-white/10 bg-white/[0.02] px-4 py-8 text-center">
                <p className="text-sm text-muted-foreground">
                  No workspaces yet. Create one to get started.
                </p>
              </div>
            )}
            {orgs.data?.map((org) => (
              <button
                key={org.id}
                type="button"
                className="group flex w-full items-center justify-between rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3.5 text-left transition hover:border-indigo-500/30 hover:bg-indigo-500/5"
                onClick={() => localStorage.setItem("eaw_org_id", org.id)}
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/30 to-violet-600/20 text-sm font-semibold text-indigo-200 ring-1 ring-white/10">
                    {org.name.slice(0, 1).toUpperCase()}
                  </div>
                  <div>
                    <p className="font-medium group-hover:text-white">
                      {org.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      /{org.slug} · {org.plan_tier} plan
                    </p>
                  </div>
                </div>
                <Badge className="capitalize">{org.my_role}</Badge>
              </button>
            ))}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Plus className="h-4 w-4 text-violet-300" />
              <CardTitle>Create workspace</CardTitle>
            </div>
            <CardDescription>
              You become the Owner of the new organization.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="ws">Workspace name</Label>
              <Input
                id="ws"
                placeholder="Acme Corp"
                value={workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
              />
            </div>
            {error && (
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
                {error}
              </div>
            )}
            <Button
              className="w-full"
              disabled={!workspaceName.trim() || createOrg.isPending}
              onClick={() => {
                setError(null);
                createOrg.mutate();
              }}
            >
              {createOrg.isPending ? "Creating…" : "Create workspace"}
            </Button>
          </CardContent>
        </Card>
      </div>

      <div className="mt-8">
        <PageHeader
          title="Quick access"
          description="Jump into knowledge, analytics, or any connector."
        />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {quickLinks.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className="group rounded-2xl border border-white/[0.07] bg-card/50 p-4 transition hover:border-indigo-500/25 hover:bg-card/90"
              >
                <div
                  className={`mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br ${item.tone} ring-1 ring-white/10`}
                >
                  <Icon className="h-5 w-5" />
                </div>
                <p className="font-medium tracking-tight group-hover:text-white">
                  {item.title}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {item.desc}
                </p>
              </Link>
            );
          })}
        </div>
      </div>
    </PageContainer>
  );
}
