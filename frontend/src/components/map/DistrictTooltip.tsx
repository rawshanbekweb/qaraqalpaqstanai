"use client";

import { AnimatePresence, motion } from "motion/react";
import { TrendingDown, TrendingUp } from "lucide-react";
import { MODULE_BY_ID } from "@/data/modules";
import { districtProfile } from "@/lib/analytics";
import { performanceColor } from "@/lib/scale";
import { Meter, StatusPill } from "@/components/ui/primitives";
import { trim } from "@/lib/utils";
import type { ModuleId } from "@/lib/types";

/**
 * `minX`/`maxX` — tooltip sig'ishi kerak bo'lgan ochiq maydon. Xarita butun
 * ekranni egallagani uchun uning chekkalari suzuvchi panellar ostida qoladi;
 * bu chegaralarsiz tooltip panel ortiga kirib ketadi.
 */
export function DistrictTooltip({
  districtId,
  x,
  y,
  year,
  moduleId,
  minX,
  maxX,
}: {
  districtId: string | null;
  x: number;
  y: number;
  year: number;
  moduleId: ModuleId | "all";
  minX: number;
  maxX: number;
}) {
  return (
    <AnimatePresence>
      {districtId ? (
        <Body
          key={districtId}
          districtId={districtId}
          x={x}
          y={y}
          year={year}
          moduleId={moduleId}
          minX={minX}
          maxX={maxX}
        />
      ) : null}
    </AnimatePresence>
  );
}

function Body({
  districtId,
  x,
  y,
  year,
  moduleId,
  minX,
  maxX,
}: {
  districtId: string;
  x: number;
  y: number;
  year: number;
  moduleId: ModuleId | "all";
  minX: number;
  maxX: number;
}) {
  const p = districtProfile(districtId, year);
  const W = 268;
  const raw = x + W + 24 > maxX ? x - W - 18 : x + 18;
  const left = Math.min(Math.max(raw, minX + 8), Math.max(minX + 8, maxX - W - 8));

  const shown =
    moduleId === "all"
      ? [...p.modules].sort((a, b) => a.performance - b.performance).slice(0, 4)
      : p.modules.filter((m) => m.moduleId === moduleId);

  return (
    <motion.div
      className="pointer-events-none absolute z-40"
      style={{ left, top: Math.max(8, y - 40), width: W }}
      initial={{ opacity: 0, scale: 0.92, y: 8 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95, y: 4 }}
      transition={{ type: "spring", stiffness: 460, damping: 32 }}
    >
      <div className="glass glass-top-glow overflow-hidden rounded-2xl">
        <div className="flex items-start gap-2 border-b border-hairline/70 px-3.5 py-2.5">
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-bold text-ink">{p.district.name}</div>
            <div className="truncate text-[10.5px] text-ink-3">
              {p.district.center} · {trim(p.district.population)} ming aholi
            </div>
          </div>
          <StatusPill status={p.status} />
        </div>

        <div className="px-3.5 py-3">
          <div className="mb-2.5 flex items-baseline justify-between">
            <span className="text-[10px] font-semibold tracking-wider text-ink-3 uppercase">
              Umumiy bajarilish
            </span>
            <span
              className="tnum text-lg font-bold"
              style={{ color: performanceColor(p.overall) }}
            >
              {trim(p.overall * 100)}%
            </span>
          </div>
          <Meter value={p.overall} color={performanceColor(p.overall)} height={5} />

          <div className="mt-3 space-y-2">
            {shown.map((m, i) => (
              <motion.div
                key={m.moduleId}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.05 + i * 0.05 }}
                className="flex items-center gap-2"
              >
                <span
                  className="size-1.5 shrink-0 rounded-full"
                  style={{ background: MODULE_BY_ID[m.moduleId].color }}
                />
                <span className="flex-1 truncate text-[11.5px] text-ink-2">{m.name}</span>
                <span className="tnum text-[11.5px] font-semibold text-ink">
                  {trim(m.performance * 100)}%
                </span>
                <span
                  className="tnum inline-flex w-13 shrink-0 items-center justify-end gap-0.5 text-[10.5px]"
                  // Inflyatsiyada pasayish yaxshi — belgi teskari o'qiladi
                  style={{
                    color: (
                      MODULE_BY_ID[m.moduleId].lowerIsBetter ? m.yoy <= 0 : m.yoy >= 0
                    )
                      ? "#34d399"
                      : "#fb7185",
                  }}
                >
                  {m.yoy >= 0 ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                  {trim(Math.abs(m.yoy))}%
                </span>
              </motion.div>
            ))}
          </div>

          <div className="mt-3 border-t border-hairline/60 pt-2 text-[10px] text-ink-3">
            Batafsil ko&apos;rish uchun bosing
          </div>
        </div>
      </div>
    </motion.div>
  );
}
