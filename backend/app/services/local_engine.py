"""Claude API kalitisiz ishlaydigan zaxira analitik dvigatel.

Xuddi Claude yo'lidagi kabi javob bazadagi yozuvlardan quriladi — farqi
shundaki, matn oldindan belgilangan shablonlar bo'yicha yig'iladi.
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.schemas import AiInsight, ChatResponse, Recommendation
from app.services import analytics as an
from app.services import charts as ch

MODULE_KEYWORDS = {
    "inflation": ["inflyatsiya", "inflatsiya", "narx", "qimmatchilik"],
    "industry": ["sanoat", "ishlab chiqarish", "zavod", "korxona"],
    "agriculture": ["qishloq", "dehqon", "hosil", "ekin", "sug'orish", "paxta", "agro"],
    "investment": ["investitsiya", "sarmoya", "investor"],
    "export": ["eksport", "tashqi savdo", "xorij"],
    "employment": ["bandlik", "ish o'rni", "ishsizlik", "mehnat"],
    "construction": ["qurilish", "uy-joy", "obyekt"],
    "services": ["xizmat", "turizm", "savdo"],
}

INTENT_KEYWORDS: list[tuple[str, list[str]]] = [
    ("recommend", ["tavsiya", "taklif", "nima qil", "yechim", "chora", "harakat rejasi"]),
    ("weak", ["muammo", "zaif", "kritik", "ortda", "xavf", "past", "bajarilmagan"]),
    ("compare", ["solishtir", "taqqosla", "reyting", "eng yaxshi", "qaysi tuman"]),
    ("annual", ["yillik", "bir yil", "hisobot", "yakun", "umumiy tahlil"]),
]

PLAYBOOK: dict[str, list[Recommendation]] = {
    "agriculture": [
        Recommendation(
            horizon="short",
            title="Suvni tejash rejimiga o'tish (1–3 oy)",
            actions=[
                "Ko'p suv talab qiladigan maydonlarni inventarizatsiya qilish va limitni qayta taqsimlash",
                "Tomchilatib sug'orish uskunalarini subsidiyalangan lizingga chiqarish",
                "Kanallardagi filtratsiya yo'qotishlarini bartaraf etish",
            ],
            impact="Sug'orish suvi sarfini 12–18% ga qisqartirish",
        ),
        Recommendation(
            horizon="mid",
            title="Ekin tuzilmasini qayta ko'rib chiqish (6 oy)",
            actions=[
                "Suvtalab ekinlarni sho'rga chidamli navlarga almashtirish",
                "Kollektor-drenaj tarmog'ini tozalash grafigini tuzish",
                "Fermerlar bilan kafolatlangan xarid shartnomalari",
            ],
            impact="1 gektardan olinadigan daromadni 15–20% ga oshirish",
        ),
        Recommendation(
            horizon="long",
            title="Qayta ishlash zanjirini qurish (1 yil)",
            actions=[
                "Quritish va konservalash sexlarini ishga tushirish",
                "Sovutgichli omborxonalar tarmog'ini kengaytirish",
                "Organik sertifikatlash orqali eksport bozoriga chiqish",
            ],
            impact="Qo'shilgan qiymatni va eksport narxini oshirish",
        ),
    ],
    "export": [
        Recommendation(
            horizon="short",
            title="Logistika xarajatlarini pasaytirish (1–3 oy)",
            actions=[
                "Kichik eksportchilarni birlashtirib konsolidatsiyalangan jo'natish",
                "Bojxona rasmiylashtiruvi muddatlarini qisqartirish",
                "Sertifikatlashda «yagona darcha» xizmatini kengaytirish",
            ],
            impact="Bir tonna yukning logistika tannarxini 8–12% ga kamaytirish",
        ),
        Recommendation(
            horizon="mid",
            title="Bozorlarni diversifikatsiya qilish (6 oy)",
            actions=[
                "Yangi yo'nalishlarda savdo uylarini ochish",
                "Eksportchilarga imtiyozli aylanma mablag' krediti",
                "Xalqaro ko'rgazmalarda ishtirok",
            ],
            impact="Bitta bozorga bog'liqlikni 30% ga kamaytirish",
        ),
        Recommendation(
            horizon="long",
            title="Transport-logistika markazi (1 yil)",
            actions=[
                "Zamonaviy logistika markazini qurish",
                "Sovutgichli konteynerlar parkini shakllantirish",
                "Ishlab chiqarish quvvatlarini kengaytirish",
            ],
            impact="Yillik eksport hajmini 20–25% ga oshirish",
        ),
    ],
}

DEFAULT_PLAYBOOK = [
    Recommendation(
        horizon="short",
        title="Joriy holatni barqarorlashtirish (1–3 oy)",
        actions=[
            "Ortda qolish sabablarini kesim bo'yicha aniqlash va mas'ul belgilash",
            "Haftalik monitoring jadvalini yo'lga qo'yish",
            "Zaxira resurslarni eng muammoli yo'nalishga yo'naltirish",
        ],
        impact="Ko'rsatkichning keyingi pasayishini to'xtatish",
    ),
    Recommendation(
        horizon="mid",
        title="Tizimli chora-tadbirlar (6 oy)",
        actions=[
            "Sohaga yo'naltirilgan qo'llab-quvvatlash dasturini ishga tushirish",
            "Kadrlar va texnik ta'minotni kuchaytirish",
            "Xususiy sektor bilan hamkorlik loyihalarini boshlash",
        ],
        impact="Reja bajarilishini 90% dan yuqori darajaga chiqarish",
    ),
    Recommendation(
        horizon="long",
        title="Barqaror o'sish asosini yaratish (1 yil)",
        actions=[
            "Infratuzilma va modernizatsiya loyihalarini yakunlash",
            "Investitsiya jalb qilish bo'yicha aniq maqsadli ish",
            "Natijalarni yillik hisobotda mustahkamlash",
        ],
        impact="Sohani barqaror o'sish traektoriyasiga olib chiqish",
    ),
]


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().replace("ʻ", "'").replace("ʼ", "'")).strip()


def _unique_districts(spots: list[dict], limit: int) -> list[str]:
    """
    Zaif kesimlar ro'yxatidan takrorlanmaydigan tuman kodlari.

    Bitta tuman haqidagi so'rovda `spots` o'sha tumanning bir necha sohasidan
    iborat bo'ladi — tuman kodi bir necha marta takrorlanadi. Frontend esa
    "javob bitta hududga tegishlimi?" degan qarorni shu ro'yxat uzunligiga
    qarab qabul qiladi, shuning uchun takrorlar bu yerda olib tashlanadi.
    """
    return list(dict.fromkeys(s["district_id"] for s in spots))[:limit]


def parse(db: Session, prompt: str) -> tuple[str, str | None, str | None]:
    q = _normalize(prompt)

    district_id = None
    for did, d in an.district_map(db).items():
        stem = _normalize(d.name).replace("'", "")[:5]
        if stem and stem in q.replace("'", ""):
            district_id = did
            break

    module_id = None
    for mid, keys in MODULE_KEYWORDS.items():
        if any(k in q for k in keys):
            module_id = mid
            break

    intent = "overview"
    for name, keys in INTENT_KEYWORDS:
        if any(k in q for k in keys):
            intent = name
            break
    if intent == "overview":
        if district_id:
            intent = "district"
        elif module_id:
            intent = "module"

    return intent, district_id, module_id


def answer(
    db: Session,
    prompt: str,
    *,
    district_id: str | None = None,
    module_id: str | None = None,
    year: int | None = None,
) -> ChatResponse:
    year = year or an.latest_year(db)
    intent, parsed_district, parsed_module = parse(db, prompt)
    district_id = parsed_district or district_id
    module_id = parsed_module or module_id

    mods = an.module_map(db)
    dists = an.district_map(db)
    sources = len(an.fetch(db, year=year))
    spots = an.weak_spots(db, year, module_id=module_id, district_id=district_id, limit=8)

    charts = []
    recommendations: list[Recommendation] = []
    insight = None

    if intent == "recommend":
        target = spots[0] if spots else None
        mid = module_id or (target["module_id"] if target else next(iter(mods)))
        where = dists[district_id].name + " tumani" if district_id else "respublika"
        perf = f"{target['performance'] * 100:.1f}%" if target else "—"
        text = (
            f"**{where} · {mods[mid].name} — harakatlar rejasi**\n\n"
            + (
                f"Joriy holat: bajarilish **{perf}**."
                + (f" Bazadagi izoh: _{target['note']}_" if target and target.get("note") else "")
                if target
                else "Joriy holat baza ma'lumotlariga ko'ra reja doirasida."
            )
            + "\n\nQuyida bazadagi ko'rsatkichlar asosida 3 bosqichli reja keltirilgan."
        )
        recommendations = PLAYBOOK.get(mid, DEFAULT_PLAYBOOK)
        charts = [
            c
            for c in [
                ch.build(db, "dynamics", module_id=mid, district_id=district_id, year=year),
                ch.build(db, "profile", module_id=mid, district_id=district_id, year=year)
                if district_id
                else ch.build(db, "deviation", module_id=mid, district_id=None, year=year),
            ]
            if c
        ]

    elif intent == "weak":
        if spots:
            lines = "\n".join(
                f"{i + 1}. **{s['district_name']}** — {s['module_name'].lower()}: "
                f"bajarilish **{s['performance'] * 100:.1f}%**"
                + (f"\n   ↳ _{s['note']}_" if s.get("note") else "")
                for i, s in enumerate(spots[:6])
            )
            critical = sum(1 for s in spots if s["status"] == "critical")
            text = (
                f"**Muammoli sohalar — {year}-yil**\n\n"
                f"Reja va amaldagi ko'rsatkichlarni solishtirish natijasida **{len(spots)} ta** "
                f"ortda qolayotgan kesim aniqlandi, shundan **{critical} tasi kritik** holatda.\n\n"
                f"{lines}"
            )
            insight = AiInsight(
                headline=f"{spots[0]['district_name']} tumanida {spots[0]['module_name'].lower()} xavf ostida",
                body=spots[0].get("note") or f"Bajarilish {spots[0]['performance'] * 100:.1f}%.",
                severity=spots[0]["status"],
                districts=[s["district_id"] for s in spots[:5]],
                module_id=spots[0]["module_id"],
            )
        else:
            text = f"{year}-yil bo'yicha rejadan sezilarli ortda qolgan yo'nalish topilmadi."
        charts = [
            c
            for c in [
                ch.build(db, "deviation", module_id=module_id, district_id=None, year=year),
                ch.build(
                    db,
                    "dynamics",
                    module_id=spots[0]["module_id"] if spots else module_id,
                    district_id=spots[0]["district_id"] if spots else district_id,
                    year=year,
                ),
            ]
            if c
        ]

    elif intent == "compare":
        rank = an.district_scores(db, module_id, year)
        top = rank[:3]
        bottom = list(reversed(rank[-3:]))
        text = (
            f"**Tumanlar reytingi — {year}-yil**\n\n**Yetakchilar:**\n"
            + "\n".join(f"{i + 1}. {t['name']} — **{t['performance'] * 100:.1f}%**" for i, t in enumerate(top))
            + "\n\n**Ortda qolayotganlar:**\n"
            + "\n".join(f"{i + 1}. {t['name']} — **{t['performance'] * 100:.1f}%**" for i, t in enumerate(bottom))
        )
        charts = [
            c
            for c in [
                ch.build(db, "deviation", module_id=module_id, district_id=None, year=year),
                ch.build(db, "comparison", module_id=module_id, district_id=None, year=year)
                if module_id
                else ch.build(db, "structure", module_id=None, district_id=None, year=year),
            ]
            if c
        ]

    elif intent == "district" and district_id:
        p = an.district_profile(db, district_id, year)
        ordered = sorted(p["modules"], key=lambda m: m["performance"])
        worst, best = ordered[0], ordered[-1]
        text = (
            f"**{p['district']['name']} — {year}-yil kesimi**\n\n"
            f"Markaz: {p['district']['center']} · Aholi: {p['district']['population']:g} ming\n\n"
            f"Umumiy bajarilish **{p['overall'] * 100:.1f}%**. Eng kuchli yo'nalish — "
            f"**{best['name'].lower()}** ({best['performance'] * 100:.1f}%), eng zaif — "
            f"**{worst['name'].lower()}** ({worst['performance'] * 100:.1f}%)."
        )
        insight = AiInsight(
            headline=f"{p['district']['name']}: {worst['name'].lower()} bo'yicha {worst['performance'] * 100:.1f}%",
            body=f"Umumiy bajarilish {p['overall'] * 100:.1f}%.",
            severity=p["status"],
            districts=[district_id],
            module_id=worst["module_id"],
        )
        charts = [
            c
            for c in [
                ch.build(db, "profile", module_id=None, district_id=district_id, year=year),
                ch.build(db, "dynamics", module_id=worst["module_id"], district_id=district_id, year=year),
            ]
            if c
        ]

    elif intent == "module" and module_id:
        m = mods[module_id]
        agg = an.rollup(an.fetch(db, module_id=module_id, district_id=district_id, year=year), m.lower_is_better)
        growth = an.yoy_growth(db, module_id, district_id)
        where = dists[district_id].name + " tumani" if district_id else "Respublika"
        text = (
            f"**{m.name} — {where}, {year}-yil**\n\n"
            f"Amaldagi hajm **{agg.fact:g} {m.unit}**, reja **{agg.plan:g} {m.unit}** — "
            f"bajarilish **{agg.ratio * 100:.1f}%**.\n\n"
            f"O'tgan yilga nisbatan o'zgarish: **{growth:+.1f}%**."
        )
        charts = [
            c
            for c in [
                ch.build(db, "dynamics", module_id=module_id, district_id=district_id, year=year),
                ch.build(db, "comparison", module_id=module_id, district_id=None, year=year),
            ]
            if c
        ]

    else:  # annual / overview
        stats = an.headline_stats(db, module_id, year)
        rank = an.district_scores(db, module_id, year)
        text = (
            f"**Qoraqalpog'iston Respublikasi — {year}-yil umumiy manzara**\n\n"
            f"Bazada {stats['records']} ta ko'rsatkich yozuvi mavjud. "
            f"O'rtacha bajarilish **{stats['performance'] * 100:.1f}%**, "
            f"real sektorda o'sish **{stats['growth']:+.1f}%**.\n\n"
            f"Yetakchi — **{rank[0]['name']}** ({rank[0]['performance'] * 100:.1f}%), "
            f"ortda — **{rank[-1]['name']}** ({rank[-1]['performance'] * 100:.1f}%). "
            f"Kritik kesimlar: **{stats['critical']} ta**, xavf ostida: **{stats['at_risk']} ta**."
        )
        if spots:
            insight = AiInsight(
                headline=f"{spots[0]['district_name']} tumanida {spots[0]['module_name'].lower()} xavf ostida",
                body=spots[0].get("note") or "Reja bajarilishi 90% dan past.",
                severity=spots[0]["status"],
                districts=_unique_districts(spots, 4),
                module_id=spots[0]["module_id"],
            )
        charts = [
            c
            for c in [
                ch.build(db, "structure", module_id=None, district_id=None, year=year),
                ch.build(db, "growth", module_id=None, district_id=None, year=year),
                ch.build(db, "deviation", module_id=None, district_id=None, year=year),
            ]
            if c
        ]

    return ChatResponse(
        text=text,
        charts=charts,
        insight=insight,
        recommendations=recommendations,
        sources=sources,
        highlight=_unique_districts(spots, 5),
        engine="local",
    )
