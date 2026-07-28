"use client";

import { AnimatePresence, motion } from "motion/react";
import { Activity, Minimize2, Sparkles, TrendingDown, TrendingUp, X } from "lucide-react";
import { useMemo } from "react";
import { volumeColor } from "@/lib/scale";
import { useDashboard } from "@/lib/store";
import {
  shortUnit,
  useDistrictProfile,
  useMapLayer,
  useOverview,
  useSeries,
  useStatsMeta,
  type MapDistrict,
} from "@/lib/stats";
import type { ChartSpec } from "@/lib/types";
import { cn, compact, trim } from "@/lib/utils";
import { ChartRenderer } from "@/components/charts/ChartRenderer";
import { HeroFigure, StatTile } from "@/components/charts/StatTile";

/**
 * O'ng panel — tanlangan kesimning raqamlari.
 *
 * Manba statistikada reja yo'q, shuning uchun bu yerda "bajarilish %"
 * emas, HAJM va uning o'zgarishi ko'rsatiladi: qiymat, o'tgan yilga
 * nisbatan o'sish, respublikadagi ulush va o'rin.
 */
export function StatsPanel() {
  const { moduleId, year, selectedDistrict, aiCharts, setAiCharts, focusMode, exitFocus } =
    useDashboard();

  const { data: meta } = useStatsMeta();
  const { data: layer } = useMapLayer(moduleId, year || null);
  const { data: overview } = useOverview(year || null);
  const { data: profile } = useDistrictProfile(selectedDistrict, year || null);
  const { data: series } = useSeries(moduleId, selectedDistrict);

  const activeModule = meta?.modules.find((m) => m.id === moduleId);
  const unit = shortUnit(layer?.unit ?? activeModule?.unit ?? "");

  /** Tanlangan kesim: hudud tanlangan bo'lsa uning qatori, aks holda respublika. */
  const cell: MapDistrict | undefined = selectedDistrict
    ? layer?.districts.find((d) => d.district_id === selectedDistrict)
    : undefined;

  const current = series?.points.find((p) => p.year === year);
  const value = selectedDistrict ? (cell?.value ?? 0) : (current?.value ?? layer?.total ?? 0);
  const growth = selectedDistrict ? cell?.yoy : current?.yoy;

  const spark = useMemo(() => (series?.points ?? []).slice(-10).map((p) => p.value), [series]);

  /** Rayonlar — ma'lumoti bor bo'lganlari, hajm bo'yicha tartiblangan. */
  const ranked = useMemo(() => (layer?.districts ?? []).filter((d) => d.value !== null), [layer]);

  const movers = useMemo(
    () => [...ranked.filter((d) => d.yoy !== null)].sort((a, b) => (b.yoy ?? 0) - (a.yoy ?? 0)),
    [ranked],
  );

  const defaultCharts = useMemo<ChartSpec[]>(() => {
    if (!activeModule || !layer) return [];
    const where = profile ? profile.district.name : "Respublika";
    const list: ChartSpec[] = [];

    if (series && series.points.length > 1) {
      list.push({
        id: `dyn-${moduleId}-${selectedDistrict ?? "all"}`,
        kind: "area",
        title: `${activeModule.name} — jıllar boyınsha`,
        subtitle: `${where} · ${series.points[0].year}–${series.points[series.points.length - 1].year}`,
        unit,
        series: [{ key: "value", label: activeModule.short, color: activeModule.color }],
        data: series.points.map((p) => ({ label: p.label, value: p.value })),
      });
    }

    if (profile) {
      // Hududning tarmoq tarkibi — nima bilan yashaydi
      list.push({
        id: `struct-${profile.district.id}-${year}`,
        kind: "bar",
        title: `${profile.district.name} — tarawlar keseginde`,
        subtitle: `${year}-jıl · respublikadaǵı úlesi, %`,
        unit: "%",
        series: [{ key: "value", label: "Úlesi" }],
        data: [...profile.modules]
          .filter((m) => m.share !== null)
          .sort((a, b) => (b.share ?? 0) - (a.share ?? 0))
          .map((m) => ({ label: m.name, value: m.share ?? 0, color: m.color })),
      });
    } else {
      list.push({
        id: `rank-${moduleId}-${year}`,
        kind: "bar",
        title: "Rayonlar boyınsha kólemi",
        subtitle: `${activeModule.name} · ${year}-jıl${layer.partial ? ` (${layer.period_caption})` : ""}`,
        unit,
        series: [{ key: "value", label: activeModule.short }],
        data: ranked.map((d) => ({
          label: d.name,
          value: d.value ?? 0,
          color: volumeColor(d.intensity),
        })),
      });
    }

    if (movers.length > 1) {
      list.push({
        id: `growth-${moduleId}-${year}`,
        kind: "diverging-bar",
        title: "Ósiw pátleri",
        subtitle: `${activeModule.name} · ótken jılǵa salıstırǵanda, %`,
        unit: "%",
        series: [{ key: "value", label: "Ósiw" }],
        data: movers.map((d) => ({
          label: d.name,
          value: d.yoy ?? 0,
          color: (d.yoy ?? 0) >= 0 ? "#2a78d6" : "#d03b3b",
        })),
      });
    }

    return list;
  }, [activeModule, layer, series, profile, moduleId, selectedDistrict, year, unit, ranked, movers]);

  /** Chuqur fokusda panel kengayadi — grafiklar ikki ustunga bo'linadi. */
  const deep = focusMode && !!profile;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-2 px-4 pt-3 pb-2">
        <Activity size={14} className="text-cyan" />
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-[13px] font-bold tracking-tight text-ink">
            {profile ? profile.district.name : "Respublika"} statistikası
          </h2>
          <p className="truncate text-[10.5px] text-ink-3">
            {activeModule?.name ?? "…"} · {year}-jıl
            {layer?.partial ? ` (${layer.period_caption})` : ""}
          </p>
        </div>
        {focusMode && (
          <button
            onClick={exitFocus}
            title="Keńeytilgen kórinisten shıǵıw"
            className="grid size-7 shrink-0 place-items-center rounded-lg text-ink-3 transition hover:bg-raised/60 hover:text-ink"
          >
            <Minimize2 size={14} />
          </button>
        )}
      </div>

      <div className="thin-scroll min-h-0 flex-1 space-y-2.5 overflow-y-auto px-3 pb-4">
        <HeroFigure
          label={activeModule?.name ?? "Kólemi"}
          value={value}
          suffix={unit}
          color={activeModule?.color ?? "#22d3ee"}
          caption={
            profile && cell
              ? `${cell.rank ?? "—"}-orın · respublikanıń ${trim(cell.share ?? 0)}% i · ${profile.district.center}`
              : layer
                ? `${layer.covered} rayon · eń joqarı: ${ranked[0]?.name ?? "—"}`
                : "júklenbekte…"
          }
        />

        <div className={cn("grid gap-2.5", deep ? "grid-cols-4" : "grid-cols-2")}>
          <StatTile
            label={`${activeModule?.short ?? ""} ósiwi`}
            value={growth ?? 0}
            unit="%"
            delta={growth ?? undefined}
            deltaLabel={`${year - 1}-jılǵa`}
            spark={spark}
            accent={activeModule?.color ?? "#0284c7"}
            index={0}
          />
          <StatTile
            label="Ortasha ósiw"
            value={(profile ? profile.avg_growth : overview?.avg_growth) ?? 0}
            unit="%"
            delta={(profile ? profile.avg_growth : overview?.avg_growth) ?? undefined}
            deltaLabel="barlıq tarawlar"
            accent="#34d399"
            index={1}
          />
          <StatTile
            label="Ósip atır"
            value={
              profile
                ? profile.modules.filter((m) => (m.yoy ?? 0) > 0).length
                : movers.filter((d) => (d.yoy ?? 0) > 0).length
            }
            digits={0}
            unit={profile ? "taraw" : "rayon"}
            accent="#2a78d6"
            index={2}
          />
          <StatTile
            label="Tómenlegen"
            value={
              profile
                ? profile.modules.filter((m) => (m.yoy ?? 0) < 0).length
                : movers.filter((d) => (d.yoy ?? 0) < 0).length
            }
            digits={0}
            unit={profile ? "taraw" : "rayon"}
            upIsGood={false}
            accent="#d03b3b"
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
                  {" — tarawlar boyınsha"}
                </span>
                <span className="text-[10.5px] text-ink-3">
                  {profile.district.center} · xalıq {trim(profile.district.population)} mıń
                </span>
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                {profile.modules.map((m, i) => (
                  <motion.div
                    key={m.module}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.04 * i }}
                    className="flex items-center gap-2"
                  >
                    <span className="size-2 shrink-0 rounded-full" style={{ background: m.color }} />
                    <span className="w-20 shrink-0 truncate text-[11px] text-ink-2">{m.name}</span>
                    {/* Chiziq — respublikadagi ulush (17 rayon, o'rtacha ≈ 6%) */}
                    <span className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-abyss/70">
                      <motion.span
                        className="absolute inset-y-0 left-0 rounded-full"
                        style={{ background: m.color }}
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min(100, (m.share ?? 0) * 3)}%` }}
                        transition={{ delay: 0.08 + 0.04 * i, duration: 0.6 }}
                      />
                    </span>
                    <span className="tnum w-11 shrink-0 text-right text-[11px] font-semibold text-ink">
                      {trim(m.share ?? 0)}%
                    </span>
                    <span
                      className="tnum inline-flex w-14 shrink-0 items-center justify-end gap-0.5 text-[10px]"
                      style={{ color: (m.yoy ?? 0) >= 0 ? "#34d399" : "#fb7185" }}
                      title={`${year - 1}-jılǵa salıstırǵanda`}
                    >
                      {m.yoy === null ? (
                        <span className="text-ink-3">—</span>
                      ) : (
                        <>
                          {m.yoy >= 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                          {trim(Math.abs(m.yoy))}%
                        </>
                      )}
                    </span>
                  </motion.div>
                ))}
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
                  AI soraw boyınsha
                </span>
                <button
                  onClick={() => setAiCharts([])}
                  className="grid size-5 place-items-center rounded text-ink-3 transition hover:text-coral"
                  title="Tazalaw"
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

        {/* Eng ko'p pasaygan hududlar */}
        {!profile && movers.length > 0 && (
          <div className="glass rounded-2xl p-3">
            <div className="mb-2 text-[12.5px] font-semibold text-ink">Dıqqat talap etedi</div>
            <div className="space-y-2">
              {movers
                .slice(-4)
                .reverse()
                .map((d, i) => (
                  <motion.div
                    key={d.district_id}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="flex items-center gap-2 rounded-xl bg-abyss/50 px-2.5 py-2 ring-1 ring-edge/40"
                  >
                    <span
                      className="size-2 shrink-0 rounded-full"
                      style={{ background: volumeColor(d.intensity) }}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-[11.5px] font-medium text-ink">{d.name}</div>
                      <div className="truncate text-[10px] text-ink-3">
                        {compact(d.value ?? 0)} {unit} · {d.rank}-orın
                      </div>
                    </div>
                    <span
                      className="tnum text-[11.5px] font-semibold"
                      style={{ color: (d.yoy ?? 0) >= 0 ? "#34d399" : "#fb7185" }}
                    >
                      {(d.yoy ?? 0) > 0 ? "+" : ""}
                      {trim(d.yoy ?? 0)}%
                    </span>
                  </motion.div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
