"""Claude API kalitisiz ishlaydigan zaxira analitik dvigatel.

Xuddi Claude yo'lidagi kabi javob bazadagi o'lchovlardan quriladi — farqi
shundaki, matn oldindan belgilangan shablonlar bo'yicha yig'iladi.

Manba statistikada reja yo'q, shuning uchun "bajarilish %" haqida gap
bora olmaydi. O'lchov birligi: hajm, o'sish, ulush va o'rin.
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.schemas import AiInsight, ChatResponse, Recommendation
from app.services import stat_charts as ch
from app.services import stats as st
from app.text import normalize

MODULE_KEYWORDS: dict[str, list[str]] = {
    "sanaat": ["sanaat", "sanoat", "zavod", "karxana", "korxona", "islep shigariw"],
    "awil_xojaligi": [
        "awil xojaligi", "awil", "qishloq", "diyxan", "dehqon", "egin", "paxta",
        "hasil", "hosil", "agro", "suwgariw", "sugorish",
    ],
    "investitsiya": ["investitsiya", "sarmaya", "sarmoya", "investor", "kapital"],
    "qurilis": ["qurilis", "qurilish", "jay", "uy-joy", "obekt", "obyekt"],
    "xizmetler": ["xizmet", "xizmatlar", "turizm", "servis"],
    "transport": ["transport", "juk", "yuk", "tasiw", "avtomobil", "jol"],
    "sawda": ["sawda", "savdo", "satiw", "tovar", "baha", "narx", "bazar"],
}

INTENT_KEYWORDS: list[tuple[str, list[str]]] = [
    ("recommend", ["usinis", "tavsiya", "taklif", "ne islew", "nima qil", "sheshim", "ilaj", "chora"]),
    ("weak", ["mashqala", "muammo", "maseleli", "tomen", "past", "artta", "keyin qalgan", "hawip", "kritik", "zaif"]),
    ("compare", ["salistir", "solishtir", "taqqosla", "reyting", "en jaqsi", "eng yaxshi", "qaysi rayon", "qaysi tuman"]),
    ("annual", ["jilliq", "yillik", "dinamika", "juwmaq", "hisobot", "tariyx", "osiw pati"]),
]

#: Sohaga bog'langan harakatlar rejasi. Ma'lumot bermaydi — nima
#: qilishni taklif qiladi; raqamlar har doim bazadan qo'shiladi.
PLAYBOOK: dict[str, list[Recommendation]] = {
    "awil_xojaligi": [
        Recommendation(
            horizon="short",
            title="Suwdı únemlew rejimine ótiw (1–3 ay)",
            actions=[
                "Kóp suw talap etetuǵın maydanlardı inventarizaciyalaw hám limitti qayta bólistiriw",
                "Tamshılatıp suwǵarıw úskenelerin subsidiyalanǵan lizingge shıǵarıw",
                "Kanallardaǵı filtraciya joǵaltıwların saplastırıw",
            ],
            impact="Suwǵarıw suwı sarpın 12–18% ke qısqartırıw",
        ),
        Recommendation(
            horizon="mid",
            title="Egin dúzilisin qayta kórip shıǵıw (6 ay)",
            actions=[
                "Suw talap etetuǵın eginlerdi sorǵa shıdamlı sortlarǵa almastırıw",
                "Kollektor-drenaj tarmaǵın tazalaw grafigin dúziw",
                "Fermerler menen kepillengen satıp alıw shártnamaları",
            ],
            impact="Bir gektardan alınatuǵın dáramattı 15–20% ke asırıw",
        ),
        Recommendation(
            horizon="long",
            title="Qayta islew shınjırın qurıw (1 jıl)",
            actions=[
                "Qurıtıw hám konservalaw sexlerin iske túsiriw",
                "Muzlatqısh ambarlar tarmaǵın keńeytiw",
                "Organikalıq sertifikatlaw arqalı eksport bazarına shıǵıw",
            ],
            impact="Qosılǵan qunnı hám eksport bahasın asırıw",
        ),
    ],
    "sanaat": [
        Recommendation(
            horizon="short",
            title="Quwatlardı tolıq júklew (1–3 ay)",
            actions=[
                "Toqtap turǵan liniyalardı hám sebeplerin anıqlaw",
                "Shiyki zat jetkerip beriwdiń úzilislerin saplastırıw",
                "Elektr támiyinatı grafigin kárxanalar menen kelisiw",
            ],
            impact="Ámeldegi quwattan paydalanıwdı arttırıw",
        ),
        Recommendation(
            horizon="mid",
            title="Kishi sanaat zonaların keńeytiw (6 ay)",
            actions=[
                "Boc turǵan maydanlardı investorlarǵa usınıw",
                "Injenerlik infradúzilmesin jetkeriw",
                "Kadrlardı qayta tayarlaw kursların shólkemlestiriw",
            ],
            impact="Jańa jumıs orınları hám ónim kólemi",
        ),
        Recommendation(
            horizon="long",
            title="Modernizaciya hám tereńlestirip qayta islew (1 jıl)",
            actions=[
                "Eskirgen úskenelerdi almastırıw baǵdarlaması",
                "Jergilikli shiyki zattı tereńlestirip qayta islew",
                "Eksportqa baǵdarlanǵan ónim túrlerin ózlestiriw",
            ],
            impact="Qosılǵan qunnıń úlesin asırıw",
        ),
    ],
}

DEFAULT_PLAYBOOK = [
    Recommendation(
        horizon="short",
        title="Házirgi jaǵdaydı turaqlastırıw (1–3 ay)",
        actions=[
            "Tómenlew sebeplerin kesim boyınsha anıqlaw hám juwapkerni belgilew",
            "Háptelik monitoring grafigin jolǵa qoyıw",
            "Rezerv resurslardı eń máseleli baǵdarǵa jóneltiw",
        ],
        impact="Kórsetkishtiń keyingi tómenlewin toqtatıw",
    ),
    Recommendation(
        horizon="mid",
        title="Sistemalı ilajlar (6 ay)",
        actions=[
            "Tarawǵa baǵdarlanǵan qollap-quwatlaw baǵdarlamasın iske túsiriw",
            "Kadrlar hám texnikalıq támiynattı kúsheytiw",
            "Jeke sektor menen sheriklik joybarların baslaw",
        ],
        impact="Ósiw pátin respublika ortashasına shıǵarıw",
    ),
    Recommendation(
        horizon="long",
        title="Turaqlı ósiw tiykarın jaratıw (1 jıl)",
        actions=[
            "Infradúzilme hám modernizaciya joybarların juwmaqlaw",
            "Investiciya tartıw boyınsha anıq maqsetli jumıs",
            "Nátiyjelerdi jıllıq esabatta bekkemlew",
        ],
        impact="Tarawdı turaqlı ósiw trayektoriyasına alıp shıǵıw",
    ),
]


def severity_from_growth(yoy: float | None) -> str:
    """
    O'sish sur'atidan holat kodi.

    Manbada reja yo'q, shuning uchun holat yagona mavjud signaldan —
    o'tgan yilga nisbatan o'zgarishdan chiqariladi. Frontend'dagi status
    ranglari va yorliqlari shu qiymatlarga tayanadi.
    """
    if yoy is None:
        return "in_progress"
    if yoy < -5:
        return "critical"
    if yoy < 0:
        return "at_risk"
    if yoy < 5:
        return "in_progress"
    return "completed"


#: Nom qancha harfdan boshlab tanilishi mumkin. Undan qisqasi tasodifiy
#: so'zlarga yopishib qoladi ("kegey" — mayli, "keg" — yo'q).
MIN_STEM = 5


def _clean(text: str) -> str:
    """Qidiruv uchun: diakritikasiz, tinish belgilarisiz, bir bo'shliqli."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]+", " ", normalize(text))).strip()


