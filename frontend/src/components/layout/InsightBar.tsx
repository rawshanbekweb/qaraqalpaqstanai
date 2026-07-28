"use client";

import { motion } from "motion/react";
import { ChevronRight, Sparkles } from "lucide-react";
import { useMemo } from "react";
import { useDashboard } from "@/lib/store";
import { useMapLayer, useOverview } from "@/lib/stats";
import { trim } from "@/lib/utils";

/**
 * Dashboard tepasidagi doimiy xulosa.
 *
 * Matn bazadagi raqamlardan deterministik quriladi — model chaqirilmaydi.
 * Sahifa ochilishi bilan ko'rinishi kerak, chat javobini kutib turmaydi.
 */
export function InsightBar() {
  const { moduleId, year, setHighlighted, selectDistrict } = useDashboard();
  const { data: overview } = useOverview(year || null);
  const { data: layer } = useMapLayer(moduleId, year || null);

  const insight = useMemo(() => {
    const withYoy = (layer?.districts ?? []).filter((d) => d.yoy !== null);
    const sorted = [...withYoy].sort((a, b) => (b.yoy ?? 0) - (a.yoy ?? 0));
    const top = sorted[0];
    const bottom = sorted[sorted.length - 1];
    const name = layer?.indicator.module_name ?? "";

    // O'sish faqat bir xil davrlar taqqoslanganda hisoblanadi. 2026 yil
    // yarmi bilan 2025 yilning to'lig'ini solishtirib bo'lmaydi —
    // bunday holda o'sish emas, hajm haqida gapiramiz.
    if (!layer || sorted.length === 0) {
      const leader = layer?.districts.find((d) => d.rank === 1);
      return {
        headline: leader ? `${name}: aldıńǵı — ${leader.name}` : "Maǵlıwmat júklenbekte",
        body: leader
          ? `${trim(leader.share ?? 0)}% úles${layer?.partial ? ` · ${layer.period_caption} juwmaǵı` : ""}`
          : "",
        districts: leader ? [leader.district_id] : [],
        tone: "#22d3ee",
      };
    }

    const declining = sorted.filter((d) => (d.yoy ?? 0) < 0);
    return {
      headline:
        declining.length > 0
          ? `${name}: ${declining.length} rayonda tómenlew`
          : `${name}: barlıq rayonlarda ósiw`,
      body: `Eń tez — ${top.name} (${top.yoy! > 0 ? "+" : ""}${trim(top.yoy!)}%), eń páseń — ${bottom.name} (${bottom.yoy! > 0 ? "+" : ""}${trim(bottom.yoy!)}%). ${
        overview ? `Barlıq tarawlar boyınsha ortasha ósiw ${trim(overview.avg_growth ?? 0)}%.` : ""
      }`,
      districts: (declining.length > 0 ? declining.slice(-3) : sorted.slice(0, 3)).map(
        (d) => d.district_id,
      ),
      tone: declining.length > 0 ? "#fab219" : "#0ca30c",
    };
  }, [layer, overview]);

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
      className="relative z-20 shrink-0 overflow-hidden border-b border-hairline/40 bg-abyss/25 backdrop-blur-2xl backdrop-saturate-150"
    >
      <motion.div
        className="absolute inset-y-0 w-40 opacity-40"
        style={{
          background: `linear-gradient(90deg, transparent, color-mix(in oklab, ${insight.tone} 35%, transparent), transparent)`,
        }}
        animate={{ x: ["-15%", "115%"] }}
        transition={{ duration: 7, repeat: Infinity, ease: "easeInOut", repeatDelay: 4 }}
      />

      <div className="relative flex flex-wrap items-center gap-x-3 gap-y-1.5 px-4 py-2">
        <span className="inline-flex items-center gap-1.5">
          <Sparkles size={13} className="text-violet" />
          <span className="text-[10px] font-semibold tracking-[0.14em] text-violet uppercase">
            Juwmaq
          </span>
        </span>

        <p className="min-w-0 flex-1 text-[12.5px] text-ink">
          <span className="font-semibold">{insight.headline}.</span>{" "}
          <span className="text-ink-3">{insight.body}</span>
        </p>

        <div className="flex items-center gap-1.5">
          {insight.districts.slice(0, 3).map((id) => {
            const d = layer?.districts.find((x) => x.district_id === id);
            return (
              <button
                key={id}
                onClick={() => {
                  selectDistrict(id);
                  setHighlighted(insight.districts);
                }}
                className="rounded-full bg-raised/60 px-2.5 py-1 text-[10.5px] font-medium text-ink-2 ring-1 ring-edge/50 transition hover:text-ink hover:ring-cyan/50"
              >
                {d?.name ?? id}
              </button>
            );
          })}
          {insight.districts.length > 0 && (
            <button
              onClick={() => setHighlighted(insight.districts)}
              className="inline-flex items-center gap-0.5 rounded-full px-2 py-1 text-[10.5px] font-semibold text-cyan transition hover:text-ink"
            >
              Kartada kóriw
              <ChevronRight size={12} />
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
}
