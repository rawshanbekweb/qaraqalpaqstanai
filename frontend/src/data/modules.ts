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
    name: "Inflyaciya",
    short: "Inflyaciya",
    unit: "%",
    lowerIsBetter: true,
    color: "#e11d48",
    glow: "225 29 72",
  },
  {
    id: "industry",
    name: "Sanaat ónimi",
    short: "Sanaat",
    unit: "mlrd so'm",
    lowerIsBetter: false,
    color: "#0284c7",
    glow: "2 132 199",
  },
  {
    id: "agriculture",
    name: "Awıl xojalıǵı",
    short: "Awıl xojalıǵı",
    unit: "mlrd so'm",
    lowerIsBetter: false,
    color: "#65a30d",
    glow: "101 163 13",
  },
  {
    id: "investment",
    name: "Investiciyalar",
    short: "Investiciya",
    unit: "mlrd so'm",
    lowerIsBetter: false,
    color: "#8b5cf6",
    glow: "139 92 246",
  },
  {
    id: "export",
    name: "Eksport kólemi",
    short: "Eksport",
    unit: "mln $",
    lowerIsBetter: false,
    color: "#0891b2",
    glow: "8 145 178",
  },
  {
    id: "employment",
    name: "Bántlik",
    short: "Bántlik",
    unit: "ming kishi",
    lowerIsBetter: false,
    color: "#d97706",
    glow: "217 119 6",
  },
  {
    id: "construction",
    name: "Qurılıs",
    short: "Qurılıs",
    unit: "mlrd so'm",
    lowerIsBetter: false,
    color: "#c026d3",
    glow: "192 38 211",
  },
  {
    id: "services",
    name: "Xızmetler tarawı",
    short: "Xızmetler",
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
  { id: "completed", name: "Ósiw", color: "#0ca30c", threshold: 1.0 },
  { id: "in_progress", name: "Turaqlı", color: "#8fa3d4", threshold: 0.9 },
  { id: "at_risk", name: "Tómenlew", color: "#fab219", threshold: 0.75 },
  { id: "critical", name: "Keskin tómenlew", color: "#d03b3b", threshold: 0 },
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
