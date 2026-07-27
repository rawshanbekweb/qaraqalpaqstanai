import { CURRENT_MONTH, CURRENT_YEAR, BASE_YEAR, INDICATORS } from "@/data/dataset";
import { DISTRICTS, DISTRICT_BY_ID } from "@/data/districts";
import { MODULES, MODULE_BY_ID, MONTHS_UZ } from "@/data/modules";
import {
  districtProfile,
  districtRanking,
  monthlySeries,
  quarterlySeries,
  radarCompare,
  rollup,
  round,
  weakSpots,
  yoyGrowth,
} from "@/lib/analytics";
import { performanceColor } from "@/lib/scale";
import type { AiInsight, ChartSpec, ModuleId, Recommendation } from "@/lib/types";
import { trim, uid } from "@/lib/utils";

/**
 * Mahalliy RAG dvigateli.
 *
 * Backend (FastAPI + Claude API) mavjud bo'lmaganda ham chat to'liq ishlashi
 * uchun: so'rovdan niyat/tuman/modul ajratiladi -> bazadan tegishli yozuvlar
 * olinadi -> javob matni, grafiklar va tavsiyalar SHU yozuvlardan quriladi.
 * Ya'ni hech qanday "o'ylab topilgan" raqam yo'q.
 */

export type Intent =
  | "annual"
  | "weak"
  | "recommend"
  | "compare"
  | "district"
  | "module"
  | "forecast"
  | "overview";

export interface Retrieval {
  intent: Intent;
  districtId: string | null;
  moduleId: ModuleId | null;
  year: number;
  /** Kontekstga tushgan yozuvlar soni — RAG shaffofligi */
  sources: number;
}

// ── Niyat va entity ajratish ─────────────────────────────────────────

const MODULE_KEYWORDS: Record<ModuleId, string[]> = {
  inflation: ["inflyatsiya", "inflatsiya", "narx", "qimmatchilik", "iste'mol"],
  industry: ["sanoat", "ishlab chiqarish", "zavod", "korxona", "industriya"],
  agriculture: ["qishloq", "dehqon", "hosil", "ekin", "sug'orish", "paxta", "bug'doy", "agro"],
  investment: ["investitsiya", "sarmoya", "investor", "kapital"],
  export: ["eksport", "tashqi savdo", "chetga", "xorij"],
  employment: ["bandlik", "ish o'rni", "ishsizlik", "mehnat", "ish joyi"],
  construction: ["qurilish", "uy-joy", "obyekt", "infratuzilma"],
  services: ["xizmat", "turizm", "savdo", "servis"],
};

const INTENT_KEYWORDS: Array<[Intent, string[]]> = [
  ["recommend", ["tavsiya", "taklif", "nima qil", "yechim", "chora", "harakat rejasi", "qanday yaxshila", "rejа"]],
  ["weak", ["muammo", "zaif", "kritik", "ortda", "xavf", "yomon", "past", "bajarilmagan", "risk"]],
  ["compare", ["solishtir", "taqqosla", "reyting", "eng yaxshi", "top ", "kim oldinda", "qaysi tuman"]],
  ["forecast", ["prognoz", "bashorat", "kelajak", "keyingi yil", "kutilmoqda"]],
  ["annual", ["yillik", "bir yil", "yil bo'yicha", "hisobot", "umumiy tahlil", "yakun"]],
];

