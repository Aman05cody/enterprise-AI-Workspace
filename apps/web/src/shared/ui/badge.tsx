import * as React from "react";
import { cn } from "@/shared/lib/utils";

export function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & {
  variant?: "default" | "success" | "warning" | "muted" | "accent";
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium tracking-wide",
        variant === "default" &&
          "bg-indigo-500/15 text-indigo-300 ring-1 ring-inset ring-indigo-500/25",
        variant === "success" &&
          "bg-emerald-500/15 text-emerald-300 ring-1 ring-inset ring-emerald-500/25",
        variant === "warning" &&
          "bg-amber-500/15 text-amber-300 ring-1 ring-inset ring-amber-500/25",
        variant === "muted" &&
          "bg-white/5 text-muted-foreground ring-1 ring-inset ring-white/10",
        variant === "accent" &&
          "bg-violet-500/15 text-violet-300 ring-1 ring-inset ring-violet-500/25",
        className
      )}
      {...props}
    />
  );
}
