"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BarChart3,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Github,
  LayoutDashboard,
  LogOut,
  PanelLeft,
  Slack,
  Sparkles,
  FileText,
  HardDrive,
  Trello,
} from "lucide-react";
import { clearSession, getMe } from "@/features/auth/api";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";

type NavItem = {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  match?: (path: string) => boolean;
};

const primaryNav: NavItem[] = [
  {
    href: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    match: (p) => p === "/dashboard",
  },
  {
    href: "/knowledge",
    label: "Knowledge",
    icon: BookOpen,
    match: (p) => p.startsWith("/knowledge") || p.startsWith("/chat"),
  },
  {
    href: "/analytics",
    label: "Analytics",
    icon: BarChart3,
    match: (p) => p.startsWith("/analytics"),
  },
];

const connectorNav: NavItem[] = [
  { href: "/connectors/github", label: "GitHub", icon: Github },
  { href: "/connectors/notion", label: "Notion", icon: FileText },
  { href: "/connectors/drive", label: "Drive", icon: HardDrive },
  { href: "/connectors/slack", label: "Slack", icon: Slack },
  { href: "/connectors/jira", label: "Jira", icon: Trello },
];

function NavLink({
  item,
  collapsed,
  active,
}: {
  item: NavItem;
  collapsed: boolean;
  active: boolean;
}) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      title={collapsed ? item.label : undefined}
      className={cn(
        "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all",
        active
          ? "bg-gradient-to-r from-indigo-500/20 to-violet-500/10 text-white shadow-sm ring-1 ring-inset ring-indigo-500/30"
          : "text-muted-foreground hover:bg-white/[0.04] hover:text-foreground"
      )}
    >
      <Icon
        className={cn(
          "h-[18px] w-[18px] shrink-0 transition-colors",
          active ? "text-indigo-300" : "text-muted-foreground group-hover:text-foreground"
        )}
      />
      {!collapsed && <span className="truncate">{item.label}</span>}
      {active && !collapsed && (
        <span className="ml-auto h-1.5 w-1.5 rounded-full bg-indigo-400 shadow-[0_0_8px] shadow-indigo-400" />
      )}
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userName, setUserName] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        if (!localStorage.getItem("eaw_access_token")) return;
        const me = await getMe();
        if (!cancelled) {
          setUserName(me.full_name);
          setUserEmail(me.email);
        }
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const isActive = (item: NavItem) =>
    item.match ? item.match(pathname) : pathname.startsWith(item.href);

  const sidebar = (
    <aside
      className={cn(
        "flex h-full flex-col border-r border-white/[0.06] bg-[hsl(var(--sidebar))]/95 backdrop-blur-xl transition-all duration-300",
        collapsed ? "w-[72px]" : "w-64"
      )}
    >
      <div
        className={cn(
          "flex h-16 items-center border-b border-white/[0.06] px-3",
          collapsed ? "justify-center" : "justify-between gap-2"
        )}
      >
        <Link href="/dashboard" className="flex min-w-0 items-center gap-2.5">
          <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/30">
            <Sparkles className="h-4 w-4 text-white" />
            <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-emerald-400 ring-2 ring-[hsl(var(--sidebar))]" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold tracking-tight">
                Enterprise AI
              </p>
              <p className="truncate text-[11px] text-muted-foreground">
                Workspace
              </p>
            </div>
          )}
        </Link>
        {!collapsed && (
          <button
            type="button"
            onClick={() => setCollapsed(true)}
            className="hidden rounded-lg p-1.5 text-muted-foreground hover:bg-white/5 hover:text-foreground lg:inline-flex"
            aria-label="Collapse sidebar"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        )}
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto p-3">
        <div className="space-y-1">
          {!collapsed && (
            <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground/70">
              Workspace
            </p>
          )}
          {primaryNav.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              collapsed={collapsed}
              active={isActive(item)}
            />
          ))}
        </div>

        <div className="space-y-1">
          {!collapsed && (
            <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground/70">
              Connectors
            </p>
          )}
          {connectorNav.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              collapsed={collapsed}
              active={pathname.startsWith(item.href)}
            />
          ))}
        </div>
      </nav>

      <div className="border-t border-white/[0.06] p-3">
        {collapsed ? (
          <div className="flex flex-col items-center gap-2">
            <button
              type="button"
              onClick={() => setCollapsed(false)}
              className="rounded-lg p-2 text-muted-foreground hover:bg-white/5 hover:text-foreground"
              aria-label="Expand sidebar"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => {
                clearSession();
                router.push("/login");
              }}
              className="rounded-lg p-2 text-muted-foreground hover:bg-red-500/10 hover:text-red-300"
              aria-label="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="flex items-center gap-3 rounded-xl bg-white/[0.03] px-3 py-2.5 ring-1 ring-inset ring-white/[0.06]">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500/40 to-violet-600/40 text-xs font-semibold text-white ring-1 ring-white/10">
                {(userName || "U")
                  .split(" ")
                  .map((p) => p[0])
                  .join("")
                  .slice(0, 2)
                  .toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">
                  {userName || "Loading…"}
                </p>
                <p className="truncate text-[11px] text-muted-foreground">
                  {userEmail || ""}
                </p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start text-muted-foreground"
              onClick={() => {
                clearSession();
                router.push("/login");
              }}
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </Button>
          </div>
        )}
      </div>
    </aside>
  );

  return (
    <div className="flex min-h-screen">
      {/* Desktop sidebar */}
      <div className="sticky top-0 hidden h-screen shrink-0 lg:block">{sidebar}</div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            aria-label="Close menu"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 w-72 shadow-2xl">{sidebar}</div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-white/[0.06] bg-background/70 px-4 backdrop-blur-xl lg:hidden">
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            className="rounded-lg p-2 text-muted-foreground hover:bg-white/5 hover:text-foreground"
            aria-label="Open menu"
          >
            <PanelLeft className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600">
              <Sparkles className="h-3.5 w-3.5 text-white" />
            </div>
            <span className="text-sm font-semibold">Enterprise AI</span>
          </div>
        </header>

        <div className="page-enter flex-1">{children}</div>
      </div>
    </div>
  );
}

/** Page chrome used inside AppShell pages */
export function PageHeader({
  title,
  description,
  actions,
  breadcrumb,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  breadcrumb?: React.ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
      <div className="space-y-1">
        {breadcrumb && (
          <div className="mb-1 text-sm text-muted-foreground">{breadcrumb}</div>
        )}
        <h1 className="text-2xl font-semibold tracking-tight md:text-3xl">
          {title}
        </h1>
        {description && (
          <p className="max-w-2xl text-sm text-muted-foreground md:text-base">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function PageContainer({
  children,
  className,
  wide,
}: {
  children: React.ReactNode;
  className?: string;
  wide?: boolean;
}) {
  return (
    <main
      className={cn(
        "mx-auto w-full px-4 py-6 sm:px-6 lg:px-8 lg:py-8",
        wide ? "max-w-7xl" : "max-w-6xl",
        className
      )}
    >
      {children}
    </main>
  );
}

