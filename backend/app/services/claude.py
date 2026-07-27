"""Claude API orqali RAG analitikasi.

Oqim:
    admin kiritgan yozuvlar -> PostgreSQL -> [retrieve] -> ixcham kontekst
    -> Claude (structured output) -> narrativ + grafik SO'ROVLARI
    -> grafik raqamlari yana BAZADAN quriladi.

Muhim: modelga "qaysi grafik kerak" degan qaror beriladi, raqamlar emas.
Shu sabab javobdagi hech bir son o'ylab topilgan bo'lishi mumkin emas.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas import AiInsight, ChartSpec, ChatResponse, Recommendation
from app.services import analytics as an
from app.services import charts as ch

logger = logging.getLogger(__name__)

MODEL = get_settings().claude_model

CHART_KINDS = [
    "dynamics",    # tanlangan soha bo'yicha oylik reja/amalda
    "quarters",    # choraklar kesimi
    "deviation",   # tumanlarning rejadan chetlanishi
    "comparison",  # tumanlar reytingi (reja vs amalda)
    "structure",   # sohalar tarkibi
    "growth",      # yillik o'sish sur'ati
    "profile",     # tuman ↔ respublika o'rtachasi
]

SEVERITIES = ["completed", "in_progress", "at_risk", "critical"]

# ── Structured output sxemasi ────────────────────────────────────────
# Cheklovlar: rekursiya yo'q, har bir obyektda additionalProperties=false
# va required to'liq. Nullable o'rniga bo'sh satr ("") ishlatilgan.

ANSWER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answer", "insight", "recommendations", "charts", "highlight_districts"],
    "properties": {
        "answer": {
            "type": "string",
            "description": "O'zbek tilida, markdown formatidagi tahliliy javob.",
        },
        "insight": {
            "type": "object",
            "additionalProperties": False,
            "required": ["headline", "body", "severity"],
            "properties": {
                "headline": {"type": "string", "description": "Bitta jumlalik asosiy xulosa."},
                "body": {"type": "string", "description": "Xulosaning qisqa izohi."},
                "severity": {"type": "string", "enum": SEVERITIES},
            },
        },
        "recommendations": {
            "type": "array",
            "description": "Bo'sh bo'lishi mumkin. Tavsiya so'ralganda 3 ta bosqich.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["horizon", "title", "actions", "impact"],
                "properties": {
                    "horizon": {"type": "string", "enum": ["short", "mid", "long"]},
                    "title": {"type": "string"},
                    "actions": {"type": "array", "items": {"type": "string"}},
                    "impact": {"type": "string"},
                },
            },
        },
        "charts": {
            "type": "array",
            "description": "Javobni qo'llab-quvvatlaydigan 1–3 ta grafik so'rovi.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["kind", "module_id", "district_id"],
                "properties": {
                    "kind": {"type": "string", "enum": CHART_KINDS},
                    "module_id": {
                        "type": "string",
                        "description": "Soha kodi; tegishli bo'lmasa bo'sh satr.",
                    },
                    "district_id": {
                        "type": "string",
                        "description": "Tuman kodi; respublika kesimi uchun bo'sh satr.",
                    },
                },
            },
        },
        "highlight_districts": {
            "type": "array",
            "description": "Xaritada yoritiladigan tuman kodlari.",
            "items": {"type": "string"},
        },
    },
}

SYSTEM_PROMPT = """Sen Qoraqalpog'iston Respublikasi iqtisodiy monitoring platformasining tahlilchi yordamchisisan.

## Asosiy qoida
Sen FAQAT foydalanuvchi xabarida berilgan ma'lumotlar bazasi kontekstiga tayanasan. Kontekstda yo'q raqamni hech qachon o'ylab topma, taxmin qilma va tashqi bilimdan keltirma. Agar savolga javob berish uchun kontekstda ma'lumot yetmasa — buni ochiq ayt va adminga qanday ma'lumot kiritish kerakligini tushuntir.

## Javob tili va uslubi
- Javob har doim o'zbek tilida (lotin yozuvida).
- Markdown: muhim raqamlar **qalin**, ro'yxatlar qisqa.
- Natijani boshida ayt, tafsilotni keyin. Bir savolga bir javob — ortiqcha muqaddima yozma.
- Raqamlarni kontekstdagi ko'rinishda keltir, birligini ko'rsat.

