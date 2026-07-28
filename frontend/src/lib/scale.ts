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

/*
 * ── Hajm shkalasi (haqiqiy statistika) ──────────────────────────────
 *
 * Yuqoridagi qutbli shkala reja bilan taqqoslash uchun. Manba
 * statistikada reja yo'q — o'lchanadigan narsa HAJM, uning esa qutbi
 * yo'q: ko'p yoki kam, "yomon tomon" degani emas. Shuning uchun bu yerda
 * bir yo'nalishli (sequential) ramp: qorong'i ko'kdan yorug' zangoriga.
 *
 * Yorug'lik monoton o'sadi, ya'ni rangni ko'rmaydigan foydalanuvchi ham
 * bosqichlarni ajrata oladi.
 */
const VOLUME_STOPS: Array<[number, [number, number, number]]> = [
  [0, [30, 41, 74]], //     #1e294a — eng kichik hajm
  [0.25, [30, 78, 132]], // #1e4e84
  [0.5, [26, 122, 178]], // #1a7ab2
  [0.75, [45, 170, 205]], //#2daacd
  [1, [125, 226, 231]], //  #7de2e7 — eng katta hajm
];

/**
 * Hajm ulushidan rang.
 *
 * `t` — eng katta tumanga nisbat (0..1). Ildiz ataylab olinadi: Nukus
 * shahri ko'p sohada respublikaning ~30% ini beradi, chiziqli shkalada
 * qolgan 16 tuman bir xil qorong'i dog'ga aylanib qolardi.
 */
export function volumeColor(t: number | null | undefined, alpha = 1): string {
  if (t === null || t === undefined) return alpha === 1 ? "#1b2338" : `rgb(27 35 56 / ${alpha})`;
  const v = Math.sqrt(clamp(t, 0, 1));
  for (let i = 0; i < VOLUME_STOPS.length - 1; i++) {
    const [a, ca] = VOLUME_STOPS[i];
    const [b, cb] = VOLUME_STOPS[i + 1];
    if (v >= a && v <= b) {
      const k = (v - a) / (b - a);
      const c = [0, 1, 2].map((j) => Math.round(ca[j] + (cb[j] - ca[j]) * k));
      return alpha === 1 ? `rgb(${c[0]} ${c[1]} ${c[2]})` : `rgb(${c[0]} ${c[1]} ${c[2]} / ${alpha})`;
    }
  }
  return `rgb(125 226 231${alpha === 1 ? "" : ` / ${alpha}`})`;
}

/** Hajm legendasi — ulush bo'yicha, chunki birlik sohaga qarab o'zgaradi. */
export const VOLUME_LEGEND = [
  { t: 0.02, label: "eń tómen" },
  { t: 0.15, label: "tómen" },
  { t: 0.4, label: "ortasha" },
  { t: 0.7, label: "joqarı" },
  { t: 1, label: "eń joqarı" },
].map((s) => ({ ...s, color: volumeColor(s.t) }));

/**
 * O'sish sur'ati uchun rang — nolga nisbatan qutbli.
 * Qutbli shkala shu yerda o'z ma'nosida qoladi: pasayish ↔ o'sish.
 */
export function growthColor(yoy: number | null | undefined): string {
  if (yoy === null || yoy === undefined) return "#5a6588";
  // 1.0 = nol o'sish; ±20% chekka nuqtalar
  return performanceColor(1 + clamp(yoy, -20, 20) / 20 * 0.18);
}
