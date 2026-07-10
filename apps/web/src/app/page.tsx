import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  Bot,
  Github,
  Lock,
  Shield,
  Sparkles,
  Zap,
} from "lucide-react";
import { Button } from "@/shared/ui/button";
import { Badge } from "@/shared/ui/badge";

const features = [
  {
    icon: BookOpen,
    title: "Grounded RAG chat",
    desc: "Answers with citations from your knowledge bases — refuses when context is weak.",
  },
  {
    icon: Shield,
    title: "Multi-tenant security",
    desc: "Workspace isolation, JWT auth, RBAC roles from Owner to Guest.",
  },
  {
    icon: Github,
    title: "Connectors",
    desc: "GitHub, Notion, Drive, Slack, and Jira — index and query where work lives.",
  },
  {
    icon: Zap,
    title: "Admin analytics",
    desc: "Usage, storage, search trends, and audit trails for enterprise ops.",
  },
];

export default function LandingPage() {
  return (
    <main className="relative min-h-screen overflow-hidden">
      <div className="pointer-events-none absolute inset-0 mesh-grid opacity-60" />

      <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/30">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold tracking-tight">
              Enterprise AI Workspace
            </p>
            <p className="text-[11px] text-muted-foreground">
              Secure · Multi-tenant · Grounded
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/login">
            <Button variant="ghost">Sign in</Button>
          </Link>
          <Link href="/register">
            <Button>
              Get started
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </header>

      <section className="relative z-10 mx-auto grid max-w-6xl gap-12 px-6 pb-20 pt-12 lg:grid-cols-2 lg:items-center lg:pt-20">
        <div className="space-y-7">
          <Badge variant="accent" className="px-3 py-1">
            <Bot className="mr-1.5 h-3 w-3" />
            Production-ready AI platform
          </Badge>
          <h1 className="text-4xl font-semibold leading-[1.1] tracking-tight md:text-5xl lg:text-6xl">
            Your company&apos;s{" "}
            <span className="text-gradient">secure AI workspace</span>
          </h1>
          <p className="max-w-xl text-lg leading-relaxed text-muted-foreground">
            Multi-tenant knowledge, grounded answers with citations, and
            connector intelligence — built like an internal platform from the
            best enterprise AI teams.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link href="/register">
              <Button size="lg">
                Create workspace
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/login">
              <Button size="lg" variant="outline">
                Sign in
              </Button>
            </Link>
          </div>
          <div className="flex flex-wrap gap-4 pt-2 text-sm text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <Lock className="h-3.5 w-3.5 text-emerald-400" />
              JWT + refresh rotation
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Shield className="h-3.5 w-3.5 text-indigo-400" />
              RBAC isolation
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-violet-400" />
              Citation-backed RAG
            </span>
          </div>
        </div>

        {/* Product preview card */}
        <div className="relative animate-float">
          <div className="absolute -inset-4 rounded-3xl bg-gradient-to-br from-indigo-500/20 via-violet-500/10 to-transparent blur-2xl" />
          <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-card/80 shadow-2xl shadow-black/50 backdrop-blur-xl glow-ring">
            <div className="flex items-center gap-2 border-b border-white/5 bg-white/[0.02] px-4 py-3">
              <span className="h-2.5 w-2.5 rounded-full bg-red-400/80" />
              <span className="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/80" />
              <span className="ml-3 text-xs text-muted-foreground">
                knowledge · chat · grounded
              </span>
            </div>
            <div className="space-y-4 p-5">
              <div className="flex gap-3">
                <div className="mt-1 h-8 w-8 shrink-0 rounded-full bg-white/10" />
                <div className="rounded-2xl rounded-tl-md bg-white/[0.04] px-4 py-3 text-sm text-muted-foreground ring-1 ring-white/5">
                  Summarize our Q3 security policy and list open risks.
                </div>
              </div>
              <div className="flex gap-3">
                <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-600">
                  <Sparkles className="h-3.5 w-3.5 text-white" />
                </div>
                <div className="flex-1 space-y-3 rounded-2xl rounded-tl-md bg-indigo-500/10 px-4 py-3 text-sm ring-1 ring-indigo-500/20">
                  <p className="leading-relaxed text-foreground/90">
                    Based on{" "}
                    <span className="text-indigo-300">security-policy-v3.pdf</span>{" "}
                    and{" "}
                    <span className="text-indigo-300">risk-register.xlsx</span>,
                    three residual risks remain open for vendor access…
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <Badge>Citation 1 · score 0.91</Badge>
                    <Badge variant="accent">Citation 2 · score 0.87</Badge>
                    <Badge variant="success">Confidence 0.88</Badge>
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 pt-1">
                {["Upload docs", "Index vectors", "Ask + cite"].map((step, i) => (
                  <div
                    key={step}
                    className="rounded-xl bg-white/[0.03] px-3 py-2.5 text-center ring-1 ring-white/5"
                  >
                    <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                      Step {i + 1}
                    </p>
                    <p className="mt-0.5 text-xs font-medium">{step}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="relative z-10 mx-auto max-w-6xl px-6 pb-24">
        <div className="mb-8 flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-indigo-300/80">
              Platform
            </p>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight">
              Everything your team needs
            </h2>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((f) => {
            const Icon = f.icon;
            return (
              <div
                key={f.title}
                className="group rounded-2xl border border-white/[0.07] bg-card/50 p-5 transition hover:border-indigo-500/30 hover:bg-card/80"
              >
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/15 text-indigo-300 ring-1 ring-indigo-500/20 transition group-hover:bg-indigo-500/25">
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="font-semibold tracking-tight">{f.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                  {f.desc}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      <footer className="relative z-10 border-t border-white/5 py-8 text-center text-xs text-muted-foreground">
        Enterprise AI Workspace
      </footer>
    </main>
  );
}