def district_aliases(d) -> list[str]:
    """
    Hudud nomining barcha yozilishi.

    Foydalanuvchi o'zbekcha ("Mo'ynoq"), qoraqalpoqcha ("Moynaq") yoki
    ruscha ("Муйнак") yozishi mumkin. ID aynan o'zbekcha translitdan
    kelib chiqqani uchun uchinchi variantni bepul beradi.
    """
    return [a for a in (_clean(d.name), _clean(d.id), _clean(d.name_ru)) if len(a) >= 4]


def _has(q: str, keys: list[str]) -> bool:
    """
    Kalit so'z SO'Z BOSHIDA uchraydimi.

    Oddiy `in` tekshiruvi so'z ichiga ham yopishadi: "jay" (qurilish
    kaliti) "Xojayli" nomining o'rtasida turibdi va hudud haqidagi savol
    qurilish so'rovi bo'lib qolardi. Oxiri erkin — qo'shimchalar
    ("jaylar", "sawdada") kesilmasligi kerak.
    """
    return any(re.search(rf"\b{re.escape(_clean(k))}", q) for k in keys)


def _match_len(alias: str, q: str) -> int:
    """
    So'rovda topilgan eng uzun bosh qism uzunligi.

    Faqat boshi solishtiriladi, chunki qo'shimchalar oxiriga qo'shiladi:
    "Moynaqta", "Moynaqtıń", "Mo'ynoqda" — hammasi bir xil boshlanadi.
    """
    best = 0
    for n in range(MIN_STEM, len(alias) + 1):
        if alias[:n] not in q:
            break
        best = n
    return best


