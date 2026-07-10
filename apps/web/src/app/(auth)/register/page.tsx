"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Sparkles } from "lucide-react";
import { persistSession, register as registerUser } from "@/features/auth/api";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";

const schema = z.object({
  full_name: z.string().min(1, "Name is required"),
  email: z.string().email(),
  password: z
    .string()
    .min(8)
    .regex(/[A-Za-z]/, "Must include a letter")
    .regex(/[0-9]/, "Must include a number"),
});

type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
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
      const tokens = await registerUser(values);
      persistSession(tokens);
      router.push("/dashboard");
    } catch (err: unknown) {
      const msg =
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (err as any)?.response?.data?.error?.message || "Registration failed";
      setError(msg);
    }
  };

  return (
    <main className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden overflow-hidden border-r border-white/5 lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div className="pointer-events-none absolute inset-0 mesh-grid opacity-50" />
        <div className="pointer-events-none absolute -left-20 top-20 h-72 w-72 rounded-full bg-violet-500/20 blur-3xl" />
        <div className="pointer-events-none absolute bottom-10 right-0 h-80 w-80 rounded-full bg-indigo-500/15 blur-3xl" />

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
            Spin up your team&apos;s
            <br />
            <span className="text-gradient">AI knowledge layer.</span>
          </h2>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li className="flex gap-2">
              <span className="text-indigo-400">✓</span>
              Create workspaces and invite members
            </li>
            <li className="flex gap-2">
              <span className="text-indigo-400">✓</span>
              Upload docs and chat with citations
            </li>
            <li className="flex gap-2">
              <span className="text-indigo-400">✓</span>
              Connect GitHub, Slack, Notion, Drive, Jira
            </li>
          </ul>
        </div>

        <p className="relative text-xs text-muted-foreground">
          Free local development · no credit card
        </p>
      </div>

      <div className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md space-y-8">
          <div className="space-y-2 text-center lg:text-left">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/30 lg:hidden">
              <Sparkles className="h-6 w-6 text-white" />
            </div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Create your account
            </h1>
            <p className="text-sm text-muted-foreground">
              Start your secure multi-tenant AI workspace
            </p>
          </div>

          <form
            className="space-y-4 rounded-2xl border border-white/[0.08] bg-card/60 p-6 shadow-xl backdrop-blur-xl sm:p-8"
            onSubmit={handleSubmit(onSubmit)}
          >
            <div className="space-y-2">
              <Label htmlFor="full_name">Full name</Label>
              <Input
                id="full_name"
                placeholder="Ada Lovelace"
                {...register("full_name")}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Work email</Label>
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
                autoComplete="new-password"
                placeholder="Min 8 chars, letters + numbers"
                {...register("password")}
              />
              <p className="text-xs text-muted-foreground">
                At least 8 characters with letters and numbers
              </p>
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
              {isSubmitting ? "Creating…" : "Create account"}
              {!isSubmitting && <ArrowRight className="h-4 w-4" />}
            </Button>
          </form>

          <p className="text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link
              href="/login"
              className="font-medium text-indigo-300 hover:text-indigo-200 hover:underline"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
