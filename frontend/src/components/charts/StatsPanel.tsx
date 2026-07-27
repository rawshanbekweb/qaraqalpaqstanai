"use client";

import { AnimatePresence, motion } from "motion/react";
import { Activity, Minimize2, Sparkles, TrendingDown, TrendingUp, X } from "lucide-react";
import { useMemo } from "react";
import { DISTRICT_BY_ID } from "@/data/districts";
import { MODULES, MODULE_BY_ID } from "@/data/modules";
import {
  districtProfile,
  districtRanking,
  headlineStats,
  monthlySeries,
  quarterlySeries,
  radarCompare,
  rollup,
  round,
  weakSpots,
  yoyGrowth,
} from "@/lib/analytics";
import { INDICATORS } from "@/data/dataset";
import { performanceColor } from "@/lib/scale";
import { useDashboard } from "@/lib/store";
import type { ChartSpec, ModuleId } from "@/lib/types";
import { cn, trim } from "@/lib/utils";
import { ChartRenderer } from "@/components/charts/ChartRenderer";
import { HeroFigure, StatTile } from "@/components/charts/StatTile";
import { StatusPill } from "@/components/ui/primitives";

export function StatsPanel() {
  const { moduleId, year, selectedDistrict, aiCharts, setAiCharts, focusMode, exitFocus } =
    useDashboard();

  const scope = selectedDistrict ?? "all";
  const stats = useMemo(() => headlineStats(moduleId, year), [moduleId, year]);

  const profile = useMemo(
    () => (selectedDistrict ? districtProfile(selectedDistrict, year) : null),
    [selectedDistrict, year],
  );

  const overall = profile ? profile.overall : stats.performance;

  // Sparkline uchun oylik seriya
  const spark = useMemo(() => {
    const mid: ModuleId = moduleId === "all" ? "industry" : moduleId;
    return monthlySeries(mid, scope, year).map((p) => p.fact);
  }, [moduleId, scope, year]);

  const defaultCharts = useMemo<ChartSpec[]>(() => {
    const mid: ModuleId = moduleId === "all" ? "industry" : moduleId;
    const m = MODULE_BY_ID[mid];
    const where = selectedDistrict ? DISTRICT_BY_ID[selectedDistrict].name : "Respublika";

    const list: ChartSpec[] = [
      {
        id: `dyn-${mid}-${scope}-${year}`,
        kind: "area",
        title: `${m.name} — oylik dinamika`,
        subtitle: `${where}, ${year}-yil`,
        unit: m.unit,
        series: [
          { key: "plan", label: "Reja", color: "#5a6588" },
          { key: "fact", label: "Amalda", color: m.color },
        ],
        data: monthlySeries(mid, scope, year).map((p) => ({
          label: p.label,
          plan: p.plan,
          fact: p.fact,
        })),
      },
    ];

    if (selectedDistrict) {
      list.push({
        id: `cmp-${selectedDistrict}-${year}`,
        kind: "dumbbell",
        title: `${DISTRICT_BY_ID[selectedDistrict].name} — sohalar kesimi`,
        subtitle: "Tuman va respublika o'rtachasi, bajarilish %",
        unit: "%",
        series: [
          { key: "local", label: DISTRICT_BY_ID[selectedDistrict].name, color: "#0891b2" },
          { key: "republic", label: "Respublika o'rtachasi", color: "#8b5cf6" },
        ],
        data: radarCompare(selectedDistrict, year).map((r) => ({
          label: r.label,
          local: r.local,
          republic: r.republic,
        })),
      });
      list.push({
        id: `q-${mid}-${selectedDistrict}-${year}`,
        kind: "grouped-bar",
        title: `${m.name} — choraklar`,
        subtitle: `${where}, ${year}-yil`,
        unit: m.unit,
        series: [
          { key: "plan", label: "Reja", color: "#5a6588" },
          { key: "fact", label: "Amalda", color: m.color },
        ],
        data: quarterlySeries(mid, scope, year).map((q) => ({
          label: q.label,
          plan: q.plan,
          fact: q.fact,
        })),
      });
    } else {
      const rank = districtRanking(moduleId, year);
      list.push({
        id: `rank-${moduleId}-${year}`,
        kind: "diverging-bar",
        title: "Rejadan chetlanish",
        subtitle: `${moduleId === "all" ? "Barcha sohalar" : m.name} · 100% rejaga nisbatan, punkt`,
        unit: "",
        series: [{ key: "value", label: "Chetlanish" }],
        data: rank.map((r) => ({
          label: r.name,
          value: round(r.performance * 100 - 100),
          color: performanceColor(r.performance),
        })),
      });
      list.push({
        id: `struct-${year}`,
        kind: "bar",
        title: "Iqtisodiyot tarkibi",
        subtitle: `${year}-yil · sohalar bo'yicha amaldagi hajm`,
        series: [{ key: "value", label: "Amaldagi hajm" }],
        data: MODULES.filter((x) => x.id !== "inflation")
          .map((x) => {
            const r = rollup(
              INDICATORS.filter((i) => i.moduleId === x.id && i.year === year),
              x.id,
            );
            return { label: x.short, value: Math.round(r.fact), color: x.color };
          })
          .sort((a, b) => b.value - a.value),
      });
    }
    return list;
  }, [moduleId, scope, selectedDistrict, year]);

  const spots = useMemo(
    () =>
      weakSpots(year, {
        moduleId,
        districtId: selectedDistrict ?? "all",
        limit: 4,
      }),
    [moduleId, selectedDistrict, year],
  );

  const growth = useMemo(
    () => yoyGrowth(moduleId === "all" ? "industry" : moduleId, scope),
    [moduleId, scope],
  );

  const inflation = useMemo(
    () =>
      rollup(
        INDICATORS.filter(
          (i) => i.moduleId === "inflation" && i.year === year && (scope === "all" || i.districtId === scope),
        ),
        "inflation",
      ),
    [scope, year],
  );

  const activeModule = moduleId === "all" ? null : MODULE_BY_ID[moduleId];

  /** Chuqur fokusda panel kengayadi — grafiklar ikki ustunga bo'linadi. */
  const deep = focusMode && !!profile;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-2 px-4 pt-3 pb-2">
        <Activity size={14} className="text-cyan" />
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-[13px] font-bold tracking-tight text-ink">
            {profile ? profile.district.name : "Respublika"} statistikasi
          </h2>
          <p className="truncate text-[10.5px] text-ink-3">
            {activeModule ? activeModule.name : "Barcha sohalar"} · {year}-yil
          </p>
        </div>
        {profile ? <StatusPill status={profile.status} /> : null}
        {focusMode && (
          <button
            onClick={exitFocus}
            title="Kengaytirilgan ko'rinishdan chiqish"
            className="grid size-7 shrink-0 place-items-center rounded-lg text-ink-3 transition hover:bg-raised/60 hover:text-ink"
          >
            <Minimize2 size={14} />
          </button>
        )}
      </div>

      <div className="thin-scroll min-h-0 flex-1 space-y-2.5 overflow-y-auto px-3 pb-4">
        <HeroFigure
          label="Reja bajarilishi"
          value={overall * 100}
          color={performanceColor(overall)}
          caption={
            profile
              ? `${profile.criticalCount} ta soha e'tibor talab qiladi · ${profile.district.center}`
              : `${stats.critical} kritik · ${stats.atRisk} xavf ostida · ${stats.records} yozuv`
          }
        />

        <div className={cn("grid gap-2.5", deep ? "grid-cols-4" : "grid-cols-2")}>
          <StatTile
            label={`${activeModule?.short ?? "Sanoat"} o'sishi`}
            value={growth}
            unit="%"
            delta={growth}
            deltaLabel="2025-yilga nisbatan"
            spark={spark}
            accent={activeModule?.color ?? "#0284c7"}
            index={0}
          />
          <StatTile
            label="Inflyatsiya darajasi"
            value={inflation.fact}
            unit="%"
            delta={inflation.fact - inflation.plan}
            deltaLabel="maqsaddan farq"
            upIsGood={false}
            accent="#e11d48"
            index={1}
          />
          <StatTile
            label="Kritik kesimlar"
            value={profile ? profile.modules.filter((m) => m.status === "critical").length : stats.critical}
            digits={0}
            unit="ta"
            upIsGood={false}
            accent="#d03b3b"
            index={2}
          />
          <StatTile
            label="Xavf ostida"
            value={profile ? profile.modules.filter((m) => m.status === "at_risk").length : stats.atRisk}
            digits={0}
            unit="ta"
            upIsGood={false}
            accent="#fab219"
            index={3}
          />
        </div>

        {/* Chuqur fokus — hududning barcha sohalari bir qarashda */}
        <AnimatePresence>
          {deep && profile && (
            <motion.div
              key="module-breakdown"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
              className="glass rounded-2xl p-3"
            >
              <div className="mb-2.5 flex items-center gap-2">
                <span className="text-[12.5px] font-semibold text-ink">
                  {profile.district.name}
                  {" — sohalar bo'yicha"}
                </span>
                <span className="text-[10.5px] text-ink-3">
                  {profile.district.center} · aholi {trim(profile.district.population)} ming
                </span>
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                {profile.modules.map((m, i) => {
                  // Inflyatsiyada pasayish yaxshi — o'sish belgisi teskari o'qiladi
                  const good = MODULE_BY_ID[m.moduleId].lowerIsBetter ? m.yoy <= 0 : m.yoy >= 0;
                  return (
                  <motion.div
                    key={m.moduleId}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.04 * i }}
                    className="flex items-center gap-2"
                  >
                    <span
                      className="size-2 shrink-0 rounded-full"
                      style={{ background: m.color }}
                    />
                    <span className="w-20 shrink-0 truncate text-[11px] text-ink-2">{m.name}</span>
                    {/* Bajarilish chizig'i: 100% shkalaning o'rtasida */}
                    <span className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-abyss/70">
                      <motion.span
                        className="absolute inset-y-0 left-0 rounded-full"
                        style={{ background: performanceColor(m.performance) }}
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min(100, (m.performance / 1.2) * 100)}%` }}
                        transition={{ delay: 0.08 + 0.04 * i, duration: 0.6 }}
                      />
                    </span>
                    <span className="tnum w-11 shrink-0 text-right text-[11px] font-semibold text-ink">
                      {trim(m.performance * 100)}%
                    </span>
                    <span
                      className="tnum inline-flex w-14 shrink-0 items-center justify-end gap-0.5 text-[10px]"
                      style={{ color: good ? "#34d399" : "#fb7185" }}
                      title="2025-yilga nisbatan"
                    >
                      {m.yoy >= 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                      {trim(Math.abs(m.yoy))}%
                    </span>
                  </motion.div>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* AI generatsiya qilgan grafiklar */}
        <AnimatePresence mode="popLayout">
          {aiCharts.length > 0 && (
            <motion.div
              key="ai-charts"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="space-y-2.5"
            >
              <div className="flex items-center gap-2 px-1 pt-1">
                <Sparkles size={12} className="text-violet" />
                <span className="flex-1 text-[10px] font-semibold tracking-wider text-violet uppercase">
                  AI so&apos;rovi bo&apos;yicha
                </span>
                <button
                  onClick={() => setAiCharts([])}
                  className="grid size-5 place-items-center rounded text-ink-3 transition hover:text-coral"
                  title="Tozalash"
                >
                  <X size={12} />
                </button>
              </div>
              <div className={cn(deep && "grid grid-cols-2 gap-2.5")}>
                {aiCharts.map((c) => (
                  <ChartRenderer key={c.id} spec={c} />
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Standart grafiklar */}
        <div className={cn(deep ? "grid grid-cols-2 gap-2.5" : "space-y-2.5")}>
          {defaultCharts.map((c) => (
            <ChartRenderer key={c.id} spec={c} />
          ))}
        </div>

        {/* Muammoli kesimlar ro'yxati */}
        {spots.length > 0 && (
          <div className="glass rounded-2xl p-3">
            <div className="mb-2 text-[12.5px] font-semibold text-ink">E&apos;tibor talab qiladi</div>
            <div className="space-y-2">
              {spots.map((s, i) => (
                <motion.div
                  key={`${s.districtId}-${s.moduleId}`}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex items-center gap-2 rounded-xl bg-abyss/50 px-2.5 py-2 ring-1 ring-edge/40"
                >
                  <span
                    className="size-2 shrink-0 rounded-full"
                    style={{ background: MODULE_BY_ID[s.moduleId].color }}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[11.5px] font-medium text-ink">
                      {s.districtName}
                    </div>
                    <div className="truncate text-[10px] text-ink-3">{s.moduleName}</div>
                  </div>
                  <span className="tnum text-[11.5px] font-semibold text-ink-2">
                    {trim(s.performance * 100)}%
                  </span>
                  <StatusPill status={s.status} />
                </motion.div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
