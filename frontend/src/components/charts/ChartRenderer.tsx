"use client";

import { motion } from "motion/react";
import { Table2, TrendingUp } from "lucide-react";
import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartSpec } from "@/lib/types";
import { cn, compactAxis, trim } from "@/lib/utils";

/* ── Chizma "chrome"i — hammasi ink tokenlarida, hech qachon seriya rangida ── */
const INK_MUTED = "#6b779c";
const INK_2 = "#a8b4d8";
const GRID = "#1e2a4d";
const SURFACE = "#0b1024";

/** Kategorik slotlar — dataviz validatoridan o'tgan tartib. Hech qachon aylantirilmaydi. */
const SLOTS = ["#e11d48", "#0284c7", "#65a30d", "#8b5cf6", "#0891b2", "#d97706", "#c026d3", "#059669"];
/** "Reja" — kontekst seriyasi, shuning uchun neytral kulrang (emphasis: amaldagi asosiy). */
const CONTEXT_GRAY = "#5a6588";

function seriesColor(spec: ChartSpec, index: number): string {
  const s = spec.series[index];
  if (s?.color) return s.color;
  if (s?.key === "plan") return CONTEXT_GRAY;
  return SLOTS[index % SLOTS.length];
}

const axisProps = {
  stroke: GRID,
  tick: { fill: INK_MUTED, fontSize: 10.5 },
  tickLine: false,
  axisLine: { stroke: GRID },
} as const;

// ── Tooltip ──────────────────────────────────────────────────────────

