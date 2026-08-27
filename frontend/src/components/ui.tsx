import { type ButtonHTMLAttributes, type InputHTMLAttributes, type SelectHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Button({
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" }) {
  const styles = {
    primary:
      "bg-cyan-400/90 text-slate-950 hover:bg-cyan-300 shadow-[0_0_24px_rgba(34,211,238,0.25)]",
    ghost:
      "bg-white/5 text-slate-100 border border-white/10 hover:bg-white/10 hover:border-cyan-400/30",
    danger: "bg-rose-500/90 text-white hover:bg-rose-400",
  }[variant];
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition disabled:opacity-50",
        styles,
        className
      )}
      {...props}
    />
  );
}

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("glass rounded-2xl p-5", className)} {...props} />;
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2.5 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-400/50",
        className
      )}
      {...props}
    />
  );
}

export function Select({ className, children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-cyan-400/50",
        className
      )}
      {...props}
    >
      {children}
    </select>
  );
}

export function Label({ children }: { children: React.ReactNode }) {
  return <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-slate-400">{children}</label>;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-xl bg-white/5", className)} />;
}

export function RiskBadge({ level }: { level: string }) {
  const map: Record<string, string> = {
    LOW: "bg-emerald-400/15 text-emerald-300 border-emerald-400/30",
    MEDIUM: "bg-amber-400/15 text-amber-300 border-amber-400/30",
    HIGH: "bg-orange-400/15 text-orange-300 border-orange-400/30",
    CRITICAL: "bg-rose-400/15 text-rose-300 border-rose-400/30",
  };
  return (
    <span className={cn("rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tracking-wide", map[level] || "bg-white/10 text-slate-300")}>
      {level}
    </span>
  );
}

export function DemoBanner({ show }: { show?: boolean }) {
  if (!show) return null;
  return (
    <div className="mb-5 rounded-xl border border-amber-400/20 bg-amber-400/10 px-4 py-2.5 text-sm text-amber-200">
      DEMO / SYNTHETIC DATA — metrics are generated from a simulated dataset and are not real-world performance.
    </div>
  );
}
