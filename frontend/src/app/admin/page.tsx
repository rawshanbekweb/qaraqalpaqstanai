"use client";

import { AnimatePresence, motion } from "motion/react";
import {
  AlertTriangle,
  ClipboardList,
  Database,
  LayoutList,
  Loader2,
  MapPin,
  Upload,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { fetchSummary, adminConfigured, type AdminSummary } from "@/lib/admin";
import { useStatsMeta } from "@/lib/stats";
import { trim } from "@/lib/utils";
import { AuroraBackground } from "@/components/ui/AuroraBackground";
import { AdminTopBar } from "@/components/layout/TopBar";
import { Panel, Segmented } from "@/components/ui/primitives";
import { IndicatorBrowser } from "@/components/admin/IndicatorBrowser";
import { StatUpload } from "@/components/admin/StatUpload";
import { TaskBoard } from "@/components/admin/TaskBoard";

type Tab = "state" | "upload" | "indicators" | "tasks";

/**
 * Admin panel.
 *
 * Ma'lumot Excel'dan yuklanadi, shuning uchun bu yerda qo'lda qiymat
 * kiritish yo'q. Adminning uch ishi bor: bazaning holatini ko'rish,
 * yangi fayl yuklash va qaysi ko'rsatkich qaysi tayanch sohani
 * ta'minlashini belgilash.
 */
export default function AdminPage() {
  const configured = adminConfigured();
  const [tab, setTab] = useState<Tab>("state");
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [loading, setLoading] = useState(configured);
  const { data: meta } = useStatsMeta();

  const reload = useCallback(() => {
    if (!configured) return;
    fetchSummary()
      .then((data) => {
        setSummary(data);
        setFetchError(null);
      })
      .catch((e: Error) => setFetchError(e.message))
      .finally(() => setLoading(false));
  }, [configured]);

  useEffect(reload, [reload]);

  const error = configured
    ? fetchError
    : "NEXT_PUBLIC_API_URL sazlanbaǵan — admin panel serversiz islemeydi";

  const tiles = [
    { icon: Database, label: "Ólshemler", value: summary?.observations ?? 0 },
    { icon: LayoutList, label: "Kórsetkishler", value: summary?.indicators ?? 0 },
    { icon: MapPin, label: "Rayon kesimi bar", value: summary?.with_districts ?? 0 },
    { icon: ClipboardList, label: "Aqırǵı jıl", value: summary?.latest_year ?? 0, plain: true },
  ];

  return (
    <div className="relative min-h-dvh">
      <AuroraBackground />

      <div className="relative z-10 flex min-h-dvh flex-col">
        <AdminTopBar title="Admin panel" />

        <div className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-5">
          {error && (
            <div className="mb-4 flex items-start gap-2 rounded-2xl bg-crimson/12 px-4 py-3 ring-1 ring-crimson/30">
              <AlertTriangle size={15} className="mt-0.5 shrink-0 text-crimson" />
              <span className="text-[12px] leading-relaxed text-coral">{error}</span>
            </div>
          )}

          {/* Bazaning holati */}
          <div className="mb-4 grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
            {tiles.map((s, i) => (
              <motion.div
                key={s.label}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06 }}
                className="glass flex items-center gap-3 rounded-2xl px-4 py-3"
              >
                <div className="grid size-9 shrink-0 place-items-center rounded-xl bg-raised/70 text-cyan ring-1 ring-edge/60">
                  <s.icon size={16} />
                </div>
                <div className="min-w-0">
                  <div className="truncate text-[10.5px] text-ink-3">{s.label}</div>
                  <div className="text-[19px] leading-tight font-semibold text-ink">
                    {loading && !summary ? (
                      <Loader2 size={16} className="animate-spin text-ink-3" />
                    ) : s.plain ? (
                      s.value
                    ) : (
                      trim(s.value, 0)
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          <Panel glow className="overflow-hidden">
            <div className="flex flex-wrap items-center gap-3 border-b border-hairline/70 px-4 py-3">
              <Segmented<Tab>
                layoutId="admin-tab"
                value={tab}
                onChange={setTab}
                options={[
                  { value: "state", label: "Baza halatı" },
                  { value: "upload", label: "Excel júklew" },
                  { value: "indicators", label: "Kórsetkishler" },
                  { value: "tasks", label: "Tapsırmalar" },
                ]}
              />
              <div className="flex-1" />
              <span className="text-[11px] text-ink-3">
                {summary
                  ? `${summary.years[0]}–${summary.years[summary.years.length - 1]} · ${summary.districts} rayon`
                  : ""}
              </span>
            </div>

            <div className="p-4">
              <AnimatePresence mode="wait">
                <motion.div
                  key={tab}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.25 }}
                >
                  {tab === "state" && <BaseState summary={summary} />}

                  {tab === "upload" && (
                    <div className="max-w-2xl">
                      <StatUpload
                        sourceDirs={summary?.source_dirs ?? []}
                        onDone={reload}
                      />
                    </div>
                  )}

                  {tab === "indicators" && (
                    <IndicatorBrowser
                      categories={meta?.categories ?? []}
                      modules={summary?.modules ?? []}
                      onChanged={reload}
                    />
                  )}

                  {tab === "tasks" && <TaskBoard />}
                </motion.div>
              </AnimatePresence>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function BaseState({ summary }: { summary: AdminSummary | null }) {
  if (!summary) {
    return <div className="py-8 text-center text-[12px] text-ink-3">Maǵlıwmat joq</div>;
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
      <div>
        <div className="mb-2 text-[12.5px] font-semibold text-ink">Bólimler boyınsha</div>
        <div className="thin-scroll overflow-x-auto rounded-2xl ring-1 ring-edge/50">
          <table className="w-full min-w-[420px] border-collapse text-[11.5px]">
            <thead className="bg-abyss/70">
              <tr>
                {["Bólim", "Kórsetkish", "Ólshem"].map((h) => (
                  <th
                    key={h}
                    className="px-3 py-2.5 text-left text-[10px] font-semibold tracking-wider text-ink-3 uppercase"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {summary.categories.map((c) => (
                <tr key={c.id} className="border-t border-hairline/50">
                  <td className="px-3 py-2">
                    <span className="inline-flex items-center gap-1.5 text-ink">
                      <span className="size-1.5 rounded-full" style={{ background: c.color }} />
                      {c.name}
                    </span>
                    <div className="text-[10px] text-ink-3">{c.source_dir}</div>
                  </td>
                  <td className="tnum px-3 py-2 text-right text-ink-2">{c.indicators}</td>
                  <td className="tnum px-3 py-2 text-right text-ink">{trim(c.observations, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <div className="mb-2 text-[12.5px] font-semibold text-ink">
          Karta isletetuǵın tiykarǵı kórsetkishler
        </div>
        <div className="space-y-2">
          {summary.modules.map((m) => (
            <div key={m.id} className="rounded-xl bg-abyss/50 px-3 py-2.5 ring-1 ring-edge/40">
              <div className="flex items-center gap-2">
                <span className="size-2 shrink-0 rounded-full" style={{ background: m.color }} />
                <span className="text-[12px] font-semibold text-ink">{m.name}</span>
                <span className="ml-auto text-[10px] text-ink-3">#{m.indicator_id}</span>
              </div>
              <div className="mt-1 truncate text-[10.5px] text-ink-3" title={m.indicator_name}>
                {m.indicator_name}
              </div>
              <div className="truncate text-[10px] text-ink-3">{m.unit}</div>
            </div>
          ))}
        </div>
        <p className="mt-3 flex items-start gap-1.5 text-[10.5px] leading-relaxed text-ink-3">
          <Upload size={12} className="mt-0.5 shrink-0" />
          Tiykarǵı kórsetkish avtomat saylanadı: rayon kesimi bar, kólemdi ólsheytuǵın hám
          ólshemi kóbirek bolǵanı. Basqasın qoyıw ushın «Kórsetkishler» bóliminde házirgisiniń
          biriktiriwin úziń.
        </p>
      </div>
    </div>
  );
}
