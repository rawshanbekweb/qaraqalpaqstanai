"use client";

import { animate, motion, useMotionValue, useTransform } from "motion/react";
import { useEffect, useRef, type ReactNode } from "react";
import { STATUS_BY_ID } from "@/data/modules";
import type { StatusId } from "@/lib/types";
import { cn, trim } from "@/lib/utils";

// ── Shisha panel ─────────────────────────────────────────────────────

export function Panel({
  children,
  className,
  glow = false,
  ...rest
}: {
  children: ReactNode;
  className?: string;
  glow?: boolean;
} & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("glass", glow && "glass-top-glow", className)} {...rest}>
      {children}
    </div>
  );
}

export function PanelHeader({
  icon,
  title,
  subtitle,
  action,
  className,
}: {
  icon?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center gap-3 border-b border-hairline/70 px-4 py-3", className)}>
      {icon ? (
        <div className="grid size-9 shrink-0 place-items-center rounded-xl bg-raised/70 text-cyan ring-1 ring-edge/60">
          {icon}
        </div>
      ) : null}
      <div className="min-w-0 flex-1">
        <div className="truncate text-[13px] font-semibold tracking-tight text-ink">{title}</div>
        {subtitle ? (
          <div className="truncate text-[11px] text-ink-3">{subtitle}</div>
        ) : null}
      </div>
      {action}
    </div>
  );
}

// ── Animatsion raqam ─────────────────────────────────────────────────

export function Counter({
  value,
  digits = 1,
  suffix = "",
  prefix = "",
  className,
  duration = 1.1,
}: {
  value: number;
  digits?: number;
  suffix?: string;
  prefix?: string;
  className?: string;
  duration?: number;
}) {
  const mv = useMotionValue(0);
  const text = useTransform(mv, (v) => `${prefix}${trim(v, digits)}${suffix}`);
  const prev = useRef(0);

  useEffect(() => {
    const controls = animate(mv, value, {
      duration,
      ease: [0.22, 1, 0.36, 1],
    });
    prev.current = value;
    return () => controls.stop();
  }, [value, mv, duration]);

  return <motion.span className={cn("tnum", className)}>{text}</motion.span>;
}

// ── Status ───────────────────────────────────────────────────────────

export function StatusDot({ status, size = 8 }: { status: StatusId; size?: number }) {
  const c = STATUS_BY_ID[status].color;
  return (
    <span className="relative inline-flex shrink-0" style={{ width: size, height: size }}>
      <span
        className="absolute inset-0 rounded-full"
        style={{ background: c, boxShadow: `0 0 10px ${c}` }}
      />
      {(status === "critical" || status === "at_risk") && (
        <span
          className="absolute inset-0 rounded-full animate-[pulse-ring_2.4s_cubic-bezier(0.4,0,0.6,1)_infinite]"
          style={{ background: c, opacity: 0.5 }}
        />
      )}
    </span>
  );
}

export function StatusPill({
  status,
  label,
  className,
}: {
  status: StatusId;
  label?: string;
  className?: string;
}) {
  const meta = STATUS_BY_ID[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-semibold tracking-wide uppercase",
        className,
      )}
      style={{
        color: meta.color,
        background: `color-mix(in oklab, ${meta.color} 14%, transparent)`,
        boxShadow: `inset 0 0 0 1px color-mix(in oklab, ${meta.color} 32%, transparent)`,
      }}
    >
      <StatusDot status={status} size={6} />
      {label ?? meta.name}
    </span>
  );
}

// ── Segmentli filtr ──────────────────────────────────────────────────

export interface SegmentOption<T extends string> {
  value: T;
  label: string;
  color?: string;
}

