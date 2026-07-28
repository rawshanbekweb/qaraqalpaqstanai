"use client";

/**
 * `/api/stats` — Excel'dan yuklangan haqiqiy statistika bilan ishlash.
 *
 * Demo ma'lumot (`src/data/dataset.ts`) reja↔amalda modeliga qurilgan.
 * Manba statistikada reja yo'q, shuning uchun bu yerdagi tushunchalar
 * boshqacha: hajm, o'tgan yilga nisbatan o'sish, respublikadagi ulush
 * va o'rin.
 */

import { useCallback, useEffect, useState } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

// ── Javob shakllari (backend `app/services/stats.py` bilan bir xil) ──

export interface StatsModule {
  id: string;
  name: string;
  short: string;
  color: string;
  sort: number;
  unit: string;
  indicator_id: number;
  has_districts: boolean;
  /** Shu soha uchun manbada mavjud yillar */
  years: number[];
  latest_year: number | null;
}

export interface StatsCategory {
  id: string;
  name: string;
  name_uz: string;
  color: string;
  sort: number;
  indicators: number;
}

export interface StatsDistrict {
  id: string;
  name: string;
  name_ru: string;
  center: string;
  area_km2: number;
  population: number;
}

export interface StatsMeta {
  years: number[];
  latest_year: number;
  modules: StatsModule[];
  categories: StatsCategory[];
  districts: StatsDistrict[];
  indicators: number;
  observations: number;
}

export interface IndicatorBrief {
  id: number;
  slug: string;
  category_id: string;
  name: string;
  name_uz: string;
  unit: string;
  module: string | null;
  module_name: string | null;
  color: string | null;
  has_districts: boolean;
  lower_is_better: boolean;
  source: string;
}

export interface MapDistrict {
  district_id: string;
  name: string;
  /** Manbada shu yil uchun yozuv bo'lmasa — null */
  value: number | null;
  share: number | null;
  yoy: number | null;
  /** Eng katta qiymatga nisbati, 0..1 */
  intensity: number | null;
  rank: number | null;
}

export interface MapLayer {
  indicator: IndicatorBrief;
  year: number;
  period: string | null;
  period_caption: string | null;
  /** Yil tugamagan — qiymat yil boshidan yig'indi */
  partial: boolean;
  /** O'tgan yil bilan bir xil davr kesimidami */
  comparable: boolean;
  unit: string;
  total: number;
  max: number;
  covered: number;
  districts: MapDistrict[];
}

export interface SeriesPoint {
  year: number;
  label: string;
  caption: string;
  partial: boolean;
  value: number;
  yoy: number | null;
  sources: number;
  aggregated: boolean;
}

export interface Series {
  indicator: IndicatorBrief;
  district_id: string | null;
  unit: string;
  points: SeriesPoint[];
}

export interface ProfileModule {
  module: string;
  name: string;
  full_name: string;
  color: string;
  sort: number;
  indicator_id: number;
  unit: string;
  value: number;
  yoy: number | null;
  partial: boolean;
  share: number | null;
  rank: number | null;
  of: number;
  trend: number[];
}

export interface DistrictProfile {
  district: StatsDistrict;
  year: number;
  modules: ProfileModule[];
  avg_growth: number | null;
}

export interface OverviewModule {
  module: string;
  name: string;
  full_name: string;
  color: string;
  sort: number;
  indicator_id: number;
  unit: string;
  value: number;
  yoy: number | null;
  partial: boolean;
  caption: string;
  leader: { district_id: string; name: string; value: number } | null;
  laggard: { district_id: string; name: string; value: number } | null;
  trend: Array<{ year: number; value: number }>;
}

export interface Overview {
  year: number;
  years: number[];
  modules: OverviewModule[];
  avg_growth: number | null;
  growing: number;
  declining: number;
}

// ── So'rov qatlami ───────────────────────────────────────────────────

/**
 * Javoblar keshi.
 *
 * Xarita, tooltip va statistika paneli bir vaqtda bir xil kesimni
 * so'raydi; kesh bo'lmasa har filtr o'zgarishida bir xil so'rov 3–4 marta
 * ketardi. Ma'lumot statik (yilda bir yangilanadi) — muddat qo'yilmagan.
 */
