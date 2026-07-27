"use client";

import { AnimatePresence, motion } from "motion/react";
import { Check, Loader2, Save } from "lucide-react";
import { useMemo, useState } from "react";
import { BASE_YEAR, CURRENT_YEAR, statusFromRatio } from "@/data/dataset";
import { DISTRICTS } from "@/data/districts";
import { MODULES, MODULE_BY_ID, MONTHS_UZ, STATUS_BY_ID } from "@/data/modules";
import type { Indicator, ModuleId, StatusId } from "@/lib/types";
import { performanceColor } from "@/lib/scale";
import { trim, uid } from "@/lib/utils";
import { Button, Field, Input, Meter, Select, StatusPill, Textarea } from "@/components/ui/primitives";

/** TT 2.1 — qo'lda ma'lumot kiritish formasi. */
export function DataEntryForm({ onSaved }: { onSaved: (rows: Indicator[]) => void }) {
  const [moduleId, setModuleId] = useState<ModuleId>("agriculture");
  const [districtId, setDistrictId] = useState(DISTRICTS[0].id);
  const [year, setYear] = useState(CURRENT_YEAR);
  const [month, setMonth] = useState(7);
  const [plan, setPlan] = useState("");
  const [fact, setFact] = useState("");
  const [note, setNote] = useState("");
  const [manualStatus, setManualStatus] = useState<StatusId | "auto">("auto");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const meta = MODULE_BY_ID[moduleId];
  const planNum = Number(plan.replace(",", "."));
  const factNum = Number(fact.replace(",", "."));
  const ratio = planNum > 0 ? factNum / planNum : 0;
  const valid = plan !== "" && fact !== "" && Number.isFinite(planNum) && Number.isFinite(factNum);

  const autoStatus = useMemo<StatusId>(
    () => (valid ? statusFromRatio(ratio, meta.lowerIsBetter) : "in_progress"),
    [ratio, meta.lowerIsBetter, valid],
  );
  const effectiveStatus = manualStatus === "auto" ? autoStatus : manualStatus;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!valid) return;
    setBusy(true);
    await new Promise((r) => setTimeout(r, 500));

    const row: Indicator = {
      id: uid("ind"),
      moduleId,
      districtId,
      year,
      month,
      quarter: Math.ceil(month / 3),
      plan: planNum,
      fact: factNum,
      unit: meta.unit,
      status: effectiveStatus,
      note: note.trim() || undefined,
    };
    onSaved([row]);
    setBusy(false);
    setDone(true);
    setPlan("");
    setFact("");
    setNote("");
    setTimeout(() => setDone(false), 2200);
  }

  return (
    <form onSubmit={submit} className="space-y-3.5">
      <div className="grid gap-3.5 sm:grid-cols-2">
        <Field label="Modul / soha">
          <Select value={moduleId} onChange={(e) => setModuleId(e.target.value as ModuleId)}>
            {MODULES.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </Select>
        </Field>

        <Field label="Hudud">
          <Select value={districtId} onChange={(e) => setDistrictId(e.target.value)}>
            {DISTRICTS.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </Select>
        </Field>

        <Field label="Yil">
          <Select value={year} onChange={(e) => setYear(Number(e.target.value))}>
            {[BASE_YEAR, CURRENT_YEAR].map((y) => (
              <option key={y} value={y}>
                {y}-yil
              </option>
            ))}
          </Select>
        </Field>

        <Field label="Oy">
          <Select value={month} onChange={(e) => setMonth(Number(e.target.value))}>
            {MONTHS_UZ.map((m, i) => (
              <option key={m} value={i + 1}>
                {m} ({Math.ceil((i + 1) / 3)}-chorak)
              </option>
            ))}
          </Select>
        </Field>

        <Field label={`Reja (KPI), ${meta.unit}`}>
          <Input
            value={plan}
            onChange={(e) => setPlan(e.target.value)}
            inputMode="decimal"
            placeholder="0"
            required
          />
        </Field>

        <Field label={`Amalda, ${meta.unit}`}>
          <Input
            value={fact}
            onChange={(e) => setFact(e.target.value)}
            inputMode="decimal"
            placeholder="0"
            required
          />
        </Field>
      </div>

      {/* Bajarilishning jonli ko'rsatkichi */}
      <AnimatePresence>
        {valid && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="rounded-xl bg-abyss/60 px-3.5 py-3 ring-1 ring-edge/50">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-[11px] text-ink-3">
                  Reja bajarilishi
                  {meta.lowerIsBetter ? " (past ko'rsatkich — yaxshi)" : ""}
                </span>
                <span
                  className="tnum text-sm font-bold"
                  style={{ color: performanceColor(meta.lowerIsBetter ? 1 / (ratio || 1) : ratio) }}
                >
                  {trim(ratio * 100)}%
                </span>
              </div>
              <Meter
                value={meta.lowerIsBetter ? 1 / (ratio || 1) : ratio}
                color={performanceColor(meta.lowerIsBetter ? 1 / (ratio || 1) : ratio)}
              />
              <div className="mt-2 flex items-center gap-2">
                <span className="text-[10.5px] text-ink-3">Avtomatik status:</span>
                <StatusPill status={autoStatus} />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <Field label="Status" hint="Avtomatik holat reja/amalda nisbatidan hisoblanadi">
        <Select
          value={manualStatus}
          onChange={(e) => setManualStatus(e.target.value as StatusId | "auto")}
        >
          <option value="auto">Avtomatik ({STATUS_BY_ID[autoStatus].name})</option>
          {Object.values(STATUS_BY_ID).map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </Select>
      </Field>

      <Field
        label="Izoh / muammo tavsifi"
        hint="Bu matn AI tahliliga kontekst sifatida uzatiladi — sababni yozing"
      >
        <Textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={3}
          placeholder="Masalan: Eksport hajmi 12% ga kamaydi, sababi logistika narxlari oshgani."
        />
      </Field>

      <div className="flex items-center gap-3">
        <Button type="submit" disabled={!valid || busy}>
          {busy ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
          Bazaga saqlash
        </Button>
        <AnimatePresence>
          {done && (
            <motion.span
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              className="inline-flex items-center gap-1.5 text-[12px] font-semibold text-mint"
            >
              <Check size={14} />
              Saqlandi
            </motion.span>
          )}
        </AnimatePresence>
      </div>
    </form>
  );
}