export function Segmented<T extends string>({
  options,
  value,
  onChange,
  layoutId,
  className,
  size = "md",
}: {
  options: SegmentOption<T>[];
  value: T;
  onChange: (v: T) => void;
  layoutId: string;
  className?: string;
  size?: "sm" | "md";
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-0.5 rounded-full bg-abyss/70 p-1 ring-1 ring-edge/50",
        className,
      )}
      role="tablist"
    >
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(o.value)}
            className={cn(
              "relative rounded-full whitespace-nowrap font-medium transition-colors",
              size === "sm" ? "px-2.5 py-1 text-[11px]" : "px-3.5 py-1.5 text-xs",
              active ? "text-void" : "text-ink-3 hover:text-ink-2",
            )}
          >
            {active && (
              <motion.span
                layoutId={layoutId}
                className="absolute inset-0 rounded-full"
                style={{
                  background: o.color
                    ? `linear-gradient(120deg, ${o.color}, color-mix(in oklab, ${o.color} 65%, #fff))`
                    : "linear-gradient(120deg, #22d3ee, #818cf8)",
                }}
                transition={{ type: "spring", stiffness: 420, damping: 34 }}
              />
            )}
            <span className="relative z-10">{o.label}</span>
          </button>
        );
      })}
    </div>
  );
}

// ── Tugma ────────────────────────────────────────────────────────────

export function Button({
  children,
  variant = "solid",
  className,
  ...rest
}: {
  children: ReactNode;
  variant?: "solid" | "ghost" | "outline" | "danger";
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-45 active:scale-[0.98]";
  const styles = {
    solid:
      "bg-gradient-to-br from-cyan to-iris text-void shadow-[0_8px_28px_-10px_rgba(34,211,238,0.75)] hover:brightness-110",
    ghost: "text-ink-2 hover:bg-raised/60 hover:text-ink",
    outline: "ring-1 ring-edge/70 text-ink-2 hover:ring-cyan/60 hover:text-ink bg-abyss/40",
    danger: "bg-crimson/15 text-crimson ring-1 ring-crimson/35 hover:bg-crimson/25",
  }[variant];
  return (
    <button className={cn(base, styles, className)} {...rest}>
      {children}
    </button>
  );
}

// ── Forma maydonlari ─────────────────────────────────────────────────

export function Field({
  label,
  hint,
  children,
  className,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label className={cn("block", className)}>
      <span className="mb-1.5 block text-[11px] font-semibold tracking-wide text-ink-3 uppercase">
        {label}
      </span>
      {children}
      {hint ? <span className="mt-1 block text-[11px] text-ink-3">{hint}</span> : null}
    </label>
  );
}

const inputBase =
  "w-full rounded-xl bg-abyss/70 px-3.5 py-2.5 text-sm text-ink ring-1 ring-edge/60 outline-none transition placeholder:text-ink-3/70 focus:ring-cyan/70 focus:bg-abyss";

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cn(inputBase, props.className)} />;
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={cn(inputBase, "resize-none", props.className)} />;
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={cn(inputBase, "appearance-none bg-no-repeat pr-9", props.className)}
      style={{
        backgroundImage:
          "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='none' stroke='%236b779c' stroke-width='2'%3E%3Cpath d='M4 6l4 4 4-4'/%3E%3C/svg%3E\")",
        backgroundPosition: "right 12px center",
        ...props.style,
      }}
    />
  );
}

// ── Progress ─────────────────────────────────────────────────────────

export function Meter({
  value,
  color = "#22d3ee",
  height = 6,
  className,
  delay = 0,
}: {
  /** 0..1 */
  value: number;
  color?: string;
  height?: number;
  className?: string;
  delay?: number;
}) {
  return (
    <div
      className={cn("w-full overflow-hidden rounded-full bg-abyss/80 ring-1 ring-edge/40", className)}
      style={{ height }}
    >
      <motion.div
        className="h-full rounded-full"
        style={{
          background: `linear-gradient(90deg, color-mix(in oklab, ${color} 55%, transparent), ${color})`,
          boxShadow: `0 0 12px color-mix(in oklab, ${color} 60%, transparent)`,
        }}
        initial={{ width: 0 }}
        animate={{ width: `${Math.min(100, Math.max(0, value * 100))}%` }}
        transition={{ duration: 0.9, delay, ease: [0.22, 1, 0.36, 1] }}
      />
    </div>
  );
}

// ── Skelet / yuklanish ───────────────────────────────────────────────

export function ThinkingDots({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1", className)}>
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="size-1.5 rounded-full bg-cyan"
          animate={{ opacity: [0.25, 1, 0.25], y: [0, -3, 0] }}
          transition={{ duration: 1.1, repeat: Infinity, delay: i * 0.16 }}
        />
      ))}
    </span>
  );
}