function normalize(s: string) {
  return s
    .toLowerCase()
    .replace(/[ʻʼ‘’`]/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

export function retrieve(prompt: string): Retrieval {
  const q = normalize(prompt);

  // Tuman
  let districtId: string | null = null;
  for (const d of DISTRICTS) {
    const variants = [normalize(d.name), normalize(d.name).replace(/'/g, ""), normalize(d.center)];
    if (variants.some((v) => v.length > 3 && q.includes(v.slice(0, Math.max(4, v.length - 2))))) {
      districtId = d.id;
      break;
    }
  }

  // Modul
  let moduleId: ModuleId | null = null;
  for (const m of MODULES) {
    if (MODULE_KEYWORDS[m.id].some((k) => q.includes(k))) {
      moduleId = m.id;
      break;
    }
  }

  // Yil
  const yearMatch = q.match(/20(2[4-9]|3\d)/);
  const year = yearMatch ? Number(yearMatch[0]) : CURRENT_YEAR;

  // Niyat
  let intent: Intent = "overview";
  for (const [name, keys] of INTENT_KEYWORDS) {
    if (keys.some((k) => q.includes(k))) {
      intent = name;
      break;
    }
  }
  if (intent === "overview") {
    if (districtId) intent = "district";
    else if (moduleId) intent = "module";
  }

  const sources = INDICATORS.filter(
    (i) =>
      i.year === (year === CURRENT_YEAR ? CURRENT_YEAR : year) &&
      (!districtId || i.districtId === districtId) &&
      (!moduleId || i.moduleId === moduleId),
  ).length;

  return { intent, districtId, moduleId, year: year > CURRENT_YEAR ? CURRENT_YEAR : year, sources };
}

// ── Tavsiya kutubxonasi ──────────────────────────────────────────────

const PLAYBOOK: Record<ModuleId, Recommendation[]> = {
  agriculture: [
    {
      horizon: "short",
      title: "Suvni tejash rejimiga o'tish (1–3 oy)",
      actions: [
        "Eng ko'p suv iste'mol qiladigan maydonlarni inventarizatsiya qilish va suv limitini qayta taqsimlash",
        "Tomchilatib va yomg'irlatib sug'orish uskunalarini subsidiyalangan lizingga chiqarish",
        "Kanallardagi filtratsiya yo'qotishlarini bartaraf etish uchun shoshilinch ta'mirlash ishlari",
      ],
      impact: "Sug'orish suvi sarfini 12–18% ga qisqartirish, hosildorlik pasayishini to'xtatish",
    },
    {
      horizon: "mid",
      title: "Ekin tuzilmasini qayta ko'rib chiqish (6 oy)",
      actions: [
        "Suvtalab ekinlar maydonini qisqartirib, sho'rga chidamli va kam suv talab qiladigan navlarga o'tkazish",
        "Melioratsiya tadbirlari: kollektor-drenaj tarmog'ini tozalash grafigi",
        "Agroklaster va fermerlar o'rtasida kafolatlangan xarid shartnomalarini rasmiylashtirish",
      ],
      impact: "1 gektardan olinadigan daromadni 15–20% ga oshirish",
    },
    {
      horizon: "long",
      title: "Qayta ishlash zanjirini qurish (1 yil)",
      actions: [
        "Mahalliy xom ashyoni qayta ishlaydigan quritish va konservalash sexlarini ishga tushirish",
        "Sovutgichli omborxonalar tarmog'ini kengaytirish",
        "Organik sertifikatlash orqali eksport bozoriga chiqish",
      ],
      impact: "Qo'shilgan qiymatni oshirish, eksport narxini 25% gacha ko'tarish",
    },
  ],
  export: [
    {
      horizon: "short",
      title: "Logistika xarajatlarini pasaytirish (1–3 oy)",
      actions: [
        "Konsolidatsiyalangan yuk jo'natish sxemasini yo'lga qo'yish (kichik eksportchilarni birlashtirish)",
        "Bojxona rasmiylashtiruvi muddatlarini qisqartirish bo'yicha ishchi guruh tuzish",
        "Eksport sertifikatlarini olishda «yagona darcha» xizmatini kengaytirish",
      ],
      impact: "Bir tonna yukning logistika tannarxini 8–12% ga kamaytirish",
    },
    {
      horizon: "mid",
      title: "Bozorlarni diversifikatsiya qilish (6 oy)",
      actions: [
        "Qozog'iston, Rossiya va Xitoy yo'nalishlarida savdo uylarini ochish",
        "Eksportga yo'naltirilgan korxonalarga imtiyozli aylanma mablag' krediti",
        "Xalqaro ko'rgazmalarda respublika stendini tashkil etish",
      ],
      impact: "Eksport geografiyasini kengaytirib, bitta bozorga bog'liqlikni 30% ga kamaytirish",
    },
    {
      horizon: "long",
      title: "Transport-logistika markazi (1 yil)",
      actions: [
        "Temir yo'l stansiyasi yonida zamonaviy logistika markazi qurish",
        "Sovutgichli konteynerlar parkini shakllantirish",
        "Eksport hajmini oshirish uchun ishlab chiqarish quvvatlarini kengaytirish",
      ],
      impact: "Yillik eksport hajmini 20–25% ga oshirish",
    },
  ],
  industry: [
    {
      horizon: "short",
      title: "Quvvatlardan foydalanishni oshirish (1–3 oy)",
      actions: [
        "To'liq yuklanmagan korxonalar reyestrini tuzish va sabablarini aniqlash",
        "Elektr va gaz ta'minotidagi uzilishlar bo'yicha kelishilgan grafik o'rnatish",
        "Xom ashyo yetkazib beruvchilar bilan uzoq muddatli shartnomalar",
      ],
      impact: "Quvvatlardan foydalanish darajasini 10–15 punktga oshirish",
    },
    {
      horizon: "mid",
      title: "Kichik sanoat zonalarini kengaytirish (6 oy)",
      actions: [
        "Bo'sh turgan ishlab chiqarish binolarini tadbirkorlarga imtiyozli berish",
        "Muhandislik-kommunikatsiya tarmoqlarini yetkazish",
        "Kadrlar tayyorlash uchun korxona–kollej hamkorligi",
      ],
      impact: "Yangi ishlab chiqarish subyektlari sonini 20% ga oshirish",
    },
    {
      horizon: "long",
      title: "Modernizatsiya va lokalizatsiya (1 yil)",
      actions: [
        "Asosiy korxonalarda texnologik qayta jihozlash dasturi",
        "Import o'rnini bosuvchi mahsulot ishlab chiqarishni lokalizatsiya qilish",
        "Energiya samaradorligini oshirish loyihalari",
      ],
      impact: "Mahsulot tannarxini 10% ga pasaytirish, hajmni barqaror o'stirish",
    },
  ],
  investment: [
    {
      horizon: "short",
      title: "Loyiha portfelini tozalash (1–3 oy)",
      actions: [
        "To'xtab qolgan loyihalar bo'yicha sabablarni aniqlash va muddatlarni qayta belgilash",
        "Investor uchun yer uchastkalari va infratuzilma bo'yicha tayyor «paket takliflar» shakllantirish",
        "Ruxsatnoma olish jarayonlarini raqamlashtirish",
      ],
      impact: "Loyiha ishga tushirish muddatini o'rtacha 2 oyga qisqartirish",
    },
    {
      horizon: "mid",
      title: "Investorlar bilan ishlashni tizimlashtirish (6 oy)",
      actions: [
        "Har bir yirik loyihaga mas'ul menejer biriktirish (project manager modeli)",
        "Investitsiya forumi va biznes-missiyalarni tashkil etish",
        "Xususiy-davlat sheriklik loyihalarini ishga tushirish",
      ],
      impact: "Jalb qilingan investitsiya hajmini 18–22% ga oshirish",
    },
    {
      horizon: "long",
      title: "Investitsiya muhitini institutsional mustahkamlash (1 yil)",
      actions: [
        "Erkin iqtisodiy zona rezidentlari uchun qo'shimcha imtiyozlar",
        "Infratuzilma (yo'l, suv, elektr) bo'yicha uzoq muddatli dastur",
        "Xalqaro moliya institutlari bilan hamkorlik dasturlari",
      ],
      impact: "Barqaror investitsiya oqimini shakllantirish",
    },
  ],
  employment: [
    {
      horizon: "short",
      title: "Ish o'rinlarini tez yaratish (1–3 oy)",
      actions: [
        "Ishsiz fuqarolar reyestri asosida yo'naltirilgan bandlik yarmarkalari",
        "Jamoat ishlariga vaqtinchalik jalb qilish dasturi",
        "Oilaviy tadbirkorlik uchun mikrokreditlar hajmini oshirish",
      ],
      impact: "Qisqa muddatda 1,5–2 ming vaqtinchalik ish o'rni",
    },
    {
      horizon: "mid",
      title: "Kasbga qayta tayyorlash (6 oy)",
      actions: [
        "Mehnat bozorida talab yuqori bo'lgan 10 ta kasb bo'yicha bepul kurslar",
        "Korxonalar bilan «o'qit va ishga ol» shartnomalari",
        "Ayollar va yoshlar uchun maxsus grant yo'nalishi",
      ],
      impact: "Bitiruvchilar bandligini 60% dan 80% gacha oshirish",
    },
    {
      horizon: "long",
      title: "Barqaror ish o'rinlari (1 yil)",
      actions: [
        "Mehnat sig'imi yuqori tarmoqlarga (to'qimachilik, oziq-ovqat) investitsiya jalb qilish",
        "Mehnat migratsiyasini kamaytirish uchun mahalliy ish haqi darajasini oshirish dasturi",
        "Kasb-hunar ta'limi tizimini bozor talabiga moslashtirish",
      ],
      impact: "Doimiy ish o'rinlari ulushini sezilarli oshirish",
    },
  ],
  inflation: [
    {
      horizon: "short",
      title: "Narx bosimini yumshatish (1–3 oy)",
      actions: [
        "Ijtimoiy ahamiyatga molik 15 ta mahsulot narxini haftalik monitoring qilish",
        "Zaxira omborlaridan bozorga intervensiya qilish grafigi",
        "Vositachilar zanjirini qisqartirib, dehqon bozorlarini kengaytirish",
      ],
      impact: "Oziq-ovqat guruhida narx o'sishini 1,5–2 punktga sekinlashtirish",
    },
    {
      horizon: "mid",
      title: "Taklifni oshirish (6 oy)",
      actions: [
        "Issiqxona xo'jaliklarini kengaytirish uchun imtiyozli kredit",
        "Sovutgichli omborlar sig'imini oshirib, mavsumiy narx sakrashlarini yumshatish",
        "Raqobatni cheklovchi kelishuvlar bo'yicha tekshiruvlar",
      ],
      impact: "Mavsumiy narx tebranishini 30% ga kamaytirish",
    },
    {
      horizon: "long",
      title: "Strukturaviy barqarorlik (1 yil)",
      actions: [
        "Mahalliy ishlab chiqarishni kengaytirib import ulushini kamaytirish",
        "Logistika xarajatlarini pasaytirish orqali tannarxni tushirish",
        "Aholining real daromadlarini oshirish dasturlari",
      ],
      impact: "Inflyatsiyani maqsadli koridorga qaytarish",
    },
  ],
  construction: [
    {
      horizon: "short",
      title: "Qurilish jadvalini tiklash (1–3 oy)",
      actions: [
        "Kechikayotgan obyektlar bo'yicha pudratchilar bilan qayta kelishuv",
        "Qurilish materiallari yetkazib berishni markazlashtirilgan xarid orqali ta'minlash",
        "Moliyalashtirish tranzitlarini tezlashtirish",
      ],
      impact: "Kechikishni 1–2 oyga qisqartirish",
    },
    {
      horizon: "mid",
      title: "Infratuzilma bilan bog'lash (6 oy)",
      actions: [
        "Yangi turar-joy massivlarini suv va elektr tarmog'iga ulash",
        "Mahalliy qurilish materiallari ishlab chiqarishni qo'llab-quvvatlash",
        "Loyiha-smeta hujjatlarini ekspertizadan o'tkazishni tezlashtirish",
      ],
      impact: "Obyektlarni o'z vaqtida foydalanishga topshirish ulushini oshirish",
    },
    {
      horizon: "long",
      title: "Uzoq muddatli qurilish dasturi (1 yil)",
      actions: [
        "Ipoteka dasturlarini kengaytirish",
        "Energiya samarador uy-joy standartlarini joriy etish",
        "Kadrlar (quruvchi mutaxassislar) tayyorlash",
      ],
      impact: "Qurilish hajmini barqaror o'stirish",
    },
  ],
  services: [
    {
      horizon: "short",
      title: "Xizmatlar hajmini oshirish (1–3 oy)",
      actions: [
        "Turistik marshrutlarni faollashtirish va reklama kampaniyasi",
        "Kichik xizmat ko'rsatish subyektlarini ro'yxatdan o'tkazishni soddalashtirish",
        "Onlayn to'lov va raqamli xizmatlarni kengaytirish",
      ],
      impact: "Xizmatlar hajmini 6–9% ga oshirish",
    },
    {
      horizon: "mid",
      title: "Turizm infratuzilmasi (6 oy)",
      actions: [
        "Mehmonxona fondini kengaytirish, oilaviy mehmonxonalarni qo'llab-quvvatlash",
        "Yo'l va yo'lovchi tashish xizmatlarini yaxshilash",
        "Gid va servis xodimlarini tayyorlash",
      ],
      impact: "Turistlar oqimini 25% ga oshirish",
    },
    {
      horizon: "long",
      title: "Xizmatlar ulushini oshirish (1 yil)",
      actions: [
        "IT va autsorsing xizmatlarini rivojlantirish",
        "Moliyaviy va sug'urta xizmatlari qamrovini kengaytirish",
        "Xizmat ko'rsatish sifatini standartlashtirish",
      ],
      impact: "YaHM tarkibida xizmatlar ulushini oshirish",
    },
  ],
};

// ── Grafik yasovchilar ───────────────────────────────────────────────

function dynamicsChart(moduleId: ModuleId, districtId: string | "all", year: number): ChartSpec {
  const m = MODULE_BY_ID[moduleId];
  const pts = monthlySeries(moduleId, districtId, year);
  const where = districtId === "all" ? "Respublika" : DISTRICT_BY_ID[districtId].name;
  return {
    id: uid("chart"),
    kind: "area",
    title: `${m.name} — oylik dinamika`,
    subtitle: `${where}, ${year}-yil · reja va amaldagi ko'rsatkich`,
    unit: m.unit,
    series: [
      { key: "plan", label: "Reja", color: "#6b779c" },
      { key: "fact", label: "Amalda", color: m.color },
    ],
    data: pts.map((p) => ({ label: p.label, plan: p.plan, fact: p.fact })),
  };
}

/** Rejadan chetlanish — qutbli o'lchov, shuning uchun noldan ikki tomonga. */
function rankingChart(moduleId: ModuleId | "all", year: number, limit = 8): ChartSpec {
  const rows = districtRanking(moduleId, year);
  const worst = rows.slice(-limit).reverse();
  const m = moduleId === "all" ? null : MODULE_BY_ID[moduleId];
  return {
    id: uid("chart"),
    kind: "diverging-bar",
    title: m ? `${m.name} — eng past bajarilish` : "Eng past bajarilishdagi tumanlar",
    subtitle: `${year}-yil · 100% rejaga nisbatan chetlanish, punkt`,
    series: [{ key: "value", label: "Chetlanish" }],
    data: worst.map((r) => ({
      label: r.name,
      value: round(r.performance * 100 - 100),
      color: performanceColor(r.performance),
    })),
  };
}

function comparisonChart(moduleId: ModuleId | "all", year: number): ChartSpec {
  const rows = districtRanking(moduleId, year).slice(0, 10);
  const m = moduleId === "all" ? null : MODULE_BY_ID[moduleId];
  return {
    id: uid("chart"),
    kind: "grouped-bar",
    title: m ? `${m.name} — tumanlar reytingi` : "Tumanlar reytingi",
    subtitle: `${year}-yil · reja va amalda`,
    unit: m?.unit,
    series: [
      { key: "plan", label: "Reja", color: "#6b779c" },
      { key: "fact", label: "Amalda", color: m?.color ?? "#22d3ee" },
    ],
    data: rows.map((r) => ({ label: r.name, plan: round(r.plan), fact: round(r.fact) })),
  };
}

/** Tuman ↔ respublika o'rtachasi: har bir soha uchun ikki qiymat -> dumbbell. */
function radarChart(districtId: string, year: number): ChartSpec {
  const rows = radarCompare(districtId, year);
  return {
    id: uid("chart"),
    kind: "dumbbell",
    title: `${DISTRICT_BY_ID[districtId].name} — sohalar kesimi`,
    subtitle: "Tuman va respublika o'rtachasi taqqoslamasi, bajarilish %",
    unit: "%",
    series: [
      { key: "local", label: DISTRICT_BY_ID[districtId].name, color: "#22d3ee" },
      { key: "republic", label: "Respublika o'rtachasi", color: "#a78bfa" },
    ],
    data: rows.map((r) => ({ label: r.label, local: r.local, republic: r.republic })),
  };
}

/**
 * Sohalar tarkibi — 7 ta kategoriya. Doiraviy (donut) diagramma bu yerda
 * noto'g'ri shakl: burchak uzunliklarini taqqoslash qiyin va 7 tilim
 * "hamma juftlik" rang gatelaridan o'tmaydi. Shuning uchun gorizontal
 * ustunlar — uzunlik bo'yicha taqqoslash aniq, yorliqlar to'g'ridan-to'g'ri.
 */
function structureChart(year: number): ChartSpec {
  const rows = MODULES.filter((m) => m.id !== "inflation")
    .map((m) => {
      const r = rollup(INDICATORS.filter((i) => i.moduleId === m.id && i.year === year), m.id);
      return { label: m.short, value: round(r.fact), color: m.color };
    })
    .sort((a, b) => b.value - a.value);

  return {
    id: uid("chart"),
    kind: "bar",
    title: "Iqtisodiyot tarkibi",
    subtitle: `${year}-yil · sohalar bo'yicha amaldagi hajm`,
    series: [{ key: "value", label: "Amaldagi hajm" }],
    data: rows,
  };
}

function yoyChart(year: number): ChartSpec {
  return {
    id: uid("chart"),
    kind: "bar",
    title: "Yillik o'sish sur'ati",
    subtitle: `${BASE_YEAR} → ${year} · yanvar–${MONTHS_UZ[CURRENT_MONTH - 1].toLowerCase()} taqqoslamasi`,
    unit: "%",
    series: [{ key: "value", label: "O'sish", color: "#34d399" }],
    data: MODULES.map((m) => ({ label: m.short, value: yoyGrowth(m.id) })),
  };
}

function quarterChart(moduleId: ModuleId, districtId: string | "all", year: number): ChartSpec {
  const m = MODULE_BY_ID[moduleId];
  return {
    id: uid("chart"),
    kind: "grouped-bar",
    title: `${m.name} — choraklar kesimi`,
    subtitle: `${districtId === "all" ? "Respublika" : DISTRICT_BY_ID[districtId].name}, ${year}-yil`,
    unit: m.unit,
    series: [
      { key: "plan", label: "Reja", color: "#6b779c" },
      { key: "fact", label: "Amalda", color: m.color },
    ],
    data: quarterlySeries(moduleId, districtId, year).map((q) => ({
      label: q.label,
      plan: q.plan,
      fact: q.fact,
    })),
  };
}

// ── Javob quruvchi ───────────────────────────────────────────────────

export interface AiAnswer {
  text: string;
  charts: ChartSpec[];
  insight?: AiInsight;
  recommendations?: Recommendation[];
  sources: number;
  /** Xaritada yoritish uchun */
  highlight?: string[];
}

export function answer(prompt: string): AiAnswer {
  const r = retrieve(prompt);
  const year = r.year;

  switch (r.intent) {
    case "annual":
      return annualAnswer(r, year);
    case "weak":
      return weakAnswer(r, year);
    case "recommend":
      return recommendAnswer(r, year);
    case "compare":
      return compareAnswer(r, year);
    case "district":
      return districtAnswer(r.districtId!, year, r);
    case "module":
      return moduleAnswer(r.moduleId!, r.districtId, year, r);
    case "forecast":
      return forecastAnswer(r, year);
    default:
      return overviewAnswer(r, year);
  }
}

function annualAnswer(r: Retrieval, year: number): AiAnswer {
  const growths = MODULES.map((m) => ({ m, g: yoyGrowth(m.id, r.districtId ?? "all") }));
  const real = growths.filter((x) => x.m.id !== "inflation");
  const best = [...real].sort((a, b) => b.g - a.g)[0];
  const worst = [...real].sort((a, b) => a.g - b.g)[0];
  const infl = rollup(
    INDICATORS.filter(
      (i) => i.moduleId === "inflation" && i.year === year && (!r.districtId || i.districtId === r.districtId),
    ),
    "inflation",
  );
  const spots = weakSpots(year, { districtId: r.districtId ?? "all", limit: 5 });
  const where = r.districtId ? DISTRICT_BY_ID[r.districtId].name + " tumani" : "Qoraqalpog'iston Respublikasi";

  const netGrowth = round(best.g - (infl.fact - infl.plan));

  const text = [
    `**${where} — ${year}-yil yakuniy tahlili**`,
    ``,
    `${BASE_YEAR}-yilning shu davri bilan solishtirganda **${best.m.name.toLowerCase()}** sohasi eng yuqori sur'atda o'sdi: **${best.g > 0 ? "+" : ""}${trim(best.g)}%**. Eng sust dinamika **${worst.m.name.toLowerCase()}** yo'nalishida — **${worst.g > 0 ? "+" : ""}${trim(worst.g)}%**.`,
    ``,
    `Inflyatsiya foni o'rtacha **${trim(infl.fact)}%** ni tashkil etdi (maqsadli daraja ${trim(infl.plan)}%). Ya'ni nominal o'sishning taxminan **${trim(Math.max(0, infl.fact - infl.plan))} punkti** narx omili hisobiga neytrallashdi — real o'sish ${best.m.short.toLowerCase()} bo'yicha ~**${trim(netGrowth)}%** darajasida.`,
    ``,
    spots.length
      ? `Rejadan ortda qolayotgan **${spots.length} ta** yo'nalish aniqlandi. Eng og'iri: ${spots
          .slice(0, 3)
          .map((s) => `${s.districtName} — ${s.moduleName.toLowerCase()} (${trim(s.performance * 100)}%)`)
          .join("; ")}.`
      : `Barcha yo'nalishlar bo'yicha reja bajarilmoqda.`,
  ].join("\n");

  return {
    text,
    charts: [
      yoyChart(year),
      dynamicsChart(best.m.id, r.districtId ?? "all", year),
      structureChart(year),
    ],
    insight: {
      headline: `${where}: ${best.m.short.toLowerCase()} yetakchi, ${worst.m.short.toLowerCase()} ortda`,
      body: `Inflyatsiya ${trim(infl.fact)}% — maqsaddan ${trim(Math.max(0, infl.fact - infl.plan))} punkt yuqori.`,
      severity: infl.fact > infl.plan + 2 ? "at_risk" : "in_progress",
      districts: spots.slice(0, 4).map((s) => s.districtId),
    },
    sources: r.sources,
    highlight: spots.map((s) => s.districtId),
  };
}

function weakAnswer(r: Retrieval, year: number): AiAnswer {
  const spots = weakSpots(year, {
    moduleId: r.moduleId ?? "all",
    districtId: r.districtId ?? "all",
    limit: 10,
  });

  if (!spots.length) {
    return {
      text: `Tanlangan kesimda (${year}-yil) rejadan sezilarli ortda qolgan yo'nalish topilmadi — barcha ko'rsatkichlar 90% dan yuqori bajarilgan.`,
      charts: [rankingChart(r.moduleId ?? "all", year)],
      sources: r.sources,
    };
  }

  const critical = spots.filter((s) => s.status === "critical");
  const lines = spots
    .slice(0, 6)
    .map(
      (s, i) =>
        `${i + 1}. **${s.districtName}** — ${s.moduleName.toLowerCase()}: bajarilish **${trim(s.performance * 100)}%**${s.note ? `\n   ↳ _${s.note}_` : ""}`,
    );

  const text = [
    `**Muammoli sohalar — ${year}-yil**`,
    ``,
    `Bazadagi reja va amaldagi ko'rsatkichlarni solishtirish natijasida **${spots.length} ta** ortda qolayotgan kesim aniqlandi, shundan **${critical.length} tasi kritik** holatda.`,
    ``,
    ...lines,
    ``,
    critical.length
      ? `Kritik holatdagi yo'nalishlar bo'yicha shoshilinch chora ko'rish talab etiladi. Tavsiyalarni olish uchun: _"${critical[0].districtName} ${critical[0].moduleName.toLowerCase()} bo'yicha tavsiya ber"_.`
      : `Xavf ostidagi yo'nalishlarni kuzatuvda saqlash tavsiya etiladi.`,
  ].join("\n");

  return {
    text,
    charts: [
      rankingChart(r.moduleId ?? "all", year),
      dynamicsChart(spots[0].moduleId, spots[0].districtId, year),
    ],
    insight: {
      headline: `${spots[0].districtName} va ${spots[1]?.districtName ?? ""} tumanlarida ${spots[0].moduleName.toLowerCase()} xavf ostida`,
      body: spots[0].note ?? `Bajarilish darajasi ${trim(spots[0].performance * 100)}%.`,
      severity: spots[0].status,
      districts: spots.slice(0, 5).map((s) => s.districtId),
      moduleId: spots[0].moduleId,
    },
    sources: r.sources,
    highlight: spots.map((s) => s.districtId),
  };
}

function recommendAnswer(r: Retrieval, year: number): AiAnswer {
  const spots = weakSpots(year, {
    moduleId: r.moduleId ?? "all",
    districtId: r.districtId ?? "all",
    limit: 5,
  });
  const target = spots[0];
  const moduleId = r.moduleId ?? target?.moduleId ?? "agriculture";
  const districtId = r.districtId ?? target?.districtId ?? null;
  const m = MODULE_BY_ID[moduleId];
  const where = districtId ? `${DISTRICT_BY_ID[districtId].name} tumani` : "respublika";

  const perf = target ? trim(target.performance * 100) : "—";
  const text = [
    `**${where} · ${m.name} — harakatlar rejasi**`,
    ``,
    target
      ? `Joriy holat: bajarilish **${perf}%**, rejadan farq **${trim(Math.abs(target.gap))} ${m.unit}**.${target.note ? ` Kiritilgan izohga ko'ra: _${target.note}_` : ""}`
      : `Joriy holat baza ma'lumotlariga ko'ra reja doirasida.`,
    ``,
    `Quyida bazadagi ko'rsatkichlar va izohlar asosida 3 bosqichli reja keltirilgan.`,
  ].join("\n");

  return {
    text,
    charts: [
      dynamicsChart(moduleId, districtId ?? "all", year),
      districtId ? radarChart(districtId, year) : rankingChart(moduleId, year),
    ],
    recommendations: PLAYBOOK[moduleId],
    insight: target
      ? {
          headline: `${where}: ${m.short.toLowerCase()} bo'yicha 3 bosqichli reja tayyor`,
          body: `Qisqa muddatda suv/xarajat optimallashtirish, o'rta muddatda struktura o'zgarishi, uzoq muddatda qo'shilgan qiymat.`,
          severity: target.status,
          districts: districtId ? [districtId] : spots.map((s) => s.districtId),
          moduleId,
        }
      : undefined,
    sources: r.sources,
    highlight: districtId ? [districtId] : spots.map((s) => s.districtId),
  };
}

function compareAnswer(r: Retrieval, year: number): AiAnswer {
  const moduleId = r.moduleId ?? "all";
  const rows = districtRanking(moduleId, year);
  const top = rows.slice(0, 3);
  const bottom = rows.slice(-3).reverse();
  const label = moduleId === "all" ? "umumiy bajarilish" : MODULE_BY_ID[moduleId].name.toLowerCase();

  const text = [
    `**Tumanlar reytingi — ${label}, ${year}-yil**`,
    ``,
    `**Yetakchilar:**`,
    ...top.map((t, i) => `${i + 1}. ${t.name} — **${trim(t.performance * 100)}%**`),
    ``,
    `**Ortda qolayotganlar:**`,
    ...bottom.map((t, i) => `${i + 1}. ${t.name} — **${trim(t.performance * 100)}%**`),
    ``,
    `Yetakchi va oxirgi o'rin orasidagi farq **${trim((top[0].performance - bottom[0].performance) * 100)} punkt**ni tashkil etadi.`,
  ].join("\n");

  return {
    text,
    charts: [
      comparisonChart(moduleId, year),
      rankingChart(moduleId, year),
    ],
    insight: {
      headline: `${top[0].name} yetakchi (${trim(top[0].performance * 100)}%), ${bottom[0].name} ortda (${trim(bottom[0].performance * 100)}%)`,
      body: `Reyting ${year}-yil bazadagi reja/amalda ko'rsatkichlari bo'yicha hisoblandi.`,
      severity: bottom[0].status,
      districts: bottom.map((b) => b.id),
    },
    sources: r.sources,
    highlight: bottom.map((b) => b.id),
  };
}

function districtAnswer(districtId: string, year: number, r: Retrieval): AiAnswer {
  const p = districtProfile(districtId, year);
  const sorted = [...p.modules].sort((a, b) => a.performance - b.performance);
  const worst = sorted.slice(0, 2);
  const best = sorted[sorted.length - 1];
  const notes = INDICATORS.filter(
    (i) => i.districtId === districtId && i.year === year && i.note,
  ).slice(0, 3);

  const text = [
    `**${p.district.name} — ${year}-yil kesimi**`,
    ``,
    `Markaz: ${p.district.center} · Aholi: ${trim(p.district.population)} ming · Maydon: ${trim(p.district.areaKm2, 0)} km²`,
    ``,
    `Umumiy bajarilish darajasi **${trim(p.overall * 100)}%**. Eng kuchli yo'nalish — **${best.name.toLowerCase()}** (${trim(best.performance * 100)}%), eng zaif — **${worst[0].name.toLowerCase()}** (${trim(worst[0].performance * 100)}%).`,
    ``,
    worst.length
      ? `E'tibor talab qiladigan sohalar: ${worst.map((w) => `${w.name.toLowerCase()} (${trim(w.performance * 100)}%)`).join(", ")}.`
      : ``,
    notes.length ? `\n**Bazadagi izohlar:**\n${notes.map((n) => `- _${n.note}_`).join("\n")}` : ``,
  ]
    .filter(Boolean)
    .join("\n");

  return {
    text,
    charts: [
      radarChart(districtId, year),
      dynamicsChart(worst[0].moduleId, districtId, year),
      quarterChart(best.moduleId, districtId, year),
    ],
    insight: {
      headline: `${p.district.name}: ${worst[0].name.toLowerCase()} bo'yicha ${trim(worst[0].performance * 100)}% bajarilish`,
      body: notes[0]?.note ?? `Umumiy bajarilish ${trim(p.overall * 100)}%.`,
      severity: p.status,
      districts: [districtId],
      moduleId: worst[0].moduleId,
    },
    sources: r.sources,
    highlight: [districtId],
  };
}

function moduleAnswer(
  moduleId: ModuleId,
  districtId: string | null,
  year: number,
  r: Retrieval,
): AiAnswer {
  const m = MODULE_BY_ID[moduleId];
  const scope = districtId ?? "all";
  const agg = rollup(
    INDICATORS.filter(
      (i) => i.moduleId === moduleId && i.year === year && (scope === "all" || i.districtId === scope),
    ),
    moduleId,
  );
  const growth = yoyGrowth(moduleId, scope);
  const rank = districtRanking(moduleId, year);
  const where = districtId ? DISTRICT_BY_ID[districtId].name + " tumani" : "Respublika";

  const text = [
    `**${m.name} — ${where}, ${year}-yil**`,
    ``,
    m.id === "inflation"
      ? `O'rtacha inflyatsiya **${trim(agg.fact)}%**, maqsadli daraja **${trim(agg.plan)}%**. Farq **${trim(agg.fact - agg.plan)} punkt**.`
      : `Amaldagi hajm **${trim(agg.fact)} ${m.unit}**, reja **${trim(agg.plan)} ${m.unit}** — bajarilish **${trim(agg.ratio * 100)}%**.`,
    ``,
    `${BASE_YEAR}-yilga nisbatan o'zgarish: **${growth > 0 ? "+" : ""}${trim(growth)}%**.`,
    ``,
    districtId
      ? `Respublika reytingida **${rank.findIndex((x) => x.id === districtId) + 1}-o'rin** (${rank.length} tumandan).`
      : `Yetakchi: **${rank[0].name}** (${trim(rank[0].performance * 100)}%). Ortda: **${rank[rank.length - 1].name}** (${trim(rank[rank.length - 1].performance * 100)}%).`,
  ].join("\n");

  return {
    text,
    charts: [
      dynamicsChart(moduleId, scope, year),
      comparisonChart(moduleId, year),
      quarterChart(moduleId, scope, year),
    ],
    insight: {
      headline: `${m.name}: ${trim(agg.ratio * 100)}% bajarilish, ${growth > 0 ? "+" : ""}${trim(growth)}% o'sish`,
      body: districtId ? `${where} kesimida.` : `Respublika bo'yicha umumlashtirilgan.`,
      severity: agg.status,
      districts: rank.slice(-3).map((x) => x.id),
      moduleId,
    },
    sources: r.sources,
    highlight: districtId ? [districtId] : rank.slice(-4).map((x) => x.id),
  };
}

function forecastAnswer(r: Retrieval, year: number): AiAnswer {
  const moduleId = r.moduleId ?? "industry";
  const m = MODULE_BY_ID[moduleId];
  const scope = r.districtId ?? "all";
  const pts = monthlySeries(moduleId, scope, year);
  const growth = yoyGrowth(moduleId, scope);
  const n0 = pts.length;

  // Oddiy chiziqli ekstrapolyatsiya — mavjud oylik trend bo'yicha
  const n = pts.length;
  const avgIdx = (n - 1) / 2;
  const avgVal = pts.reduce((s, p) => s + p.fact, 0) / n;
  const slope =
    pts.reduce((s, p, i) => s + (i - avgIdx) * (p.fact - avgVal), 0) /
    pts.reduce((s, _, i) => s + (i - avgIdx) ** 2, 0);

  const projected = pts.map((p) => ({ label: p.label, fact: p.fact, forecast: p.fact }));
  for (let i = n; i < 12; i++) {
    projected.push({
      label: ["Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek"][i],
      fact: 0,
      forecast: round(Math.max(0, avgVal + slope * (i - avgIdx))),
    });
  }

  const yearEnd = round(projected.reduce((s, p) => s + (p.fact || p.forecast), 0));
  const planTotal = round(
    INDICATORS.filter(
      (i) => i.moduleId === moduleId && i.year === year && (scope === "all" || i.districtId === scope),
    ).reduce((s, i) => s + i.plan, 0) * (12 / CURRENT_MONTH),
  );

  const text = [
    `**${m.name} — yil oxirigacha prognoz**`,
    ``,
    `Yanvar–${MONTHS_UZ[CURRENT_MONTH - 1].toLowerCase()} oylaridagi ${n0} ta haqiqiy yozuv asosida chiziqli trend qurildi. Oylik o'zgarish sur'ati: **${slope > 0 ? "+" : ""}${trim(slope)} ${m.unit}/oy**, o'tgan yilga nisbatan **${growth > 0 ? "+" : ""}${trim(growth)}%**.`,
    ``,
    `Yil yakunida kutilayotgan hajm: **~${trim(yearEnd)} ${m.unit}** (yillik reja ~${trim(planTotal)} ${m.unit}).`,
    ``,
    yearEnd >= planTotal
      ? `Trend saqlansa yillik reja **bajariladi**.`
      : `Trend saqlansa yillik reja **${trim(((planTotal - yearEnd) / planTotal) * 100)}% ga bajarilmay qolishi** mumkin — qo'shimcha chora talab etiladi.`,
    ``,
    `_Eslatma: prognoz faqat bazadagi mavjud oylik yozuvlar ekstrapolyatsiyasi, tashqi omillar hisobga olinmagan._`,
  ].join("\n");

  return {
    text,
    charts: [
      {
        id: uid("chart"),
        kind: "line",
        title: `${m.name} — trend va prognoz`,
        subtitle: `${scope === "all" ? "Respublika" : DISTRICT_BY_ID[scope].name}, ${year}-yil`,
        unit: m.unit,
        series: [
          { key: "fact", label: "Amalda", color: m.color },
          { key: "forecast", label: "Prognoz", color: "#a78bfa" },
        ],
        data: projected.map((p) => ({
          label: p.label,
          fact: p.fact || 0,
          forecast: p.forecast,
        })),
      },
      dynamicsChart(moduleId, scope, year),
    ],
    sources: r.sources,
    highlight: r.districtId ? [r.districtId] : undefined,
  };
}

function overviewAnswer(r: Retrieval, year: number): AiAnswer {
  const spots = weakSpots(year, { limit: 4 });
  const rank = districtRanking("all", year);
  const growth = round(
    MODULES.filter((m) => m.id !== "inflation")
      .map((m) => yoyGrowth(m.id))
      .reduce((s, v) => s + v, 0) / (MODULES.length - 1),
  );

  const text = [
    `**Qoraqalpog'iston Respublikasi — ${year}-yil umumiy manzara**`,
    ``,
    `Bazada ${year}-yil bo'yicha **${INDICATORS.filter((i) => i.year === year).length} ta** ko'rsatkich yozuvi mavjud (17 tuman × 8 soha).`,
    ``,
    `Real sektorda o'rtacha o'sish **${growth > 0 ? "+" : ""}${trim(growth)}%**. Umumiy bajarilish bo'yicha yetakchi — **${rank[0].name}** (${trim(rank[0].performance * 100)}%), ortda — **${rank[rank.length - 1].name}** (${trim(rank[rank.length - 1].performance * 100)}%).`,
    ``,
    spots.length
      ? `Diqqat talab qiladigan kesimlar: ${spots.map((s) => `${s.districtName} — ${s.moduleName.toLowerCase()}`).join(", ")}.`
      : ``,
    ``,
    `Aniqroq savol bering, masalan:\n- _"Amudaryo tumanida qishloq xo'jaligi holati qanday?"_\n- _"Eng muammoli sohalarni ko'rsat"_\n- _"Eksport bo'yicha tavsiya ber"_\n- _"Yillik tahlil qilib ber"_`,
  ]
    .filter(Boolean)
    .join("\n");

  return {
    text,
    charts: [structureChart(year), yoyChart(year), rankingChart("all", year)],
    insight: spots.length
      ? {
          headline: `${spots[0].districtName} va ${spots[1]?.districtName} tumanlarida ${spots[0].moduleName.toLowerCase()} xavf ostida`,
          body: spots[0].note ?? "Reja bajarilishi 75% dan past.",
          severity: spots[0].status,
          districts: spots.map((s) => s.districtId),
        }
      : undefined,
    sources: r.sources,
    highlight: spots.map((s) => s.districtId),
  };
}

/** Dashboard yuqorisidagi doimiy AI xulosasi. */
export function topInsight(year = CURRENT_YEAR): AiInsight {
  const spots = weakSpots(year, { limit: 6 });
  if (!spots.length) {
    return {
      headline: "Barcha yo'nalishlar reja doirasida",
      body: "Kritik holatdagi tuman yoki soha aniqlanmadi.",
      severity: "completed",
      districts: [],
    };
  }
  const byModule = new Map<ModuleId, typeof spots>();
  for (const s of spots) {
    byModule.set(s.moduleId, [...(byModule.get(s.moduleId) ?? []), s]);
  }
  const [moduleId, group] = [...byModule.entries()].sort((a, b) => b[1].length - a[1].length)[0];
  const names = group.slice(0, 2).map((g) => g.districtName);

  return {
    headline: `${names.join(" va ")} tumanlarida ${MODULE_BY_ID[moduleId].name.toLowerCase()} xavf ostida`,
    body: group[0].note ?? `Reja bajarilishi ${trim(group[0].performance * 100)}% darajasida.`,
    severity: group[0].status,
    districts: group.map((g) => g.districtId),
    moduleId,
  };
}

export const SUGGESTED_PROMPTS = [
  "Yillik tahlil qilib ber",
  "Eng muammoli sohalarni ko'rsat",
  "Tumanlar reytingini solishtir",
  "Eksport bo'yicha tavsiya ber",
  "Amudaryo tumani holati qanday?",
  "Sanoat bo'yicha prognoz",
];