function GlassTooltip({
  active,
  payload,
  label,
  unit,
}: {
  active?: boolean;
  payload?: Array<{ name?: string; dataKey?: string; value?: number; color?: string }>;
  label?: string | number;
  unit?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass rounded-xl px-3 py-2 shadow-2xl">
      <div className="mb-1.5 text-[11px] font-semibold text-ink">{label}</div>
      <div className="space-y-1">
        {payload.map((p, i) => (
          <div key={i} className="flex items-center gap-2 text-[11px]">
            <span
              className="size-2 shrink-0 rounded-full ring-2"
              style={{ background: p.color, ["--tw-ring-color" as string]: SURFACE }}
            />
            <span className="text-ink-2">{p.name}</span>
            <span className="tnum ml-auto font-semibold text-ink">
              {trim(Number(p.value ?? 0))}
              {unit ? <span className="ml-0.5 text-ink-3">{unit}</span> : null}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Legenda (≥2 seriya uchun har doim) ───────────────────────────────

function Legend({ spec }: { spec: ChartSpec }) {
  if (spec.series.length < 2) return null;
  return (
    <div className="flex flex-wrap items-center gap-x-3.5 gap-y-1 px-1 pb-1">
      {spec.series.map((s, i) => (
        <span key={s.key} className="inline-flex items-center gap-1.5">
          <span
            className="h-[3px] w-3.5 rounded-full"
            style={{ background: seriesColor(spec, i) }}
          />
          <span className="text-[10.5px] text-ink-2">{s.label}</span>
        </span>
      ))}
    </div>
  );
}

// ── Jadval ko'rinishi (har bir chizmaning "egizagi") ─────────────────

function TableView({ spec }: { spec: ChartSpec }) {
  return (
    <div className="thin-scroll max-h-[220px] overflow-auto rounded-xl ring-1 ring-edge/40">
      <table className="w-full border-collapse text-[11px]">
        <thead className="sticky top-0 bg-deep/95 backdrop-blur">
          <tr>
            <th className="px-2.5 py-1.5 text-left font-semibold text-ink-2">Davr</th>
            {spec.series.map((s) => (
              <th key={s.key} className="px-2.5 py-1.5 text-right font-semibold text-ink-2">
                {s.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {spec.data.map((row, i) => (
            <tr key={i} className="border-t border-hairline/50">
              <td className="px-2.5 py-1.5 text-ink-2">{String(row.label)}</td>
              {spec.series.map((s) => (
                <td key={s.key} className="tnum px-2.5 py-1.5 text-right text-ink">
                  {trim(Number(row[s.key] ?? 0))}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Dumbbell (tuman ↔ respublika o'rtachasi) ─────────────────────────

function Dumbbell({ spec }: { spec: ChartSpec }) {
  const cA = seriesColor(spec, 0);
  const cB = seriesColor(spec, 1);
  const values = spec.data.flatMap((d) => [Number(d[spec.series[0].key]), Number(d[spec.series[1].key])]);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 100);
  const span = max - min || 1;
  const at = (v: number) => ((v - min) / span) * 100;

  return (
    <div className="space-y-2 px-1 pt-1">
      {spec.data.map((row, i) => {
        const a = Number(row[spec.series[0].key]);
        const b = Number(row[spec.series[1].key]);
        const [lo, hi] = a <= b ? [a, b] : [b, a];
        return (
          <motion.div
            key={String(row.label)}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04, duration: 0.4 }}
            className="group grid grid-cols-[76px_1fr_46px] items-center gap-2"
            title={`${row.label}: ${spec.series[0].label} ${trim(a)}%, ${spec.series[1].label} ${trim(b)}%`}
          >
            <span className="truncate text-[10.5px] text-ink-2">{String(row.label)}</span>
            <div className="relative h-5">
              {/* hairline o'q */}
              <div className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-hairline" />
              {/* farq chizig'i */}
              <div
                className="absolute top-1/2 h-[3px] -translate-y-1/2 rounded-full"
                style={{
                  left: `${at(lo)}%`,
                  width: `${Math.max(0.5, at(hi) - at(lo))}%`,
                  background: `linear-gradient(90deg, ${a <= b ? cA : cB}, ${a <= b ? cB : cA})`,
                  opacity: 0.5,
                }}
              />
              {/* markerlar — 2px sirt halqasi bilan */}
              {[
                { v: b, c: cB },
                { v: a, c: cA },
              ].map((m, k) => (
                <span
                  key={k}
                  className="absolute top-1/2 size-[9px] -translate-x-1/2 -translate-y-1/2 rounded-full ring-2"
                  style={{
                    left: `${at(m.v)}%`,
                    background: m.c,
                    ["--tw-ring-color" as string]: SURFACE,
                  }}
                />
              ))}
            </div>
            <span className="tnum text-right text-[10.5px] font-semibold text-ink">{trim(a)}%</span>
          </motion.div>
        );
      })}
    </div>
  );
}

// ── Diverging bar (rejadan chetlanish) ───────────────────────────────

/**
 * "100% rejaga nisbatan qancha chetlashdi" — bu qutbli o'lchov, shuning uchun
 * 0 dan o'sadigan oddiy ustun emas, balki NOL CHIZIG'IDAN ikki tomonga
 * o'sadigan ustunlar. 99% va 104% orasidagi farq shundagina ko'rinadi.
 */
function DivergingBar({ spec }: { spec: ChartSpec }) {
  const key = spec.series[0].key;
  const values = spec.data.map((d) => Number(d[key]));
  const bound = Math.max(4, ...values.map((v) => Math.abs(v)));

  return (
    <div className="space-y-1.5 px-1 pt-1.5">
      {spec.data.map((row, i) => {
        const v = Number(row[key]);
        const pos = v >= 0;
        const width = (Math.abs(v) / bound) * 50; // markazdan chapga/o'ngga, %
        const color = (row.color as string) ?? (pos ? "#2a78d6" : "#d03b3b");
        return (
          <motion.div
            key={String(row.label)}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.03, duration: 0.35 }}
            className="grid grid-cols-[88px_1fr_52px] items-center gap-2"
          >
            <span className="truncate text-[10.5px] text-ink-2" title={String(row.label)}>
              {String(row.label)}
            </span>
            <div className="relative h-3.5">
              {/* nol chizig'i — hairline, punktir emas */}
              <div className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-edge" />
              <motion.div
                className="absolute top-1/2 h-2.5 -translate-y-1/2"
                style={{
                  background: color,
                  left: pos ? "50%" : `${50 - width}%`,
                  borderRadius: pos ? "0 4px 4px 0" : "4px 0 0 4px",
                }}
                initial={{ width: 0 }}
                animate={{ width: `${Math.max(0.6, width)}%` }}
                transition={{ duration: 0.7, delay: i * 0.03, ease: [0.22, 1, 0.36, 1] }}
              />
            </div>
            <span className="tnum text-right text-[10.5px] font-semibold text-ink-2">
              {v > 0 ? "+" : ""}
              {trim(v)}
              {spec.unit ? spec.unit : ""}
            </span>
          </motion.div>
        );
      })}
    </div>
  );
}

// ── Asosiy renderer ──────────────────────────────────────────────────

export function ChartRenderer({
  spec,
  height = 190,
  className,
}: {
  spec: ChartSpec;
  height?: number;
  className?: string;
}) {
  const [asTable, setAsTable] = useState(false);

  const gradientId = useMemo(() => `grad-${spec.id}`, [spec.id]);
  const c0 = seriesColor(spec, 0);
  const c1 = seriesColor(spec, 1);

  // Ustunlarda faqat eng katta qiymatga to'g'ridan-to'g'ri yorliq (tanlab yorliqlash)
  const peakIndex = useMemo(() => {
    if (spec.kind !== "bar") return -1;
    let best = 0;
    spec.data.forEach((d, i) => {
      if (Math.abs(Number(d[spec.series[0].key])) > Math.abs(Number(spec.data[best][spec.series[0].key])))
        best = i;
    });
    return best;
  }, [spec]);

  const body = () => {
    if (asTable) return <TableView spec={spec} />;

    switch (spec.kind) {
      case "dumbbell":
        return <Dumbbell spec={spec} />;

      case "diverging-bar":
        return <DivergingBar spec={spec} />;

      case "area":
        return (
          <ResponsiveContainer width="100%" height={height}>
            <AreaChart data={spec.data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={c1} stopOpacity={0.22} />
                  <stop offset="100%" stopColor={c1} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke={GRID} strokeWidth={1} vertical={false} />
              <XAxis dataKey="label" {...axisProps} interval="preserveStartEnd" />
              <YAxis {...axisProps} width={44} tickFormatter={(v) => compactAxis(Number(v))} />
              <Tooltip
                content={<GlassTooltip unit={spec.unit} />}
                cursor={{ stroke: INK_MUTED, strokeWidth: 1 }}
              />
              <Area
                type="monotone"
                dataKey={spec.series[0].key}
                name={spec.series[0].label}
                stroke={c0}
                strokeWidth={2}
                fill="none"
                strokeDasharray="0"
                dot={false}
                activeDot={{ r: 4, strokeWidth: 2, stroke: SURFACE }}
              />
              <Area
                type="monotone"
                dataKey={spec.series[1]?.key ?? spec.series[0].key}
                name={spec.series[1]?.label ?? spec.series[0].label}
                stroke={c1}
                strokeWidth={2}
                fill={`url(#${gradientId})`}
                dot={false}
                activeDot={{ r: 4.5, strokeWidth: 2, stroke: SURFACE }}
              />
            </AreaChart>
          </ResponsiveContainer>
        );

      case "line":
        return (
          <ResponsiveContainer width="100%" height={height}>
            <LineChart data={spec.data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid stroke={GRID} strokeWidth={1} vertical={false} />
              <XAxis dataKey="label" {...axisProps} interval="preserveStartEnd" />
              <YAxis {...axisProps} width={44} tickFormatter={(v) => compactAxis(Number(v))} />
              <Tooltip
                content={<GlassTooltip unit={spec.unit} />}
                cursor={{ stroke: INK_MUTED, strokeWidth: 1 }}
              />
              {spec.series.map((s, i) => (
                <Line
                  key={s.key}
                  type="monotone"
                  dataKey={s.key}
                  name={s.label}
                  stroke={seriesColor(spec, i)}
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  dot={false}
                  activeDot={{ r: 4.5, strokeWidth: 2, stroke: SURFACE }}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        );

      case "grouped-bar":
        return (
          <ResponsiveContainer width="100%" height={height}>
            <BarChart
              data={spec.data}
              margin={{ top: 8, right: 12, bottom: 0, left: 0 }}
              barGap={2}
              barCategoryGap="28%"
            >
              <CartesianGrid stroke={GRID} strokeWidth={1} vertical={false} />
              <XAxis dataKey="label" {...axisProps} interval={0} angle={-28} textAnchor="end" height={54} />
              <YAxis {...axisProps} width={44} tickFormatter={(v) => compactAxis(Number(v))} />
              <Tooltip
                content={<GlassTooltip unit={spec.unit} />}
                cursor={{ fill: "rgb(168 180 216 / 0.06)" }}
              />
              {spec.series.map((s, i) => (
                <Bar
                  key={s.key}
                  dataKey={s.key}
                  name={s.label}
                  fill={seriesColor(spec, i)}
                  radius={[4, 4, 0, 0]}
                  maxBarSize={18}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        );

      case "bar":
      default: {
        // Gorizontal ustunlar — uzun tuman/soha nomlari uchun to'g'ri shakl
        const barKey = spec.series[0].key;
        const rowH = 22;
        const h = Math.max(height, spec.data.length * rowH + 28);
        return (
          <ResponsiveContainer width="100%" height={h}>
            <BarChart
              layout="vertical"
              data={spec.data}
              margin={{ top: 4, right: 34, bottom: 4, left: 4 }}
              barCategoryGap="26%"
            >
              <CartesianGrid stroke={GRID} strokeWidth={1} horizontal={false} />
              <XAxis type="number" {...axisProps} tickFormatter={(v) => compactAxis(Number(v))} />
              <YAxis
                type="category"
                dataKey="label"
                {...axisProps}
                width={84}
                axisLine={false}
                tick={{ fill: INK_2, fontSize: 10.5 }}
              />
              <Tooltip
                content={<GlassTooltip unit={spec.unit} />}
                cursor={{ fill: "rgb(168 180 216 / 0.06)" }}
              />
              <Bar
                dataKey={barKey}
                name={spec.series[0].label}
                radius={[0, 4, 4, 0]}
                maxBarSize={16}
                label={{
                  position: "right",
                  fill: INK_2,
                  fontSize: 10,
                  formatter: (v: unknown) => trim(Number(v), 1),
                }}
              >
                {spec.data.map((row, i) => (
                  <Cell
                    key={i}
                    fill={(row.color as string) ?? seriesColor(spec, 0)}
                    fillOpacity={peakIndex === i || spec.data.length <= 3 ? 1 : 0.82}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        );
      }
    }
  };

  return (
    <motion.figure
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      className={cn("glass overflow-hidden rounded-2xl p-3", className)}
    >
      <figcaption className="mb-2 flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <div className="truncate text-[12.5px] font-semibold text-ink">{spec.title}</div>
          {spec.subtitle ? (
            <div className="truncate text-[10.5px] text-ink-3">{spec.subtitle}</div>
          ) : null}
        </div>
        <button
          onClick={() => setAsTable((v) => !v)}
          className={cn(
            "grid size-7 shrink-0 place-items-center rounded-lg ring-1 transition",
            asTable
              ? "bg-cyan/15 text-cyan ring-cyan/40"
              : "bg-abyss/50 text-ink-3 ring-edge/50 hover:text-ink-2",
          )}
          title={asTable ? "Grafik ko'rinishi" : "Jadval ko'rinishi"}
          aria-pressed={asTable}
        >
          {asTable ? <TrendingUp size={13} /> : <Table2 size={13} />}
        </button>
      </figcaption>

      {!asTable && <Legend spec={spec} />}
      {body()}
    </motion.figure>
  );
}
