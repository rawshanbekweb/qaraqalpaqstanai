import { BASE_YEAR, CURRENT_MONTH, CURRENT_YEAR, INDICATORS, statusFromRatio } from "@/data/dataset";
import { DISTRICT_BY_ID, DISTRICTS } from "@/data/districts";
import { MODULES, MONTHS_SHORT } from "@/data/modules";
import type { Indicator, ModuleId, StatusId } from "@/lib/types";

export interface Filters {
  moduleId: ModuleId | "all";
  districtId: string | "all";
  year: number;
  status: StatusId | "all";
  period: "month" | "quarter" | "year";
}

export const DEFAULT_FILTERS: Filters = {
  moduleId: "all",
  districtId: "all",
  year: CURRENT_YEAR,
  status: "all",
  period: "year",
};

export function selectIndicators(f: Partial<Filters>): Indicator[] {
  return INDICATORS.filter(
    (i) =>
      (!f.moduleId || f.moduleId === "all" || i.moduleId === f.moduleId) &&
      (!f.districtId || f.districtId === "all" || i.districtId === f.districtId) &&
      (!f.year || i.year === f.year) &&
      (!f.status || f.status === "all" || i.status === f.status),
  );
}

export interface Rollup {
  plan: number;
  fact: number;
  /** fact/plan — 1.0 = reja bajarildi */
  ratio: number;
  /** Modul yo'nalishini hisobga olgan bajarilish (inflyatsiyada teskari) */
  performance: number;
  status: StatusId;
  count: number;
}

export function rollup(rows: Indicator[], moduleId?: ModuleId): Rollup {
  const plan = rows.reduce((s, r) => s + r.plan, 0);
  const fact = rows.reduce((s, r) => s + r.fact, 0);
  const isInflation = moduleId === "inflation" || rows.every((r) => r.moduleId === "inflation");
  // Inflyatsiya — foiz, yig'indi emas o'rtacha
  const p = isInflation && rows.length ? plan / rows.length : plan;
  const fx = isInflation && rows.length ? fact / rows.length : fact;
  const ratio = p === 0 ? 1 : fx / p;
  const lower = isInflation;
  const performance = lower ? (ratio === 0 ? 1 : 1 / ratio) : ratio;
  return {
    plan: p,
    fact: fx,
    ratio,
    performance,
    status: statusFromRatio(ratio, lower),
    count: rows.length,
  };
}

/** Har bir tuman uchun umumlashtirilgan bajarilish — xarita ranglari shundan. */
export function districtScores(
  moduleId: ModuleId | "all",
  year = CURRENT_YEAR,
): Record<string, Rollup> {
  const out: Record<string, Rollup> = {};
  for (const d of DISTRICTS) {
    if (moduleId === "all") {
      // Barcha modullar bo'yicha o'rtacha bajarilish
      const perModule = MODULES.map((m) =>
        rollup(
          INDICATORS.filter(
            (i) => i.districtId === d.id && i.moduleId === m.id && i.year === year,
          ),
          m.id,
        ),
      ).filter((r) => r.count > 0);
      const performance =
        perModule.reduce((s, r) => s + r.performance, 0) / Math.max(1, perModule.length);
      out[d.id] = {
        plan: perModule.reduce((s, r) => s + r.plan, 0),
        fact: perModule.reduce((s, r) => s + r.fact, 0),
        ratio: performance,
        performance,
        status: statusFromRatio(performance, false),
        count: perModule.reduce((s, r) => s + r.count, 0),
      };
    } else {
      out[d.id] = rollup(
        INDICATORS.filter(
          (i) => i.districtId === d.id && i.moduleId === moduleId && i.year === year,
        ),
        moduleId,
      );
    }
  }
  return out;
}

export interface MonthPoint {
  label: string;
  month: number;
  plan: number;
  fact: number;
  prev?: number;
}

