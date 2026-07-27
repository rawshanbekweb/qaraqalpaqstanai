"use client";

import { motion } from "motion/react";
import { ChevronRight, Sparkles } from "lucide-react";
import { useMemo } from "react";
import { topInsight } from "@/lib/ai-engine";
import { DISTRICT_BY_ID } from "@/data/districts";
import { useDashboard } from "@/lib/store";
import { STATUS_BY_ID } from "@/data/modules";
import { StatusPill } from "@/components/ui/primitives";

/** Dashboard tepasidagi doimiy AI xulosasi (TT 4-bo'lim). */
export function InsightBar() {
  const { year, setHighlighted, selectDistrict, setModule } = useDashboard();
  const insight = useMemo(() => topInsight(year), [year]);
  const color = STATUS_BY_ID[insight.severity].color;

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
          background: `linear-gradient(90deg, transparent, color-mix(in oklab, ${color} 35%, transparent), transparent)`,
        }}
        animate={{ x: ["-15%", "115%"] }}
        transition={{ duration: 7, repeat: Infinity, ease: "easeInOut", repeatDelay: 4 }}
      />

      <div className="relative flex flex-wrap items-center gap-x-3 gap-y-1.5 px-4 py-2">
        <span className="inline-flex items-center gap-1.5">
          <Sparkles size={13} className="text-violet" />
          <span className="text-[10px] font-semibold tracking-[0.14em] text-violet uppercase">
            AI xulosasi
          </span>
        </span>

        <StatusPill status={insight.severity} />

        <p className="min-w-0 flex-1 text-[12.5px] text-ink">
          <span className="font-semibold">{insight.headline}.</span>{" "}
          <span className="text-ink-3">{insight.body}</span>
        </p>

        <div className="flex items-center gap-1.5">
          {insight.districts.slice(0, 3).map((id) => (
            <button
              key={id}
              onClick={() => {
                selectDistrict(id);
                setHighlighted(insight.districts);
                if (insight.moduleId) setModule(insight.moduleId);
              }}
              className="rounded-full bg-raised/60 px-2.5 py-1 text-[10.5px] font-medium text-ink-2 ring-1 ring-edge/50 transition hover:text-ink hover:ring-cyan/50"
            >
              {DISTRICT_BY_ID[id]?.name}
            </button>
          ))}
          <button
            onClick={() => {
              setHighlighted(insight.districts);
              if (insight.moduleId) setModule(insight.moduleId);
            }}
            className="inline-flex items-center gap-0.5 rounded-full px-2 py-1 text-[10.5px] font-semibold text-cyan transition hover:text-ink"
          >
            Xaritada ko&apos;rish
            <ChevronRight size={12} />
          </button>
        </div>
      </div>
    </motion.div>
  );
}