const cache = new Map<string, Promise<unknown>>();

export function statsUrl(path: string, params: Record<string, string | number | undefined> = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  }
  const query = qs.toString();
  return `${BASE}/api/stats${path}${query ? `?${query}` : ""}`;
}

export function fetchStats<T>(path: string, params?: Record<string, string | number | undefined>) {
  const url = statsUrl(path, params);
  let hit = cache.get(url) as Promise<T> | undefined;
  if (!hit) {
    hit = fetch(url, { signal: AbortSignal.timeout(20_000) }).then((r) => {
      if (!r.ok) throw new Error(`${r.status} ${url}`);
      return r.json() as Promise<T>;
    });
    // Xato keshda qolib ketmasin — keyingi urinish yangidan so'raydi
    hit.catch(() => cache.delete(url));
    cache.set(url, hit);
  }
  return hit;
}

export interface Query<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

/**
 * Bitta GET so'rovi — kesh bilan, natijasi komponent holatida.
 *
 * Natija so'rov URL'i bilan birga saqlanadi va render paytida solishtiriladi:
 * filtr o'zgarganda eski javob bir kadr bo'lsa ham ko'rinib qolmaydi va
 * effekt ichida holatni sinxron yangilash kerak bo'lmaydi.
 */
export function useStats<T>(
  path: string | null,
  params?: Record<string, string | number | undefined>,
): Query<T> {
  const key = path === null ? null : statsUrl(path, params);
  const [result, setResult] = useState<{ key: string | null; data: T | null; error: Error | null }>({
    key: null,
    data: null,
    error: null,
  });

  useEffect(() => {
    if (path === null || key === null) return;
    let alive = true;
    fetchStats<T>(path, params)
      .then((data) => alive && setResult({ key, data, error: null }))
      .catch((error: Error) => alive && setResult({ key, data: null, error }));
    return () => {
      alive = false;
    };
    // `params` har renderda yangi obyekt — bog'liqlik sifatida URL ishlatiladi
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const fresh = result.key === key;
  return {
    data: fresh ? result.data : null,
    loading: key !== null && !fresh,
    error: fresh ? result.error : null,
  };
}

export function useStatsMeta() {
  return useStats<StatsMeta>("/meta");
}

export function useOverview(year: number | null) {
  return useStats<Overview>(year ? "/overview" : null, { year: year ?? undefined });
}

export function useMapLayer(module: string | null, year: number | null) {
  return useStats<MapLayer>(module && year ? "/map" : null, {
    module: module ?? undefined,
    year: year ?? undefined,
  });
}

export function useDistrictProfile(districtId: string | null, year: number | null) {
  return useStats<DistrictProfile>(districtId && year ? `/districts/${districtId}` : null, {
    year: year ?? undefined,
  });
}

export function useSeries(
  module: string | null,
  districtId: string | null,
  yearFrom?: number,
  yearTo?: number,
) {
  return useStats<Series>(module ? "/series" : null, {
    module: module ?? undefined,
    district_id: districtId ?? undefined,
    year_from: yearFrom,
    year_to: yearTo,
  });
}

/** Keshni tozalash — admin ma'lumotni qayta yuklaganidan keyin kerak. */
export function useStatsRefresh() {
  return useCallback(() => cache.clear(), []);
}

// ── Formatlash ───────────────────────────────────────────────────────

/**
 * O'lchov birligi manbadan uzun keladi ("ámeldegi baxalarda; mlrd. som").
 * Kartochkada faqat o'lchov qismi kerak.
 */
export function shortUnit(unit: string): string {
  const tail = unit.split(";").pop() ?? unit;
  return tail.replace(/^\s*[-–—]\s*/, "").trim();
}

/** "2026*" kabi yorliq — yil to'liq emasligini bildiradi. */
export function periodNote(partial: boolean, caption: string | null): string {
  return partial && caption ? `${caption} juwmaǵı` : "tolıq jıl";
}