def parse(db: Session, prompt: str) -> tuple[str, str | None, str | None]:
    """So'rovdan niyat, hudud va sohani ajratadi."""
    q = _clean(prompt)

    # Eng uzun mos kelgan nom yutadi: "Nókis qalası" va "Nókis rayonı"
    # bir xil boshlanadi, faqat uzunlik ularni ajratadi.
    district_id = None
    best_len = 0
    for did, d in sorted(st.district_names(db).items()):
        hit = max((_match_len(a, q) for a in district_aliases(d)), default=0)
        if hit > best_len:
            district_id, best_len = did, hit

    module = next((mid for mid, keys in MODULE_KEYWORDS.items() if _has(q, keys)), None)
    intent = next((name for name, keys in INTENT_KEYWORDS if _has(q, keys)), "overview")
    # Soha ATALGAN bo'lsa u aniqroq javob beradi: "module" shoxi hududni
    # ham hisobga oladi ("Moynaqta sanaat"), "district" shoxi esa barcha
    # sohalarni umumlashtirib, aynan so'ralganini yo'qotardi.
    if intent == "overview":
        if module:
            intent = "module"
        elif district_id:
            intent = "district"

    return intent, district_id, module


def _fmt(value: float | None) -> str:
    """Ming ajratgichi — uzilmas probel, kasr — bitta belgi."""
    if value is None:
        return "—"
    return f"{value:,.1f}".replace(",", " ").removesuffix(".0")


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:+.1f}%"


