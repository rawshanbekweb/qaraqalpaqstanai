"use client";

import { AnimatePresence, motion } from "motion/react";
import { ClipboardList, Database, LayoutList, PencilLine, Upload } from "lucide-react";
import { useMemo, useState } from "react";
import { CURRENT_YEAR, INDICATORS } from "@/data/dataset";
import { DISTRICTS, DISTRICT_BY_ID } from "@/data/districts";
import { MODULE_BY_ID, MONTHS_SHORT } from "@/data/modules";
import type { Indicator } from "@/lib/types";
import { trim } from "@/lib/utils";
import { AuroraBackground } from "@/components/ui/AuroraBackground";
import { AdminTopBar } from "@/components/layout/TopBar";
import { Panel, Segmented, StatusPill } from "@/components/ui/primitives";
import { DataEntryForm } from "@/components/admin/DataEntryForm";
import { BulkUpload } from "@/components/admin/BulkUpload";
import { TaskBoard } from "@/components/admin/TaskBoard";

type Tab = "entry" | "bulk" | "tasks" | "records";

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("entry");
  /** Sessiya davomida qo'shilgan yozuvlar (backend ulanguncha xotirada). */
  const [added, setAdded] = useState<Indicator[]>([]);

  const stats = useMemo(
    () => ({
      total: INDICATORS.length + added.length,
      added: added.length,
      districts: DISTRICTS.length,
      year: CURRENT_YEAR,
    }),
    [added.length],
  );

  return (
    <div className="relative min-h-dvh">
      <AuroraBackground />

      <div className="relative z-10 flex min-h-dvh flex-col">
        <AdminTopBar title="Admin panel" />

        <div className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-5">
          {/* Umumiy holat */}
          <div className="mb-4 grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { icon: Database, label: "Bazadagi yozuvlar", value: stats.total, unit: "ta" },
              { icon: Upload, label: "Shu sessiyada qo'shildi", value: stats.added, unit: "ta" },
              { icon: LayoutList, label: "Hududlar", value: stats.districts, unit: "ta" },
              { icon: ClipboardList, label: "Joriy hisobot yili", value: stats.year, unit: "" },
            ].map((s, i) => (
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
                    {s.unit ? trim(s.value, 0) : s.value}
                    {s.unit ? <span className="ml-1 text-[11px] text-ink-3">{s.unit}</span> : null}
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
                  { value: "entry", label: "Ma'lumot kiritish" },
                  { value: "bulk", label: "Fayl orqali yuklash" },
                  { value: "tasks", label: "Topshiriqlar" },
                  { value: "records", label: "Yozuvlar" },
                ]}
              />
              <div className="flex-1" />
              <span className="inline-flex items-center gap-1.5 text-[11px] text-ink-3">
                <PencilLine size={12} />
                Kiritilgan izohlar AI tahliliga kontekst bo&apos;ladi
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
                  {tab === "entry" && (
                    <div className="max-w-2xl">
                      <DataEntryForm onSaved={(rows) => setAdded((p) => [...rows, ...p])} />
                    </div>
                  )}
                  {tab === "bulk" && (
                    <div className="max-w-2xl">
                      <BulkUpload onImported={(rows) => setAdded((p) => [...rows, ...p])} />
                    </div>
                  )}
                  {tab === "tasks" && <TaskBoard />}
                  {tab === "records" && <RecordsTable added={added} />}
                </motion.div>
              </AnimatePresence>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function RecordsTable({ added }: { added: Indicator[] }) {
  const [page, setPage] = useState(0);
  const PER = 25;
  const rows = useMemo(() => [...added, ...INDICATORS].slice(0, 500), [added]);
  const slice = rows.slice(page * PER, page * PER + PER);
  const pages = Math.ceil(rows.length / PER);

  return (
    <div>
      <div className="thin-scroll overflow-x-auto rounded-2xl ring-1 ring-edge/50">
        <table className="w-full min-w-[820px] border-collapse text-[11.5px]">
          <thead className="bg-abyss/70">
            <tr>
              {["Hudud", "Soha", "Davr", "Reja", "Amalda", "Bajarilish", "Status", "Izoh"].map((h) => (
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
            {slice.map((r, i) => {
              const m = MODULE_BY_ID[r.moduleId];
              const ratio = r.plan === 0 ? 1 : r.fact / r.plan;
              return (
                <motion.tr
                  key={r.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: Math.min(i * 0.012, 0.25) }}
                  className="border-t border-hairline/50 transition hover:bg-raised/35"
                >
                  <td className="px-3 py-2 text-ink">{DISTRICT_BY_ID[r.districtId]?.name}</td>
                  <td className="px-3 py-2">
                    <span className="inline-flex items-center gap-1.5 text-ink-2">
                      <span className="size-1.5 rounded-full" style={{ background: m.color }} />
                      {m.short}
                    </span>
                  </td>
                  <td className="tnum px-3 py-2 text-ink-2">
                    {r.month ? `${MONTHS_SHORT[r.month - 1]} ` : ""}
                    {r.year}
                  </td>
                  <td className="tnum px-3 py-2 text-right text-ink-2">{trim(r.plan)}</td>
                  <td className="tnum px-3 py-2 text-right text-ink">{trim(r.fact)}</td>
                  <td className="tnum px-3 py-2 text-right text-ink-2">{trim(ratio * 100)}%</td>
                  <td className="px-3 py-2">
                    <StatusPill status={r.status} />
                  </td>
                  <td className="max-w-[260px] truncate px-3 py-2 text-ink-3" title={r.note}>
                    {r.note ?? "—"}
                  </td>
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-3 flex items-center gap-2">
        <span className="text-[11px] text-ink-3">
          {rows.length} yozuvdan {page * PER + 1}–{Math.min(rows.length, (page + 1) * PER)}
        </span>
        <div className="flex-1" />
        <button
          onClick={() => setPage((p) => Math.max(0, p - 1))}
          disabled={page === 0}
          className="rounded-lg bg-abyss/70 px-3 py-1.5 text-[11.5px] text-ink-2 ring-1 ring-edge/50 transition disabled:opacity-40 enabled:hover:text-ink"
        >
          Oldingi
        </button>
        <button
          onClick={() => setPage((p) => Math.min(pages - 1, p + 1))}
          disabled={page >= pages - 1}
          className="rounded-lg bg-abyss/70 px-3 py-1.5 text-[11.5px] text-ink-2 ring-1 ring-edge/50 transition disabled:opacity-40 enabled:hover:text-ink"
        >
          Keyingi
        </button>
      </div>
    </div>
  );
}
