"use client";

import { motion } from "motion/react";
import { LayoutGrid, LogOut, MapPin, Radio, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { BASE_YEAR, CURRENT_YEAR } from "@/data/dataset";
import { DISTRICT_BY_ID } from "@/data/districts";
import { MODULES, STATUSES } from "@/data/modules";
import { useDashboard } from "@/lib/store";
import type { ModuleId, StatusId } from "@/lib/types";
import { clearSession, getSession } from "@/lib/session";
import { Segmented } from "@/components/ui/primitives";
import { useSyncExternalStore } from "react";

/** useSyncExternalStore uchun o'zgarmas "obuna bo'lmaslik" funksiyasi. */
const NO_SUBSCRIBE = () => () => {};

/**
 * Yagona filtr qatori — u qamrab olgan HAMMA narsa (xarita, statistikalar,
 * grafiklar) shu bir kesimga qarab qayta chiziladi. Kartochkalar ichida
 * alohida filtr yo'q.
 */
export function TopBar() {
  const {
    moduleId,
    setModule,
    status,
    setStatus,
    period,
    setPeriod,
    year,
    setYear,
    selectedDistrict,
    selectDistrict,
  } = useDashboard();
  const router = useRouter();
  // Sessiya cookie'da — serverda o'qilmaydi, shuning uchun tashqi "store" sifatida
  const role = useSyncExternalStore(NO_SUBSCRIBE, () => getSession()?.role ?? null, () => null);

  return (
    <header className="relative z-30 flex shrink-0 flex-wrap items-center gap-3 border-b border-hairline/40 bg-abyss/35 px-4 py-2.5 backdrop-blur-2xl backdrop-saturate-150">
      {/* Brend */}
      <Link href="/" className="flex shrink-0 items-center gap-2.5">
        <div className="relative grid size-9 place-items-center rounded-xl bg-gradient-to-br from-cyan via-iris to-magenta">
          <Radio size={17} className="text-void" strokeWidth={2.4} />
          <motion.span
            className="absolute inset-0 rounded-xl ring-2 ring-cyan/60"
            animate={{ scale: [1, 1.35], opacity: [0.5, 0] }}
            transition={{ duration: 2.6, repeat: Infinity }}
          />
        </div>
        <div className="hidden sm:block">
          <div className="text-[13px] leading-tight font-bold tracking-tight text-ink">
            Qoraqalpog&apos;iston <span className="text-gradient">Monitoring</span>
          </div>
          <div className="text-[10px] leading-tight text-ink-3">
            Iqtisodiy monitoring va AI analitika
          </div>
        </div>
      </Link>

      <div className="mx-1 hidden h-8 w-px bg-hairline lg:block" />

      {/* Filtrlar */}
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
        <Segmented<ModuleId | "all">
          layoutId="module-filter"
          size="sm"
          value={moduleId}
          onChange={setModule}
          options={[
            { value: "all", label: "Barchasi" },
            ...MODULES.map((m) => ({ value: m.id, label: m.short, color: m.color })),
          ]}
        />

        <Segmented<StatusId | "all">
          layoutId="status-filter"
          size="sm"
          value={status}
          onChange={setStatus}
          options={[
            { value: "all", label: "Har qanday" },
            ...STATUSES.map((s) => ({ value: s.id, label: s.name, color: s.color })),
          ]}
        />

        <Segmented<"month" | "quarter" | "year">
          layoutId="period-filter"
          size="sm"
          value={period}
          onChange={setPeriod}
          options={[
            { value: "month", label: "Oy" },
            { value: "quarter", label: "Chorak" },
            { value: "year", label: "Yil" },
          ]}
        />

        <Segmented<string>
          layoutId="year-filter"
          size="sm"
          value={String(year)}
          onChange={(v) => setYear(Number(v))}
          options={[
            { value: String(BASE_YEAR), label: String(BASE_YEAR) },
            { value: String(CURRENT_YEAR), label: String(CURRENT_YEAR) },
          ]}
        />

        {selectedDistrict && (
          <motion.button
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            onClick={() => selectDistrict(null)}
            className="inline-flex items-center gap-1.5 rounded-full bg-cyan/12 px-3 py-1.5 text-[11px] font-semibold text-cyan ring-1 ring-cyan/35 transition hover:bg-cyan/20"
          >
            <MapPin size={11} />
            {DISTRICT_BY_ID[selectedDistrict]?.name}
            <span className="text-cyan/60">✕</span>
          </motion.button>
        )}
      </div>

      {/* O'ng tomon */}
      <div className="flex shrink-0 items-center gap-2">
        {role === "admin" && (
          <Link
            href="/admin"
            className="inline-flex items-center gap-1.5 rounded-xl bg-abyss/70 px-3 py-2 text-[11.5px] font-semibold text-ink-2 ring-1 ring-edge/60 transition hover:text-ink hover:ring-cyan/50"
          >
            <ShieldCheck size={13} />
            <span className="hidden md:inline">Admin panel</span>
          </Link>
        )}
        <button
          onClick={() => {
            clearSession();
            router.push("/login");
          }}
          className="grid size-9 place-items-center rounded-xl bg-abyss/70 text-ink-3 ring-1 ring-edge/60 transition hover:text-coral"
          title="Chiqish"
        >
          <LogOut size={14} />
        </button>
      </div>
    </header>
  );
}

export function AdminTopBar({ title }: { title: string }) {
  const router = useRouter();
  return (
    <header className="relative z-30 flex shrink-0 items-center gap-3 border-b border-hairline/70 bg-abyss/60 px-4 py-2.5 backdrop-blur-xl">
      <Link href="/" className="flex items-center gap-2.5">
        <div className="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-cyan via-iris to-magenta">
          <Radio size={17} className="text-void" strokeWidth={2.4} />
        </div>
        <div>
          <div className="text-[13px] leading-tight font-bold tracking-tight text-ink">{title}</div>
          <div className="text-[10px] leading-tight text-ink-3">
            Qoraqalpog&apos;iston Respublikasi
          </div>
        </div>
      </Link>
      <div className="flex-1" />
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 rounded-xl bg-abyss/70 px-3 py-2 text-[11.5px] font-semibold text-ink-2 ring-1 ring-edge/60 transition hover:text-ink hover:ring-cyan/50"
      >
        <LayoutGrid size={13} />
        <span className="hidden sm:inline">Dashboard</span>
      </Link>
      <button
        onClick={() => {
          clearSession();
          router.push("/login");
        }}
        className="grid size-9 place-items-center rounded-xl bg-abyss/70 text-ink-3 ring-1 ring-edge/60 transition hover:text-coral"
        title="Chiqish"
      >
        <LogOut size={14} />
      </button>
    </header>
  );
}
