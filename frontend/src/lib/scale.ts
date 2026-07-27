import { clamp } from "@/lib/utils";

/**
 * Xarita shkalasi — DIVERGING (qutbli), kamalak emas.
 *
 * O'lchanayotgan narsa: reja bajarilishi 100% dan qay tomonga og'gani.
 * Shuning uchun neytral markaz (reja darajasi) kulrang, ikki qanoti esa
 * qarama-qarshi issiq/sovuq juftlik:
 *   qizil  ← rejadan past  ·  kulrang = reja darajasi  ·  ko'k → rejadan yuqori
 *
 * Har ikkala qanot dataviz validatoridan ordinal ramp sifatida o'tgan
 * (monoton yorug'lik, ΔL ≥ 0.06, fonga nisbatan kontrast).
 */

const NEUTRAL: [number, number, number] = [60, 67, 99]; // #3c4363 — reja darajasi

/**
 * Bosqichlar amaldagi tarqalishga moslangan: tumanlarning aksari 0,85–1,10
 * oralig'ida yotadi, shuning uchun shkala shu oraliqda eng sezgir. Chegaralar
 * filtrdan qat'i nazar O'ZGARMAYDI — aks holda modul almashtirilganda
 * ranglar qayta bo'yalib, o'quvchini chalg'itardi.
 */
const STOPS: Array<[number, [number, number, number]]> = [
  [0.7, [240, 113, 120]], //  #f07178 — eng og'ir orqada qolish
  [0.82, [208, 59, 59]], //   #d03b3b
  [0.9, [143, 48, 64]], //    #8f3040
  [0.97, NEUTRAL], //         #3c4363 — reja darajasi
  [1.02, [42, 95, 158]], //   #2a5f9e
  [1.06, [42, 120, 214]], //  #2a78d6
  [1.15, [109, 167, 236]], // #6da7ec — rejadan sezilarli yuqori
];

export function rampRgb(p: number): [number, number, number] {
  const v = clamp(p, STOPS[0][0], STOPS[STOPS.length - 1][0]);
  for (let i = 0; i < STOPS.length - 1; i++) {
    const [a, ca] = STOPS[i];
    const [b, cb] = STOPS[i + 1];
    if (v >= a && v <= b) {
      const t = (v - a) / (b - a);
      return [
        Math.round(ca[0] + (cb[0] - ca[0]) * t),
        Math.round(ca[1] + (cb[1] - ca[1]) * t),
        Math.round(ca[2] + (cb[2] - ca[2]) * t),
      ];
    }
  }
  return STOPS[STOPS.length - 1][1];
}

export function performanceColor(p: number, alpha = 1): string {
  const [r, g, b] = rampRgb(p);
  return alpha === 1 ? `rgb(${r} ${g} ${b})` : `rgb(${r} ${g} ${b} / ${alpha})`;
}

/** Legenda — rang yolg'iz ma'no tashimasligi uchun har bosqich yozuvli. */
export const LEGEND_STOPS = [
  { label: "< 80%", color: "rgb(238 100 106)", hint: "reja bajarilmagan" },
  { label: "80–92%", color: "rgb(170 52 56)", hint: "ortda qolmoqda" },
  { label: "≈ 100%", color: "rgb(74 82 116)", hint: "reja darajasida" },
  { label: "> 106%", color: "rgb(64 140 226)", hint: "rejadan yuqori" },
];
