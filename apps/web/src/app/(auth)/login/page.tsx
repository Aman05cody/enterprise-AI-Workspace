"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Sparkles } from "lucide-react";
import { login, persistSession } from "@/features/auth/api";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setError(null);
    try {
      const tokens = await login(values);
      persistSession(tokens);
      router.push("/dashboard");
    } catch (err: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const ax = err as any;
      const msg =
        ax?.response?.data?.error?.message ||
        (ax?.code === "ERR_NETWORK"
          ? "Cannot reach API. Is the backend running on port 8000?"
          : null) ||
        (ax?.response?.status === 500
          ? "Server error — database may be unavailable."
          : null) ||
        "Login failed";
      setError(msg);
    }
  };

  return (
    <main className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden overflow-hidden border-r border-white/5 lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div className="pointer-events-none absolute inset-0 mesh-grid opacity-50" />
        <div className="pointer-events-none absolute -left-20 top-20 h-72 w-72 rounded-full bg-indigo-500/20 blur-3xl" />
        <div className="pointer-events-none absolute bottom-10 right-0 h-80 w-80 rounded-full bg-violet-500/15 blur-3xl" />

        <div className="relative flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/30">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <span className="font-semibold tracking-tight">
            Enterprise AI Workspace
          </span>
        </div>

        <div className="relative max-w-md space-y-4">
          <h2 className="text-3xl font-semibold leading-tight tracking-tight">
            Grounded answers.
            <br />
            <span className="text-gradient">Enterprise control.</span>
          </h2>
          <p className="text-muted-foreground leading-relaxed">
            Sign in to manage knowledge bases, chat with citations, and
            connect the tools your teams already use.
          </p>
        </div>

        <p className="relative text-xs text-muted-foreground">
          Secure multi-tenant platform · RBAC · audit-ready
        </p>
      </div>

      <div className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md space-y-8">
          <div className="space-y-2 text-center lg:text-left">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/30 lg:hidden">
              <Sparkles className="h-6 w-6 text-white" />
            </div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Welcome back
            </h1>
            <p className="text-sm text-muted-foreground">
              Sign in to your Enterprise AI Workspace
            </p>
          </div>

          <form
            className="space-y-4 rounded-2xl border border-white/[0.08] bg-card/60 p-6 shadow-xl backdrop-blur-xl sm:p-8"
            onSubmit={handleSubmit(onSubmit)}
          >
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="you@company.com"
                {...register("email")}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                {...register("password")}
              />
            </div>
            {error && (
              <div
                className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300"
                role="alert"
              >
                {error}
              </div>
            )}
            <Button className="w-full" size="lg" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Signing in…" : "Sign in"}
              {!isSubmitting && <ArrowRight className="h-4 w-4" />}
            </Button>
          </form>

          <p className="text-center text-sm text-muted-foreground">
            No account?{" "}
            <Link
              href="/register"
              className="font-medium text-indigo-300 hover:text-indigo-200 hover:underline"
            >
              Create one free
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
