"use client";

import { AnimatePresence, motion } from "motion/react";
import { AlertTriangle, CheckCircle2, Download, FileSpreadsheet, Upload, X } from "lucide-react";
import Papa from "papaparse";
import { useCallback, useRef, useState } from "react";
import * as XLSX from "xlsx";
import { CURRENT_YEAR, statusFromRatio } from "@/data/dataset";
import { DISTRICTS } from "@/data/districts";
import { MODULES, MODULE_BY_ID } from "@/data/modules";
import type { Indicator, ModuleId, StatusId } from "@/lib/types";
import { cn, uid } from "@/lib/utils";
import { Button } from "@/components/ui/primitives";

/** Shablondagi ustunlar — Excel/CSV ikkalasi uchun bir xil. */
const COLUMNS = ["modul", "hudud", "yil", "oy", "reja", "amalda", "izoh"] as const;

interface ParseResult {
  rows: Indicator[];
  errors: string[];
  fileName: string;
}

const DISTRICT_LOOKUP = new Map<string, string>();
for (const d of DISTRICTS) {
  DISTRICT_LOOKUP.set(norm(d.name), d.id);
  DISTRICT_LOOKUP.set(norm(d.id), d.id);
  DISTRICT_LOOKUP.set(norm(d.nameRu), d.id);
}

const MODULE_LOOKUP = new Map<string, ModuleId>();
for (const m of MODULES) {
  MODULE_LOOKUP.set(norm(m.id), m.id);
  MODULE_LOOKUP.set(norm(m.name), m.id);
  MODULE_LOOKUP.set(norm(m.short), m.id);
}