/** Oylik dinamika: reja / amalda / o'tgan yil. */
export function monthlySeries(
  moduleId: ModuleId,
  districtId: string | "all",
  year = CURRENT_YEAR,
): MonthPoint[] {
  const isInflation = moduleId === "inflation";
  const points: MonthPoint[] = [];
  const lastMonth = year === CURRENT_YEAR ? CURRENT_MONTH : 12;

  for (let m = 1; m <= lastMonth; m++) {
    const pick = (y: number) =>
      INDICATORS.filter(
        (i) =>
          i.moduleId === moduleId &&
          i.year === y &&
          i.month === m &&
          (districtId === "all" || i.districtId === districtId),
      );
    const cur = pick(year);
    const prevRows = pick(year - 1);
    const agg = (rows: Indicator[], key: "plan" | "fact") => {
      if (!rows.length) return 0;
      const sum = rows.reduce((s, r) => s + r[key], 0);
      return round(isInflation ? sum / rows.length : sum);
    };
    points.push({
      label: MONTHS_SHORT[m - 1],
      month: m,
      plan: agg(cur, "plan"),
      fact: agg(cur, "fact"),
      prev: prevRows.length ? agg(prevRows, "fact") : undefined,
    });
  }
  return points;
}

export interface QuarterPoint {
  label: string;
  plan: number;
  fact: number;
}

export function quarterlySeries(
  moduleId: ModuleId,
  districtId: string | "all",
  year = CURRENT_YEAR,
): QuarterPoint[] {
  const isInflation = moduleId === "inflation";
  return [1, 2, 3, 4]
    .map((q) => {
      const rows = INDICATORS.filter(
        (i) =>
          i.moduleId === moduleId &&
          i.year === year &&
          i.quarter === q &&
          (districtId === "all" || i.districtId === districtId),
      );
      if (!rows.length) return null;
      const agg = (key: "plan" | "fact") => {
        const sum = rows.reduce((s, r) => s + r[key], 0);
        return round(isInflation ? sum / rows.length : sum);
      };
      return { label: `${q}-chorak`, plan: agg("plan"), fact: agg("fact") };
    })
    .filter(Boolean) as QuarterPoint[];
}

/** Yillik o'sish sur'ati (%) — joriy yil vs o'tgan yil, taqqoslanadigan oylar. */
export function yoyGrowth(moduleId: ModuleId, districtId: string | "all" = "all"): number {
  const upTo = CURRENT_MONTH;
  const sum = (year: number) => {
    const rows = INDICATORS.filter(
      (i) =>
        i.moduleId === moduleId &&
        i.year === year &&
        (i.month ?? 0) <= upTo &&
        (districtId === "all" || i.districtId === districtId),
    );
    if (!rows.length) return 0;
    const total = rows.reduce((s, r) => s + r.fact, 0);
    return moduleId === "inflation" ? total / rows.length : total;
  };
  const a = sum(BASE_YEAR);
  const b = sum(CURRENT_YEAR);
  if (!a) return 0;
  return round(((b - a) / a) * 100);
}

export interface WeakSpot {
  districtId: string;
  districtName: string;
  moduleId: ModuleId;
  moduleName: string;
  performance: number;
  gap: number;
  status: StatusId;
  note?: string;
}

/** Reja bajarilmayotgan tuman × modul kesimlari — eng og'iridan boshlab. */
export function weakSpots(
  year = CURRENT_YEAR,
  opts: { moduleId?: ModuleId | "all"; districtId?: string | "all"; limit?: number } = {},
): WeakSpot[] {
  const { moduleId = "all", districtId = "all", limit = 12 } = opts;
  const out: WeakSpot[] = [];

  for (const d of DISTRICTS) {
    if (districtId !== "all" && d.id !== districtId) continue;
    for (const m of MODULES) {
      if (moduleId !== "all" && m.id !== moduleId) continue;
      const rows = INDICATORS.filter(
        (i) => i.districtId === d.id && i.moduleId === m.id && i.year === year,
      );
      if (!rows.length) continue;
      const r = rollup(rows, m.id);
      if (r.performance >= 0.9) continue;
      const noted = rows.find((x) => x.note);
      out.push({
        districtId: d.id,
        districtName: d.name,
        moduleId: m.id,
        moduleName: m.name,
        performance: r.performance,
        gap: round(m.lowerIsBetter ? r.fact - r.plan : r.plan - r.fact),
        status: r.status,
        note: noted?.note,
      });
    }
  }
  return out.sort((a, b) => a.performance - b.performance).slice(0, limit);
}

