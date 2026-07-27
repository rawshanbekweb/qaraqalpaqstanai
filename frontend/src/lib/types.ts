// Platformaning umumiy domen modeli. Backend (FastAPI) shu shakllarni qaytaradi.

export type ModuleId =
  | "inflation"
  | "industry"
  | "agriculture"
  | "investment"
  | "export"
  | "employment"
  | "construction"
  | "services";

export type StatusId = "completed" | "in_progress" | "at_risk" | "critical";

export type PeriodType = "month" | "quarter" | "year";

export type Role = "admin" | "viewer";

/** Bir tuman + bir modul + bir davr kesimidagi ko'rsatkich. */
export interface Indicator {
  id: string;
  moduleId: ModuleId;
  districtId: string;
  year: number;
  /** 1..12 — yillik yozuvda null */
  month: number | null;
  /** 1..4 — hisoblab chiqariladi */
  quarter: number | null;
  /** Rejalashtirilgan ko'rsatkich (KPI) */
  plan: number;
  /** Amaldagi ko'rsatkich */
  fact: number;
  unit: string;
  status: StatusId;
  /** Admin qoldirgan izoh — AI kontekstiga tushadi */
  note?: string;
}

/** Iqtisodiy topshiriq / loyiha. */
export interface EconomicTask {
  id: string;
  title: string;
  moduleId: ModuleId;
  districtId: string;
  status: StatusId;
  progress: number;
  deadline: string;
  assignee: string;
  description?: string;
  createdAt: string;
}

/** AI qaytaradigan grafik spetsifikatsiyasi — chat javobida chizmalar shundan yasaladi. */
/**
 * `bar` — gorizontal ustunlar (uzun nomlar uchun), `grouped-bar` — vertikal
 * guruhlangan, `dumbbell` — bir obyektning ikki qiymati (tuman ↔ respublika).
 * Doiraviy (pie/donut) shakl ataylab yo'q: 7 ta yaqin qiymatni burchak orqali
 * taqqoslash noto'g'ri o'qiladi.
 */
export type ChartKind = "line" | "area" | "bar" | "grouped-bar" | "dumbbell" | "diverging-bar";

export interface ChartSeries {
  key: string;
  label: string;
  color?: string;
}

export interface ChartSpec {
  id: string;
  kind: ChartKind;
  title: string;
  subtitle?: string;
  unit?: string;
  series: ChartSeries[];
  /** Har bir yozuv: { label: string, [seriesKey]: number } */
  data: Array<Record<string, string | number>>;
}

/** AI tavsiyasi — 3 bosqichli harakatlar rejasi. */
export interface Recommendation {
  horizon: "short" | "mid" | "long";
  title: string;
  actions: string[];
  impact: string;
}

export interface AiInsight {
  headline: string;
  body: string;
  severity: StatusId;
  districts: string[];
  moduleId?: ModuleId;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  charts?: ChartSpec[];
  insight?: AiInsight;
  recommendations?: Recommendation[];
  /** Manba sifatida ishlatilgan yozuvlar soni — RAG shaffofligi uchun */
  sources?: number;
  createdAt: number;
  streaming?: boolean;
}

export interface SessionUser {
  username: string;
  fullName: string;
  role: Role;
}
