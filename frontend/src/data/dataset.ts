import { DISTRICTS } from "@/data/districts";
import { MODULES, MODULE_BY_ID } from "@/data/modules";
import type { EconomicTask, Indicator, ModuleId, StatusId } from "@/lib/types";

/**
 * Demo ma'lumotlar bazasi.
 *
 * Backend ulanmagan holatda ham platforma to'liq "tirik" ko'rinishi uchun
 * determinlashtirilgan (urug'langan) generator ishlatiladi — SSR va klient
 * bir xil natija beradi, hydration xatosi chiqmaydi.
 *
 * Backend ishga tushgach `lib/api.ts` bu qatlamni avtomatik almashtiradi.
 */

export const CURRENT_YEAR = 2026;
export const BASE_YEAR = 2025;
/** 2026-yil uchun ma'lumot mavjud bo'lgan oxirgi oy */
export const CURRENT_MONTH = 7;

// ── Urug'langan PRNG (mulberry32) ────────────────────────────────────

function seeded(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hash(str: string) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

// ── Tuman profillari ─────────────────────────────────────────────────

/**
 * Har bir tumanning modul bo'yicha "bajarilish kayfiyati".
 * 1.0 = rejaga to'liq mos. Pastroq = ortda qolish.
 * Bu yerdagi zaif nuqtalar TT'dagi stsenariyga mos: Amudaryo/Beruniy —
 * suv resurslari, Mo'ynoq — Orol ekologik zonasi.
 */
const PROFILE: Record<string, Partial<Record<ModuleId, number>>> = {
  amudaryo: { agriculture: 0.71, export: 0.68, employment: 0.92 },
  beruniy: { agriculture: 0.74, export: 0.72, investment: 0.95 },
  moynoq: { agriculture: 0.58, employment: 0.79, investment: 0.83, services: 0.86 },
  taxtakopir: { industry: 0.81, services: 0.84, investment: 0.88 },
  bozatov: { industry: 0.83, services: 0.87, agriculture: 0.9 },
  karaozak: { industry: 0.89, export: 0.87 },
  qanlikol: { investment: 0.88, industry: 0.91 },
  shumanay: { export: 0.86, investment: 0.9 },
  kegeyli: { agriculture: 0.94 },
  chimboy: { agriculture: 1.02, export: 0.93 },
  "nukus-shahri": { services: 1.12, industry: 1.08, investment: 1.14, employment: 1.06 },
  "nukus-tumani": { construction: 1.06, services: 1.03 },
  qongirot: { industry: 1.15, export: 1.09, investment: 1.07 },
  xojayli: { industry: 1.04, construction: 1.05 },
  taxiatosh: { industry: 1.09, employment: 1.02 },
  tortkol: { agriculture: 1.06, employment: 1.01 },
  ellikqala: { agriculture: 1.04, construction: 0.93 },
};

/** Modulning tumandagi mutlaq masshtabi — aholi va maydonga bog'liq. */
function scaleFor(districtId: string, moduleId: ModuleId): number {
  const d = DISTRICTS.find((x) => x.id === districtId)!;
  const pop = d.population;
  switch (moduleId) {
    case "inflation":
      return 1;
    case "employment":
      return pop * 0.42;
    case "industry":
      return pop * 7.4 + d.areaKm2 * 0.05;
    case "agriculture":
      return pop * 5.1 + d.areaKm2 * 0.02;
    case "investment":
      return pop * 4.3;
    case "export":
      return pop * 0.55;
    case "construction":
      return pop * 3.1;
    case "services":
      return pop * 6.2;
  }
}

/** Oylik mavsumiylik koeffitsiyenti. */
function seasonality(moduleId: ModuleId, month: number): number {
  const m = month - 1;
  switch (moduleId) {
    case "agriculture":
      // Yig'im-terim kuzda
      return 0.55 + 0.9 * Math.max(0, Math.sin(((m - 2) / 12) * Math.PI * 1.6));
    case "construction":
      return 0.6 + 0.7 * Math.max(0, Math.sin(((m - 1.5) / 12) * Math.PI * 1.7));
    case "export":
      return 0.82 + 0.36 * Math.sin(((m - 3) / 12) * Math.PI * 2);
    case "inflation":
      return 1;
    default:
      return 0.93 + 0.14 * Math.sin((m / 12) * Math.PI * 2);
  }
}

export function statusFromRatio(ratio: number, lowerIsBetter: boolean): StatusId {
  const r = lowerIsBetter ? (ratio === 0 ? 1 : 1 / ratio) : ratio;
  if (r >= 1) return "completed";
  if (r >= 0.9) return "in_progress";
  if (r >= 0.75) return "at_risk";
  return "critical";
}

const NOTES: Partial<Record<ModuleId, string[]>> = {
  agriculture: [
    "Sug'orish suvi limiti qisqartirildi, ekin maydonlarining bir qismi quruq qoldi.",
    "Tomchilatib sug'orish tizimi rejadagidan sekin joriy etilmoqda.",
    "Yer sho'rlanishi darajasi oshdi, hosildorlik pasaydi.",
    "Urug'lik va mineral o'g'it narxlari oshgani tannarxni ko'tardi.",
  ],
  export: [
    "Logistika narxlari oshgani eksport tannarxini qimmatlashtirdi.",
    "Asosiy xaridor bozorida talab pasaydi, shartnomalar qayta ko'rib chiqilmoqda.",
    "Sertifikatlash muddatlari cho'zilib, jo'natmalar kechikdi.",
  ],
  industry: [
    "Ishlab chiqarish quvvatlari to'liq yuklanmagan, xom ashyo yetkazib berish uzildi.",
    "Elektr ta'minotidagi uzilishlar smenalar sonini kamaytirdi.",
    "Yangi ishlab chiqarish liniyasi ishga tushirildi, quvvat oshdi.",
  ],
  investment: [
    "Xorijiy investor bilan shartnoma imzolanish bosqichida.",
    "Loyiha hujjatlarini tasdiqlash kechikdi, moliyalashtirish sekinlashdi.",
    "Bank kreditlari stavkasi oshgani xususiy investitsiyani sekinlashtirdi.",
  ],
  employment: [
    "Mavsumiy ish o'rinlari qisqardi, mehnat migratsiyasi kuchaydi.",
    "Yangi korxona ochilishi bilan doimiy ish o'rinlari yaratildi.",
    "Kasb-hunar o'quv markazlari bitiruvchilari bandligi past.",
  ],
  inflation: [
    "Oziq-ovqat guruhida narxlar sezilarli oshdi.",
    "Yoqilg'i va transport xarajatlari inflyatsiyani kuchaytirdi.",
    "Narxlar barqarorlashdi, mavsumiy pasayish kuzatildi.",
  ],
  construction: [
    "Qurilish materiallari yetkazib berish kechikdi.",
    "Ijtimoiy obyektlar qurilishi jadvaldan oldinda bormoqda.",
  ],
  services: [
    "Turizm oqimi oshdi, xizmatlar hajmi kengaydi.",
    "Raqamli xizmatlar ulushi sekin o'smoqda.",
  ],
};

// ── Generator ────────────────────────────────────────────────────────

function buildIndicators(): Indicator[] {
  const out: Indicator[] = [];

  for (const d of DISTRICTS) {
    for (const mod of MODULES) {
      const rnd = seeded(hash(`${d.id}:${mod.id}`));
      const profile = PROFILE[d.id]?.[mod.id] ?? 1;
      const baseScale = scaleFor(d.id, mod.id);
      // Trend: yildan yilga o'sish sur'ati
      const yoy = mod.id === "inflation" ? 1 : 1.05 + rnd() * 0.09;

      for (const year of [BASE_YEAR, CURRENT_YEAR]) {
        const lastMonth = year === CURRENT_YEAR ? CURRENT_MONTH : 12;
        for (let month = 1; month <= lastMonth; month++) {
          const yearFactor = year === CURRENT_YEAR ? yoy : 1;
          const season = seasonality(mod.id, month);

          let plan: number;
          let fact: number;

          if (mod.id === "inflation") {
            // Inflyatsiya: maqsadli daraja vs amaldagi daraja (%)
            plan = 7.5 - (year - BASE_YEAR) * 0.6;
            const pressure = (1 / profile - 1) * 6;
            fact =
              plan +
              pressure +
              1.6 * Math.sin(((month - 2) / 12) * Math.PI * 2) +
              (rnd() - 0.45) * 1.5;
            fact = Math.max(2.4, fact);
          } else {
            plan = (baseScale * season * yearFactor) / 12;
            plan = Math.round(plan * 10) / 10;
            const noise = 0.94 + rnd() * 0.13;
            fact = plan * profile * noise;
          }

          plan = Math.round(plan * 10) / 10;
          fact = Math.round(fact * 10) / 10;

          const ratio = plan === 0 ? 1 : fact / plan;
          const status = statusFromRatio(ratio, mod.lowerIsBetter);

          // Faqat muammoli yozuvlarga izoh biriktiramiz — AI kontekst uchun
          let note: string | undefined;
          const pool = NOTES[mod.id];
          if (pool && (status === "critical" || status === "at_risk") && rnd() > 0.55) {
            note = pool[Math.floor(rnd() * pool.length)];
          }

          out.push({
            id: `${d.id}-${mod.id}-${year}-${String(month).padStart(2, "0")}`,
            moduleId: mod.id,
            districtId: d.id,
            year,
            month,
            quarter: Math.ceil(month / 3),
            plan,
            fact,
            unit: mod.unit,
            status,
            note,
          });
        }
      }
    }
  }
  return out;
}

export const INDICATORS: Indicator[] = buildIndicators();

// ── Topshiriqlar ─────────────────────────────────────────────────────

const TASK_TEMPLATES: Array<{ title: string; moduleId: ModuleId }> = [
  { title: "Tomchilatib sug'orish maydonlarini 20% ga kengaytirish", moduleId: "agriculture" },
  { title: "Sho'rlangan yerlarni melioratsiya qilish dasturi", moduleId: "agriculture" },
  { title: "Eksport yo'nalishlarini diversifikatsiya qilish", moduleId: "export" },
  { title: "Logistika markazini ishga tushirish", moduleId: "export" },
  { title: "Kichik sanoat zonasini kengaytirish", moduleId: "industry" },
  { title: "Ishlab chiqarish quvvatlarini modernizatsiya qilish", moduleId: "industry" },
  { title: "Xorijiy investorlar bilan 3 ta shartnoma imzolash", moduleId: "investment" },
  { title: "Yoshlar tadbirkorligini qo'llab-quvvatlash dasturi", moduleId: "employment" },
  { title: "Kasb-hunar markazlarida qayta tayyorlash kurslari", moduleId: "employment" },
  { title: "Ijtimoiy uy-joy qurilishini yakunlash", moduleId: "construction" },
  { title: "Turizm infratuzilmasini rivojlantirish", moduleId: "services" },
  { title: "Iste'mol savatidagi narxlarni monitoring qilish", moduleId: "inflation" },
];

const ASSIGNEES = [
  "R. Sultonov",
  "G. Qalandarova",
  "A. Yusupov",
  "M. Seytniyazova",
  "B. Reymov",
  "N. Allambergenova",
  "J. Qurbonboyev",
];

function buildTasks(): EconomicTask[] {
  const out: EconomicTask[] = [];
  const rnd = seeded(20260727);

  DISTRICTS.forEach((d, di) => {
    const count = 2 + Math.floor(rnd() * 3);
    for (let i = 0; i < count; i++) {
      const tpl = TASK_TEMPLATES[Math.floor(rnd() * TASK_TEMPLATES.length)];
      const progress = Math.round(rnd() * 100);
      const status: StatusId =
        progress >= 100
          ? "completed"
          : progress >= 60
            ? "in_progress"
            : progress >= 30
              ? "at_risk"
              : "critical";
      const month = 1 + Math.floor(rnd() * 12);
      out.push({
        id: `task-${d.id}-${i}`,
        title: tpl.title,
        moduleId: tpl.moduleId,
        districtId: d.id,
        status,
        progress,
        deadline: `${CURRENT_YEAR}-${String(month).padStart(2, "0")}-${String(1 + Math.floor(rnd() * 27)).padStart(2, "0")}`,
        assignee: ASSIGNEES[(di + i) % ASSIGNEES.length],
        description: `${d.name} tumani bo'yicha ${MODULE_BY_ID[tpl.moduleId].name.toLowerCase()} yo'nalishidagi topshiriq.`,
        createdAt: `${CURRENT_YEAR}-01-${String(5 + i).padStart(2, "0")}`,
      });
    }
  });
  return out;
}

export const TASKS: EconomicTask[] = buildTasks();