/** Tuman kesimidagi reyting — modul bo'yicha bajarilish foizi. */
export function districtRanking(moduleId: ModuleId | "all", year = CURRENT_YEAR) {
  const scores = districtScores(moduleId, year);
  return DISTRICTS.map((d) => ({
    id: d.id,
    name: d.name,
    performance: scores[d.id]?.performance ?? 0,
    fact: scores[d.id]?.fact ?? 0,
    plan: scores[d.id]?.plan ?? 0,
    status: scores[d.id]?.status ?? ("critical" as StatusId),
  })).sort((a, b) => b.performance - a.performance);
}

/** Bitta tumanning barcha modullar bo'yicha kesimi — xarita tooltip/paneli uchun. */
export function districtProfile(districtId: string, year = CURRENT_YEAR) {
  const d = DISTRICT_BY_ID[districtId];
  const modules = MODULES.map((m) => {
    const rows = INDICATORS.filter(
      (i) => i.districtId === districtId && i.moduleId === m.id && i.year === year,
    );
    const r = rollup(rows, m.id);
    return {
      moduleId: m.id,
      name: m.short,
      unit: m.unit,
      color: m.color,
      plan: round(r.plan),
      fact: round(r.fact),
      performance: r.performance,
      status: r.status,
      yoy: yoyGrowth(m.id, districtId),
    };
  });
  const overall = modules.reduce((s, m) => s + m.performance, 0) / modules.length;
  return {
    district: d,
    modules,
    overall,
    status: statusFromRatio(overall, false),
    criticalCount: modules.filter((m) => m.status === "critical" || m.status === "at_risk").length,
  };
}

/** Umumiy KPI kartochkalari uchun. */
export function headlineStats(moduleId: ModuleId | "all", year = CURRENT_YEAR) {
  const mods = moduleId === "all" ? MODULES.map((m) => m.id) : [moduleId];
  const perf =
    mods
      .map((m) => rollup(INDICATORS.filter((i) => i.moduleId === m && i.year === year), m).performance)
      .reduce((s, v) => s + v, 0) / mods.length;

  const spots = weakSpots(year, { moduleId, limit: 200 });
  const critical = spots.filter((s) => s.status === "critical").length;
  const atRisk = spots.filter((s) => s.status === "at_risk").length;
  const growth =
    mods.map((m) => yoyGrowth(m)).reduce((s, v) => s + v, 0) / mods.length;

  return {
    performance: perf,
    growth: round(growth),
    critical,
    atRisk,
    districts: DISTRICTS.length,
    records: INDICATORS.filter(
      (i) => i.year === year && (moduleId === "all" || i.moduleId === moduleId),
    ).length,
  };
}

/** Modullar kesimidagi radar — tumanni respublika o'rtachasi bilan solishtirish. */
export function radarCompare(districtId: string | "all", year = CURRENT_YEAR) {
  return MODULES.map((m) => {
    const republic = rollup(INDICATORS.filter((i) => i.moduleId === m.id && i.year === year), m.id);
    const local =
      districtId === "all"
        ? republic
        : rollup(
            INDICATORS.filter(
              (i) => i.moduleId === m.id && i.districtId === districtId && i.year === year,
            ),
            m.id,
          );
    return {
      label: m.short,
      moduleId: m.id,
      local: round(Math.min(130, local.performance * 100)),
      republic: round(Math.min(130, republic.performance * 100)),
    };
  });
}

export function round(n: number, digits = 1): number {
  const f = 10 ** digits;
  return Math.round(n * f) / f;
}