function norm(s: string) {
  return String(s ?? "")
    .toLowerCase()
    .replace(/[ʻʼ‘’`']/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function num(v: unknown): number {
  const n = Number(String(v ?? "").replace(/\s/g, "").replace(",", "."));
  return Number.isFinite(n) ? n : NaN;
}

/** Bir qator obyektni Indicator'ga aylantiradi; xatolarni matn sifatida qaytaradi. */
function toIndicator(raw: Record<string, unknown>, index: number): Indicator | string {
  const line = index + 2; // sarlavha qatorini hisobga olgan holda
  const get = (k: string) => {
    const key = Object.keys(raw).find((x) => norm(x) === k);
    return key ? raw[key] : undefined;
  };

  const moduleId = MODULE_LOOKUP.get(norm(String(get("modul"))));
  if (!moduleId) return `${line}-qator: "modul" ustuni tanilmadi (${get("modul") ?? "bo'sh"})`;

  const districtId = DISTRICT_LOOKUP.get(norm(String(get("hudud"))));
  if (!districtId) return `${line}-qator: "hudud" ustuni tanilmadi (${get("hudud") ?? "bo'sh"})`;

  const year = num(get("yil")) || CURRENT_YEAR;
  const month = num(get("oy"));
  if (!(month >= 1 && month <= 12)) return `${line}-qator: "oy" 1–12 oralig'ida bo'lishi kerak`;

  const plan = num(get("reja"));
  const fact = num(get("amalda"));
  if (!Number.isFinite(plan) || !Number.isFinite(fact))
    return `${line}-qator: "reja" yoki "amalda" son emas`;

  const meta = MODULE_BY_ID[moduleId];
  const ratio = plan === 0 ? 1 : fact / plan;
  const status: StatusId = statusFromRatio(ratio, meta.lowerIsBetter);
  const note = String(get("izoh") ?? "").trim();

  return {
    id: uid("imp"),
    moduleId,
    districtId,
    year,
    month,
    quarter: Math.ceil(month / 3),
    plan,
    fact,
    unit: meta.unit,
    status,
    note: note || undefined,
  };
}

export function BulkUpload({ onImported }: { onImported: (rows: Indicator[]) => void }) {
  const [result, setResult] = useState<ParseResult | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleRows = useCallback((records: Record<string, unknown>[], fileName: string) => {
    const rows: Indicator[] = [];
    const errors: string[] = [];
    records.forEach((r, i) => {
      const res = toIndicator(r, i);
      if (typeof res === "string") errors.push(res);
      else rows.push(res);
    });
    setResult({ rows, errors: errors.slice(0, 8), fileName });
  }, []);

  const readFile = useCallback(
    (file: File) => {
      const isExcel = /\.(xlsx|xls)$/i.test(file.name);
      if (isExcel) {
        const reader = new FileReader();
        reader.onload = (e) => {
          const wb = XLSX.read(e.target?.result, { type: "array" });
          const sheet = wb.Sheets[wb.SheetNames[0]];
          const json = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet, { defval: "" });
          handleRows(json, file.name);
        };
        reader.readAsArrayBuffer(file);
      } else {
        Papa.parse<Record<string, unknown>>(file, {
          header: true,
          skipEmptyLines: true,
          complete: (res) => handleRows(res.data, file.name),
        });
      }
    },
    [handleRows],
  );

  function downloadTemplate() {
    const sample = [
      {
        modul: "agriculture",
        hudud: "Amudaryo",
        yil: CURRENT_YEAR,
        oy: 1,
        reja: 1250.5,
        amalda: 890.2,
        izoh: "Sug'orish suvi limiti qisqartirildi",
      },
      {
        modul: "export",
        hudud: "Beruniy",
        yil: CURRENT_YEAR,
        oy: 1,
        reja: 95,
        amalda: 68.4,
        izoh: "Logistika narxlari oshdi",
      },
    ];
    const ws = XLSX.utils.json_to_sheet(sample, { header: [...COLUMNS] });
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Ko'rsatkichlar");
    XLSX.writeFile(wb, "qoraqalpogiston-shablon.xlsx");
  }

  return (
    <div className="space-y-3.5">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const f = e.dataTransfer.files?.[0];
          if (f) readFile(f);
        }}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "relative cursor-pointer rounded-2xl border border-dashed px-5 py-8 text-center transition",
          dragging
            ? "border-cyan/70 bg-cyan/8"
            : "border-edge/70 bg-abyss/40 hover:border-cyan/50 hover:bg-abyss/60",
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) readFile(f);
            e.target.value = "";
          }}
        />
        <motion.div
          animate={dragging ? { y: -4, scale: 1.05 } : { y: 0, scale: 1 }}
          className="mx-auto mb-3 grid size-12 place-items-center rounded-2xl bg-gradient-to-br from-cyan/20 to-violet/20 ring-1 ring-cyan/30"
        >
          <Upload size={20} className="text-cyan" />
        </motion.div>
        <div className="text-[13px] font-semibold text-ink">
          Excel yoki CSV faylni bu yerga tashlang
        </div>
        <div className="mt-1 text-[11.5px] text-ink-3">
          Ustunlar: {COLUMNS.join(" · ")}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" type="button" onClick={downloadTemplate}>
          <Download size={14} />
          Shablonni yuklab olish
        </Button>
        <span className="text-[11px] text-ink-3">
          .xlsx shabloni to&apos;g&apos;ri ustun nomlari bilan tayyorlanadi
        </span>
      </div>

      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            className="rounded-2xl bg-abyss/60 p-3.5 ring-1 ring-edge/50"
          >
            <div className="mb-3 flex items-center gap-2">
              <FileSpreadsheet size={15} className="text-cyan" />
              <span className="min-w-0 flex-1 truncate text-[12.5px] font-semibold text-ink">
                {result.fileName}
              </span>
              <button
                onClick={() => setResult(null)}
                className="grid size-6 place-items-center rounded-md text-ink-3 hover:text-coral"
              >
                <X size={13} />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              <div className="rounded-xl bg-mint/8 px-3 py-2.5 ring-1 ring-mint/25">
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 size={13} className="text-mint" />
                  <span className="text-[10.5px] text-ink-3">O&apos;qildi</span>
                </div>
                <div className="tnum mt-0.5 text-xl font-semibold text-ink">
                  {result.rows.length}
                </div>
              </div>
              <div
                className={cn(
                  "rounded-xl px-3 py-2.5 ring-1",
                  result.errors.length
                    ? "bg-amber/8 ring-amber/25"
                    : "bg-abyss/50 ring-edge/40",
                )}
              >
                <div className="flex items-center gap-1.5">
                  <AlertTriangle
                    size={13}
                    className={result.errors.length ? "text-amber" : "text-ink-3"}
                  />
                  <span className="text-[10.5px] text-ink-3">Xatolar</span>
                </div>
                <div className="tnum mt-0.5 text-xl font-semibold text-ink">
                  {result.errors.length}
                </div>
              </div>
            </div>

            {result.errors.length > 0 && (
              <ul className="mt-3 space-y-1">
                {result.errors.map((e, i) => (
                  <li key={i} className="text-[11px] text-amber">
                    · {e}
                  </li>
                ))}
              </ul>
            )}

            {result.rows.length > 0 && (
              <Button
                type="button"
                className="mt-3 w-full"
                onClick={() => {
                  onImported(result.rows);
                  setResult(null);
                }}
              >
                <Upload size={14} />
                {result.rows.length} ta yozuvni bazaga import qilish
              </Button>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
