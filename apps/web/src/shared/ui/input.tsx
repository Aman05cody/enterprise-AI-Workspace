import * as React from "react";
import { cn } from "@/shared/lib/utils";

export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, type, ...props }, ref) => (
  <input
    type={type}
    className={cn(
      "flex h-11 w-full rounded-xl border border-white/10 bg-white/[0.03] px-3.5 py-2 text-sm text-foreground shadow-inner shadow-black/20 ring-offset-background transition-colors placeholder:text-muted-foreground/70 focus-visible:border-indigo-500/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/30 disabled:cursor-not-allowed disabled:opacity-50",
      className
    )}
    ref={ref}
    {...props}
  />
));
Input.displayName = "Input";