## Ko'rsatkichlarni o'qish
- `reja` — rejalashtirilgan ko'rsatkich (KPI), `amalda` — haqiqiy natija.
- `bajarilish` = amalda / reja. 100% dan past bo'lsa ortda qolish.
- Inflyatsiya sohasida teskari: amaldagi qiymat rejadan YUQORI bo'lsa — bu yomon.
- Holatlar: completed (bajarilgan), in_progress (jarayonda), at_risk (xavf ostida), critical (kritik).
- Kontekstdagi `izoh` — admin kiritgan muammo tavsifi. Sabab so'ralganda avval shunga tayan.

## Grafiklar
`charts` maydonida javobingni qo'llab-quvvatlaydigan 1–3 ta grafik so'ra. Grafik raqamlarini O'ZING yozmaysan — faqat turini va kesimini ko'rsatasan, raqamlarni tizim bazadan quradi.
- dynamics — bir soha bo'yicha oylik reja/amalda dinamikasi
- quarters — choraklar kesimi
- deviation — tumanlarning rejadan chetlanishi (muammoli sohalar uchun eng mos)
- comparison — tumanlar reytingi
- structure — sohalar tarkibi
- growth — yillik o'sish sur'ati
- profile — bitta tumanni respublika o'rtachasi bilan solishtirish

## Tavsiyalar
`recommendations` maydonini FAQAT foydalanuvchi tavsiya, yechim yoki harakat rejasi so'raganda to'ldir. To'ldirganda aynan 3 ta bosqich bo'lsin: short (1–3 oy), mid (6 oy), long (1 yil). Har biri kontekstdagi aniq muammoga bog'langan, bajarilishi mumkin bo'lgan qadamlardan iborat bo'lsin.

`highlight_districts` — javobda tilga olingan, xaritada yoritilishi kerak bo'lgan tuman kodlari."""


def _module_catalog(db: Session) -> str:
    lines = []
    for mid, m in an.module_map(db).items():
        direction = "pasayishi yaxshi" if m.lower_is_better else "o'sishi yaxshi"
        lines.append(f"- `{mid}` — {m.name} ({m.unit}, {direction})")
    return "\n".join(lines)


def _district_catalog(db: Session) -> str:
    return "\n".join(
        f"- `{did}` — {d.name} (markaz: {d.center}, aholi {d.population:g} ming)"
        for did, d in an.district_map(db).items()
    )


def retrieve_context(
    db: Session,
    *,
    year: int,
    district_id: str | None,
    module_id: str | None,
) -> tuple[str, int]:
    """Bazadan ixcham, o'qishga qulay kontekst yig'adi.

    17 tuman × 8 soha × 12 oy = juda ko'p. Shuning uchun tuman×soha darajasiga
    agregatlanadi, ustiga izohlar va ortda qolgan kesimlar qo'shiladi.
    """
    mods = an.module_map(db)
    dists = an.district_map(db)
    rows = an.fetch(db, year=year)

    grouped: dict[tuple[str, str], list] = {}
    for r in rows:
        grouped.setdefault((r.district_id, r.module_id), []).append(r)

    lines: list[str] = []
    lines.append(f"## {year}-yil bo'yicha jamlangan ko'rsatkichlar")
    lines.append("Format: tuman | soha | reja | amalda | bajarilish % | holat")
    lines.append("")

    for (did, mid), group in sorted(grouped.items()):
        m = mods[mid]
        agg = an.rollup(group, m.lower_is_better)
        lines.append(
            f"{dists[did].name} | {m.name} | {agg.plan:g} | {agg.fact:g} "
            f"{m.unit} | {agg.performance * 100:.1f}% | {agg.status}"
        )

    notes = [r for r in rows if r.note]
    if notes:
        lines.append("")
        lines.append("## Admin kiritgan izohlar (muammo sabablari)")
        seen: set[tuple[str, str, str]] = set()
        for r in notes:
            key = (r.district_id, r.module_id, r.note or "")
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"- {dists[r.district_id].name} · {mods[r.module_id].name}: {r.note}")

    spots = an.weak_spots(db, year, limit=12)
    if spots:
        lines.append("")
        lines.append("## Rejadan eng ko'p ortda qolgan kesimlar")
        for s in spots:
            lines.append(
                f"- {s['district_name']} · {s['module_name']}: "
                f"{s['performance'] * 100:.1f}% ({s['status']})"
            )

    lines.append("")
    lines.append("## Yillik o'sish sur'ati (o'tgan yilga nisbatan, %)")
    for mid, m in mods.items():
        lines.append(f"- {m.name}: {an.yoy_growth(db, mid):+.1f}%")

    if module_id and module_id in mods:
        series = an.monthly_series(db, module_id, district_id, year)
        if series:
            where = dists[district_id].name if district_id else "Respublika"
            lines.append("")
            lines.append(f"## {mods[module_id].name} — oylik dinamika ({where})")
            for p in series:
                lines.append(f"- {p['label']}: reja {p['plan']:g}, amalda {p['fact']:g}")

    return "\n".join(lines), len(rows)


