"use client";

import { motion } from "motion/react";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { Counter } from "@/components/ui/primitives";
import { cn, trim } from "@/lib/utils";

/**
 * Stat tile: label · value · delta · sparkline.
 * Katta raqamlar proportional figuralarda (tabular-nums faqat jadval/o'q uchun).
 */
export function StatTile({
  label,
  value,
  unit,
  digits = 1,
  delta,
  deltaLabel,
  upIsGood = true,
  spark,
  accent = "#0284c7",
  index = 0,
}: {
  label: string;
  value: number;
  unit?: string;
  digits?: number;
  delta?: number;
  deltaLabel?: string;
  upIsGood?: boolean;
  spark?: number[];
  accent?: string;
  index?: number;
}) {
  const dir = delta === undefined ? 0 : delta > 0.05 ? 1 : delta < -0.05 ? -1 : 0;
  const good = dir === 0 ? null : upIsGood ? dir > 0 : dir < 0;
  const deltaColor = good === null ? "#8fa3d4" : good ? "#0ca30c" : "#d03b3b";
  const DeltaIcon = dir === 0 ? Minus : dir > 0 ? ArrowUpRight : ArrowDownRight;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      className="glass relative overflow-hidden rounded-2xl px-3 py-2.5"
    >
      <div className="truncate text-[10.5px] text-ink-3">{label}</div>

      <div className="mt-1 flex items-baseline gap-1">
        <span className="text-[22px] leading-none font-semibold tracking-tight text-ink">
          <Counter value={value} digits={digits} />
        </span>
        {unit ? <span className="text-[11px] text-ink-3">{unit}</span> : null}
      </div>

      {delta !== undefined ? (
        <div className="mt-1.5 flex items-center gap-1">
          <DeltaIcon size={12} style={{ color: deltaColor }} />
          <span className="tnum text-[11px] font-semibold" style={{ color: deltaColor }}>
            {delta > 0 ? "+" : ""}
            {trim(delta)}%
          </span>
          {deltaLabel ? <span className="text-[10px] text-ink-3">{deltaLabel}</span> : null}
        </div>
      ) : null}

      {spark && spark.length > 1 ? <Sparkline points={spark} accent={accent} /> : null}
    </motion.div>
  );
}

function Sparkline({ points, accent }: { points: number[]; accent: string }) {
  const w = 100;
  const h = 22;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const step = w / (points.length - 1);
  const d = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${(i * step).toFixed(2)} ${(h - ((p - min) / span) * h).toFixed(2)}`)
    .join(" ");
  const lastX = w - 2;
  const lastY = h - ((points[points.length - 1] - min) / span) * h;

  return (
    <svg
      viewBox={`0 0 ${w} ${h + 4}`}
      className="mt-2 h-6 w-full pr-1 overflow-visible"
      preserveAspectRatio="none"
      aria-hidden
    >
      <motion.path
        d={d}
        fill="none"
        stroke="#5a6588"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
      />
      <circle cx={lastX} cy={lastY} r={3.2} fill={accent} stroke="#0b1024" strokeWidth={2} />
    </svg>
  );
}

export function HeroFigure({
  label,
  value,
  suffix = "%",
  color,
  caption,
  className,
}: {
  label: string;
  value: number;
  suffix?: string;
  color: string;
  caption?: string;
  className?: string;
}) {
  return (
    <div className={cn("glass glass-top-glow relative overflow-hidden rounded-2xl px-4 py-3.5", className)}>
      <div
        className="pointer-events-none absolute -top-16 -right-12 size-40 rounded-full opacity-25 blur-3xl"
        style={{ background: color }}
      />
      <div className="relative">
        <div className="text-[10.5px] tracking-wide text-ink-3 uppercase">{label}</div>
        <div className="mt-1 flex items-baseline gap-1.5">
          <span className="text-[48px] leading-[0.95] font-semibold tracking-tight text-ink">
            <Counter value={value} digits={1} duration={1.4} />
          </span>
          <span className="text-xl font-medium text-ink-3">{suffix}</span>
        </div>
        {caption ? <div className="mt-1.5 text-[11px] text-ink-2">{caption}</div> : null}
      </div>
    </div>
  );
}
