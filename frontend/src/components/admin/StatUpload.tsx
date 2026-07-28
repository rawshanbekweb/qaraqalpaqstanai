"use client";

import { AnimatePresence, motion } from "motion/react";
import { AlertTriangle, CheckCircle2, FileSpreadsheet, Loader2, Upload, X } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { uploadWorkbook, type UploadResult } from "@/lib/admin";
import { clearStatsCache } from "@/lib/stats";
import { cn } from "@/lib/utils";
import { Button, Field, Select } from "@/components/ui/primitives";

/**
 * Statistika Excel faylini bazaga yuklash.
 *
 * Fayl brauzerda O'QILMAYDI: manba fayllarning tuzilishi murakkab
 * (sarlavha qatori 10-qatorgacha bo'lishi mumkin, bir varaqda ustma-ust
 * jadvallar, ierarxik qatorlar), buni serverdagi parser hal qiladi.
 * Ikkinchi, soddalashtirilgan nusxa yozilsa natijalar farq qilardi.
 */
export function StatUpload({
  sourceDirs,
  onDone,
}: {
  sourceDirs: string[];
  onDone: () => void;
}) {
  const [category, setCategory] = useState(sourceDirs[0] ?? "");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const pick = useCallback((f: File | undefined) => {
    if (!f) return;
    setFile(f);
    setResult(null);
    setError(null);
  }, []);

  async function send() {
    if (!file || !category) return;
    setBusy(true);
    setError(null);
    try {
      const res = await uploadWorkbook(file, category);
      // Yuklashdan keyin panel eski javoblarni ko'rsatmasin
      clearStatsCache();
      setResult(res);
      setFile(null);
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Júklew ámelge aspadı");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3.5">
      <Field
        label="Bólim"
        hint="Fayl qaysı bólimge tiyisli ekeni atınan bilinbeydi — ashıq saylanadı"
      >
        <Select value={category} onChange={(e) => setCategory(e.target.value)}>
          {sourceDirs.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </Select>
      </Field>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          pick(e.dataTransfer.files?.[0]);
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
          accept=".xlsx,.xls"
          className="hidden"
          onChange={(e) => {
            pick(e.target.files?.[0]);
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
          {file ? file.name : "Excel faydı usı jerge taslań"}
        </div>
        <div className="mt-1 text-[11.5px] text-ink-3">
          .xlsx yamasa .xls · barlıq betler oqıladı
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button type="button" onClick={send} disabled={!file || busy}>
          {busy ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
          {busy ? "Júklenbekte…" : "Bazaǵa júklew"}
        </Button>
        <span className="text-[11px] text-ink-3">
          Tek ǵana usı fayl tiygen kórsetkishler jańalanadı
        </span>
      </div>

      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-start gap-2 rounded-xl bg-crimson/12 px-3 py-2.5 ring-1 ring-crimson/30"
          >
            <AlertTriangle size={14} className="mt-0.5 shrink-0 text-crimson" />
            <span className="text-[11.5px] leading-relaxed text-coral">{error}</span>
          </motion.div>
        )}

        {result && (
          <motion.div
            key={result.file}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            className="rounded-2xl bg-abyss/60 p-3.5 ring-1 ring-edge/50"
          >
            <div className="mb-3 flex items-center gap-2">
              <FileSpreadsheet size={15} className="text-cyan" />
              <span className="min-w-0 flex-1 truncate text-[12.5px] font-semibold text-ink">
                {result.file}
              </span>
              <button
                onClick={() => setResult(null)}
                className="grid size-6 place-items-center rounded-md text-ink-3 hover:text-coral"
              >
                <X size={13} />
              </button>
            </div>

            <div className="grid grid-cols-3 gap-2.5">
              <Tile label="Kórsetkish" value={result.korsetkish} tone="mint" />
              <Tile label="Ólshem" value={result.olshov} tone="mint" />
              <Tile
                label="Ótkerip jiberildi"
                value={result.otkazib_yuborilgan}
                tone={result.otkazib_yuborilgan ? "amber" : "flat"}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Tile({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "mint" | "amber" | "flat";
}) {
  const styles = {
    mint: "bg-mint/8 ring-mint/25",
    amber: "bg-amber/8 ring-amber/25",
    flat: "bg-abyss/50 ring-edge/40",
  }[tone];
  const icon = tone === "amber" ? AlertTriangle : CheckCircle2;
  const Icon = icon;
  return (
    <div className={cn("rounded-xl px-3 py-2.5 ring-1", styles)}>
      <div className="flex items-center gap-1.5">
        <Icon
          size={13}
          className={tone === "amber" ? "text-amber" : tone === "mint" ? "text-mint" : "text-ink-3"}
        />
        <span className="truncate text-[10.5px] text-ink-3">{label}</span>
      </div>
      <div className="tnum mt-0.5 text-xl font-semibold text-ink">{value}</div>
    </div>
  );
}