def answer(
    db: Session,
    prompt: str,
    *,
    district_id: str | None = None,
    module_id: str | None = None,
    year: int | None = None,
) -> ChatResponse:
    year = year or st.latest_year(db)
    intent, parsed_district, parsed_module = parse(db, prompt)
    district_id = parsed_district or district_id
    module = parsed_module or (module_id if module_id in st.MODULE_META else None)

    # Savolda hudud atalmagan bo'lsa ham, foydalanuvchi xaritada bittasini
    # tanlab turgan bo'lishi mumkin — "Jaǵday qalay?" o'sha hudud haqida.
    if intent == "overview":
        if district_id:
            intent = "district"
        elif module:
            intent = "module"

    primary = st.primary_indicators(db)
    indicator = primary.get(module or "") or next(iter(primary.values()), None)
    if indicator is None:
        return ChatResponse(
            text="Bazada statistika tabılmadı. Aldın maǵlıwmattı júklew kerek.",
            sources=0,
            engine="local",
        )
    module = indicator.module or module
    meta = st.MODULE_META.get(module or "", ("", "", "#38bdf8", 0))
    unit = st.short_unit(indicator.unit)

    layer = st.map_layer(db, indicator, year)
    rows = [d for d in layer["districts"] if d["value"] is not None]
    with_growth = sorted(
        (d for d in rows if d["yoy"] is not None), key=lambda d: d["yoy"], reverse=True
    )
    declining = [d for d in with_growth if d["yoy"] < 0]
    period = f"{year}-jıl" + (f" ({layer['period_caption']})" if layer["partial"] else "")

    charts = []
    recommendations: list[Recommendation] = []
    insight = None
    highlight: list[str] = []

    if intent == "recommend":
        target = declining[-1] if declining else (with_growth[-1] if with_growth else None)
        where = target["name"] if target and not district_id else None
        if district_id:
            where = st.district_names(db)[district_id].name
            target = next((d for d in rows if d["district_id"] == district_id), target)

        text = (
            f"**{where or 'Respublika'} · {meta[0]} — háreket rejesi**\n\n"
            + (
                f"Házirgi jaǵday: **{_fmt(target['value'])} {unit}**, "
                f"ótken jılǵa salıstırǵanda **{_pct(target['yoy'])}**"
                + (f", respublikada **{target['rank']}-orın**." if target.get("rank") else ".")
                if target
                else "Bul kesim boyınsha bul jılı maǵlıwmat joq."
            )
            + "\n\nTómende bazadaǵı kórsetkishler tiykarında 3 basqıshlı reje berilgen."
        )
        recommendations = PLAYBOOK.get(module or "", DEFAULT_PLAYBOOK)
        highlight = [target["district_id"]] if target else []
        charts = [
            c
            for c in [
                ch.dynamics_chart(db, indicator, target["district_id"] if target else None, year),
                ch.growth_chart(db, indicator, year),
            ]
            if c
        ]

    elif intent == "weak":
        if declining:
            lines = "\n".join(
                f"{i + 1}. **{d['name']}** — {_fmt(d['value'])} {unit}, "
                f"ósiw **{_pct(d['yoy'])}**"
                for i, d in enumerate(reversed(declining[-6:]))
            )
            worst = declining[-1]
            text = (
                f"**{meta[0]} — tómenlew gúzetilgen rayonlar ({period})**\n\n"
                f"Ótken jıl menen salıstırıwda **{len(declining)} rayonda** kólem "
                f"tómenlegen.\n\n{lines}"
            )
            insight = AiInsight(
                headline=f"{worst['name']}: {meta[1].lower()} {_pct(worst['yoy'])}",
                body=f"Kólemi {_fmt(worst['value'])} {unit}, respublikada {worst['rank']}-orın.",
                severity=severity_from_growth(worst["yoy"]),
                districts=[d["district_id"] for d in reversed(declining[-5:])],
                module_id=module,
            )
            highlight = [d["district_id"] for d in reversed(declining[-5:])]
        elif not layer["comparable"]:
            # 2026 ning yarmi 2025 ning tolig'i bilan solishtirilmaydi
            text = (
                f"**{meta[0]} — {period}**\n\n"
                f"Bul dáwir ushın ósiw esaplanbaydı: manbada {year - 1}-jıldıń usı "
                f"dáwiri joq, tolıq jıl menen salıstırıw nadurıs bolar edi. "
                f"Kólem boyınsha eń tómen rayon — **{rows[-1]['name']}** "
                f"({_fmt(rows[-1]['value'])} {unit})."
            )
            highlight = [rows[-1]["district_id"]] if rows else []
        else:
            text = f"**{meta[0]} — {period}**\n\nBarlıq rayonlarda kólem óskan."
        charts = [c for c in [ch.growth_chart(db, indicator, year), ch.ranking_chart(db, indicator, year)] if c]

    elif intent == "compare":
        top = rows[:3]
        bottom = list(reversed(rows[-3:]))
        text = (
            f"**{meta[0]} — rayonlar reytingi ({period})**\n\n**Aldıńǵılar:**\n"
            + "\n".join(
                f"{i + 1}. {r['name']} — **{_fmt(r['value'])} {unit}** "
                f"(úlesi {r['share']:.1f}%)"
                for i, r in enumerate(top)
            )
            + "\n\n**Artta qalǵanlar:**\n"
            + "\n".join(
                f"{i + 1}. {r['name']} — **{_fmt(r['value'])} {unit}** "
                f"(úlesi {r['share']:.1f}%)"
                for i, r in enumerate(bottom)
            )
        )
        highlight = [r["district_id"] for r in top]
        charts = [c for c in [ch.ranking_chart(db, indicator, year), ch.growth_chart(db, indicator, year)] if c]

    elif intent == "district" and district_id:
        profile = st.district_profile(db, district_id, year)
        if profile and profile["modules"]:
            ordered = sorted(profile["modules"], key=lambda m: m["share"] or 0)
            best, worst = ordered[-1], ordered[0]
            d = profile["district"]
            text = (
                f"**{d['name']} — {period}**\n\n"
                f"Orayı: {d['center']} · Xalıq: {d['population']:g} mıń\n\n"
                f"Eń úlken úles — **{best['name'].lower()}** "
                f"({best['share']:.1f}%, {_fmt(best['value'])} {st.short_unit(best['unit'])}), "
                f"eń kishisi — **{worst['name'].lower()}** ({worst['share']:.1f}%). "
                f"Tarawlar boyınsha ortasha ósiw **{_pct(profile['avg_growth'])}**."
            )
            insight = AiInsight(
                headline=f"{d['name']}: ortasha ósiw {_pct(profile['avg_growth'])}",
                body=f"Eń úlken taraw — {best['name'].lower()} ({best['share']:.1f}%).",
                severity=severity_from_growth(profile["avg_growth"]),
                districts=[district_id],
                module_id=best["module"],
            )
        else:
            text = f"**{period}** ushın bul aymaq boyınsha maǵlıwmat tabılmadı."
        highlight = [district_id]
        charts = [
            c
            for c in [
                ch.share_chart(db, district_id, year),
                ch.dynamics_chart(db, indicator, district_id, year),
            ]
            if c
        ]

    elif intent == "module":
        points = st.series(db, indicator, district_id=district_id, year_to=year)
        current = next((p for p in reversed(points) if p["year"] == year), None)
        where = st.district_names(db)[district_id].name if district_id else "Respublika"
        text = (
            f"**{meta[0]} — {where}, {period}**\n\n"
            f"Kólemi **{_fmt(current['value'] if current else None)} {unit}**, "
            f"ótken jılǵa salıstırǵanda **{_pct(current['yoy'] if current else None)}**.\n\n"
            f"Aldıńǵı rayon — **{rows[0]['name']}** ({rows[0]['share']:.1f}%), "
            f"eń tómeni — **{rows[-1]['name']}** ({rows[-1]['share']:.1f}%)."
            if rows
            else f"**{meta[0]}** boyınsha bul jılı maǵlıwmat joq."
        )
        highlight = [rows[0]["district_id"]] if rows else []
        charts = [
            c
            for c in [
                ch.dynamics_chart(db, indicator, district_id, year),
                ch.ranking_chart(db, indicator, year),
            ]
            if c
        ]

    else:  # annual / overview
        overview = st.overview(db, year)
        cards = overview["modules"]
        grown = sorted(
            (c for c in cards if c["yoy"] is not None), key=lambda c: c["yoy"], reverse=True
        )
        text = (
            f"**Qaraqalpaqstan Respublikası — {period} ulıwma kórinisi**\n\n"
            f"Bazada {len(cards)} tiykarǵı taraw boyınsha maǵlıwmat bar. "
            + (
                f"Ortasha ósiw **{_pct(overview['avg_growth'])}**: "
                f"**{overview['growing']} tarawda** ósiw, "
                f"**{overview['declining']} tarawda** tómenlew.\n\n"
                f"Eń tez ósken — **{grown[0]['name']}** ({_pct(grown[0]['yoy'])}), "
                f"eń páseń — **{grown[-1]['name']}** ({_pct(grown[-1]['yoy'])})."
                if grown
                else f"Bul dáwir ushın ósiw esaplanbaydı — {year - 1}-jıldıń usı dáwiri manbada joq."
            )
            + (
                f"\n\n{meta[1]} boyınsha aldıńǵı rayon — **{rows[0]['name']}** "
                f"(respublikanıń {rows[0]['share']:.1f}% i)."
                if rows
                else ""
            )
        )
        if declining:
            worst = declining[-1]
            insight = AiInsight(
                headline=f"{worst['name']}: {meta[1].lower()} {_pct(worst['yoy'])}",
                body=f"Kólemi {_fmt(worst['value'])} {unit}.",
                severity=severity_from_growth(worst["yoy"]),
                districts=[d["district_id"] for d in reversed(declining[-4:])],
                module_id=module,
            )
            highlight = [d["district_id"] for d in reversed(declining[-4:])]
        charts = [
            c
            for c in [
                ch.structure_chart(db, year),
                ch.ranking_chart(db, indicator, year),
                ch.growth_chart(db, indicator, year),
            ]
            if c
        ]

    return ChatResponse(
        text=text,
        charts=charts,
        insight=insight,
        recommendations=recommendations,
        sources=len(rows),
        highlight=list(dict.fromkeys(highlight))[:5],
        engine="local",
    )
