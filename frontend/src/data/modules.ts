import type { ModuleId, StatusId } from "@/lib/types";

export interface ModuleMeta {
  id: ModuleId;
  name: string;
  short: string;
  unit: string;
  /** Ko'rsatkich pasayishi yaxshimi? (inflyatsiya uchun — ha) */
  lowerIsBetter: boolean;
  color: string;
  glow: string;
}

export const MODULES: ModuleMeta[] = [
  {
    id: "inflation",
    name: "Inflyatsiya",
    short: "Inflyatsiya",
    unit: "%",
    lowerIsBetter: true,
    color: "#e11d48",
    glow: "225 29 72",
  },
  {
    id: "industry",
    name: "Sanoat ishlab chiqarish",
    short: "Sanoat",
    unit: "mlrd so'm",
    lowerIsBetter: false,
    color: "#0284c7",
    glow: "2 132 199",
  },
  {
    id: "agriculture",
    name: "Qishloq xo'jaligi",
    short: "Qishloq x/j",
    unit: "mlrd so'm",
    lowerIsBetter: false,
    color: "#65a30d",
    glow: "101 163 13",
  },
  {
    id: "investment",
    name: "Investitsiyalar",
    short: "Investitsiya",
    unit: "mlrd so'm",
    lowerIsBetter: false,
    color: "#8b5cf6",
    glow: "139 92 246",
  },
  {
    id: "export",
    name: "Eksport hajmi",
    short: "Eksport",
    unit: "mln $",
    lowerIsBetter: false,
    color: "#0891b2",
    glow: "8 145 178",
  },
  {
    id: "employment",
    name: "Bandlik",
    short: "Bandlik",
    unit: "ming kishi",
    lowerIsBetter: false,
    color: "#d97706",
    glow: "217 119 6",
  },
  {
    id: "construction",
    name: "Qurilish",
    short: "Qurilish",
    unit: "mlrd so'm",
    lowerIsBetter: false,
    color: "#c026d3",
    glow: "192 38 211",
  },
  {
    id: "services",
    name: "Xizmatlar sohasi",
    short: "Xizmatlar",
    unit: "mlrd so'm",
    lowerIsBetter: false,
    color: "#059669",
    glow: "5 150 105",
  },
];

export const MODULE_BY_ID = Object.fromEntries(MODULES.map((m) => [m.id, m])) as Record<
  ModuleId,
  ModuleMeta
>;

export interface StatusMeta {
  id: StatusId;
  name: string;
  color: string;
  /** Bajarilish foizining chegarasi (fact/plan) */
  threshold: number;
}

/**
 * Status palitrasi — SERIYA ranglaridan qat'iy ajratilgan va hech qachon
 * "9-chi seriya" sifatida ishlatilmaydi. Har doim matnli yorliq bilan
 * birga chiqadi, ya'ni ma'no faqat rangga tayanmaydi.
 */
export const STATUSES: StatusMeta[] = [
  { id: "completed", name: "Bajarilgan", color: "#0ca30c", threshold: 1.0 },
  { id: "in_progress", name: "Jarayonda", color: "#8fa3d4", threshold: 0.9 },
  { id: "at_risk", name: "Xavf ostida", color: "#fab219", threshold: 0.75 },
  { id: "critical", name: "Kritik", color: "#d03b3b", threshold: 0 },
];

export const STATUS_BY_ID = Object.fromEntries(STATUSES.map((s) => [s.id, s])) as Record<
  StatusId,
  StatusMeta
>;

export const MONTHS_UZ = [
  "Yanvar",
  "Fevral",
  "Mart",
  "Aprel",
  "May",
  "Iyun",
  "Iyul",
  "Avgust",
  "Sentabr",
  "Oktabr",
  "Noyabr",
  "Dekabr",
];

export const MONTHS_SHORT = ["Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek"];