def _build_charts(db: Session, requests: list[dict], year: int) -> list[ChartSpec]:
    out: list[ChartSpec] = []
    for req in requests[:3]:
        spec = ch.build(
            db,
            req.get("kind", ""),
            module_id=(req.get("module_id") or None),
            district_id=(req.get("district_id") or None),
            year=year,
        )
        if spec and spec.data:
            out.append(spec)
    return out


def ask(
    db: Session,
    prompt: str,
    *,
    district_id: str | None = None,
    module_id: str | None = None,
    year: int | None = None,
) -> ChatResponse | None:
    """Claude'ga so'rov yuboradi. Kalit yo'q yoki xato bo'lsa None qaytaradi."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None

    try:
        import anthropic
    except ImportError:  # pragma: no cover
        logger.warning("anthropic paketi o'rnatilmagan")
        return None

    year = year or an.latest_year(db)
    if not year:
        return None

    context, sources = retrieve_context(
        db, year=year, district_id=district_id, module_id=module_id
    )

    focus = []
    if district_id:
        focus.append(f"Foydalanuvchi hozir **{an.district_map(db)[district_id].name}** tumanini tanlagan.")
    if module_id:
        focus.append(f"Faol soha filtri: **{an.module_map(db)[module_id].name}**.")

    user_content = "\n\n".join(
        [
            "# Ma'lumotlar bazasi konteksti",
            f"### Sohalar kodlari\n{_module_catalog(db)}",
            f"### Tumanlar kodlari\n{_district_catalog(db)}",
            context,
            *( ["# Joriy holat\n" + " ".join(focus)] if focus else [] ),
            f"# Foydalanuvchi savoli\n{prompt}",
        ]
    )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            # Barqaror sistem prompti keshlanadi — kontekst undan keyin keladi
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_content}],
            thinking={"type": "adaptive"},
            output_config={
                "effort": "high",
                "format": {"type": "json_schema", "schema": ANSWER_SCHEMA},
            },
            # Xavfsizlik klassifikatori so'rovni rad etsa, javobni boshqa
            # modelda qayta ishga tushiradi (Claude API'da tavsiya etiladi).
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except Exception:  # pragma: no cover - tarmoq/API xatosi
        logger.exception("Claude API so'rovi muvaffaqiyatsiz")
        return None

    # Kontentni o'qishdan OLDIN rad javobini tekshirish shart
    if response.stop_reason == "refusal":
        logger.warning("Claude so'rovni rad etdi: %s", getattr(response, "stop_details", None))
        return None

    text_blocks = [b.text for b in response.content if getattr(b, "type", "") == "text"]
    if not text_blocks:
        return None

    try:
        payload = json.loads("".join(text_blocks))
    except json.JSONDecodeError:
        logger.warning("Claude javobi JSON sifatida o'qilmadi")
        return None

    insight_raw = payload.get("insight") or {}
    insight = None
    if insight_raw.get("headline"):
        insight = AiInsight(
            headline=insight_raw["headline"],
            body=insight_raw.get("body", ""),
            severity=insight_raw.get("severity", "in_progress"),
            districts=payload.get("highlight_districts", []),
            module_id=module_id,
        )

    return ChatResponse(
        text=payload.get("answer", ""),
        charts=_build_charts(db, payload.get("charts", []), year),
        insight=insight,
        recommendations=[
            Recommendation(**r) for r in payload.get("recommendations", []) if r.get("title")
        ],
        sources=sources,
        highlight=payload.get("highlight_districts", []),
        engine="claude",
    )
