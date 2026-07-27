import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** 12345.6 -> "12,3 ming" ko'rinishida ixchamlashtirish. */
export function compact(n: number, digits = 1): string {
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `${trim(n / 1_000_000, digits)} mln`;
  if (abs >= 1_000) return `${trim(n / 1_000, digits)} ming`;
  return trim(n, abs < 10 ? digits : 0);
}

/** O'q yorliqlari uchun — bo'shliqsiz va qisqa, chunki joy tor. */
export function compactAxis(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `${trim(n / 1_000_000, 1)}mln`;
  if (abs >= 1_000) return `${trim(n / 1_000, abs >= 10_000 ? 0 : 1)}k`;
  return trim(n, 0);
}

/**
 * Raqamni o'zbekcha formatda yozadi: mingliklar ajratgichi — uzilmas probel,
 * kasr ajratgichi — vergul.
 *
 * `toLocaleString` ataylab ishlatilmagan: Node va brauzerdagi ICU ma'lumotlari
 * farq qilib, SSR bilan klient natijasi mos kelmay hydration xatosi berardi.
 */
export function trim(n: number, digits = 1): string {
  if (!Number.isFinite(n)) return "0";
  const neg = n < 0;
  const fixed = Math.abs(n).toFixed(digits);
  let [int, frac = ""] = fixed.split(".");
  frac = frac.replace(/0+$/, "");
  int = int.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${neg ? "−" : ""}${int}${frac ? `,${frac}` : ""}`;
}

export function pct(n: number, digits = 1): string {
  return `${n > 0 ? "+" : ""}${trim(n, digits)}%`;
}

export function ratioPct(ratio: number): string {
  return `${trim(ratio * 100, 1)}%`;
}

export function uid(prefix = "id"): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

export function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}.${m}.${y}`;
}

export function daysLeft(iso: string, from = new Date("2026-07-27")): number {
  const target = new Date(iso);
  return Math.round((target.getTime() - from.getTime()) / 86_400_000);
}

export function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export function clamp(n: number, min: number, max: number) {
  return Math.min(max, Math.max(min, n));
}
