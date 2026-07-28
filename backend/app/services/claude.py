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
from app.services import stat_charts as ch
from app.services import stats as st

logger = logging.getLogger(__name__)

MODEL = get_settings().claude_model

CHART_KINDS = ch.CHART_KINDS

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
            "description": "Qoraqalpoq tilida, markdown formatidagi tahliliy javob.",
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
                        "description": "Tayanch soha kodi; tegishli bo'lmasa bo'sh satr.",
                    },
                    "district_id": {
                        "type": "string",
                        "description": "Hudud kodi; respublika kesimi uchun bo'sh satr.",
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
Sen FAQAT foydalanuvchi xabarida berilgan ma'lumotlar bazasi kontekstiga tayanasan. Kontekstda yo'q raqamni hech qachon o'ylab topma, taxmin qilma va tashqi bilimdan keltirma. Agar savolga javob berish uchun kontekstda ma'lumot yetmasa — buni ochiq ayt.

## Javob tili va uslubi
- Javob har doim QORAQALPOQ tilida (lotin yozuvida: á, ǵ, ı, ń, ó, ú harflari bilan).
- Markdown: muhim raqamlar **qalin**, ro'yxatlar qisqa.
- Natijani boshida ayt, tafsilotni keyin. Bir savolga bir javob — ortiqcha muqaddima yozma.
- Raqamlarni kontekstdagi ko'rinishda keltir, o'lchov birligini ko'rsat.

## Ma'lumotning tabiati — DIQQAT
Bu manba rasmiy statistika, unda REJA YO'Q. Shuning uchun "reja bajarilishi", "KPI", "chetlanish" haqida gapirma — bunday ma'lumot yo'q. O'lchanadigan narsalar:
- `kólemi` — davr ichidagi hajm (mlrd so'm, ming tonna va h.k.);
- `ósiw` — o'tgan yilning AYNAN SHU davriga nisbatan o'zgarish, foizda;
- `úlesi` — respublika yig'indisidagi ulush, foizda;
- `orın` — hajm bo'yicha 17 hudud orasidagi o'rin.

Davr ikki xil bo'ladi: to'liq yil va yil boshidan yig'indi ("yanvar–iyun"). Yarim yilni to'liq yil bilan solishtirish MUMKIN EMAS — kontekstda o'sish `—` deb berilgan bo'lsa, sababi shu; uni o'zing hisoblab chiqarma.

Hududlar qamrovi yillar bo'yicha o'zgargan (2010-yilda 15 ta, 2019-yildan 17 ta). Respublika bo'yicha o'sish faqat umumiy hududlar kesimida hisoblangan.

## Grafiklar
`charts` maydonida javobingni qo'llab-quvvatlaydigan 1–3 ta grafik so'ra. Grafik raqamlarini O'ZING yozmaysan — faqat turini va kesimini ko'rsatasan, raqamlarni tizim bazadan quradi.
- dynamics — bir soha bo'yicha yillar kesimidagi dinamika (2010–2026)
- ranking — hududlarning hajm bo'yicha reytingi
- growth — hududlarning o'sish sur'ati (muammoli kesimlar uchun eng mos)
- share — bitta hududning tarmoq tarkibi (district_id majburiy)
- structure — sohalar bo'yicha o'sish
- compare — bitta hududni respublika o'rtachasi bilan solishtirish (district_id majburiy)

## Tavsiyalar
`recommendations` maydonini FAQAT foydalanuvchi tavsiya, yechim yoki harakat rejasi so'raganda to'ldir. To'ldirganda aynan 3 ta bosqich bo'lsin: short (1–3 oy), mid (6 oy), long (1 yil). Har biri kontekstdagi aniq raqamga bog'langan, bajarilishi mumkin bo'lgan qadamlardan iborat bo'lsin.

`severity` — o'sish sur'atidan kelib chiq: pasayish −5% dan katta bo'lsa critical, pasayish bo'lsa at_risk, 0–5% oralig'ida in_progress, 5% dan yuqori o'sishda completed.

`highlight_districts` — javobda tilga olingan, xaritada yoritilishi kerak bo'lgan hudud kodlari."""


def _module_catalog(db: Session) -> str:
    lines = []
    for module, ind in st.primary_indicators(db).items():
        meta = st.MODULE_META.get(module)
        if meta is None:
            continue
        lines.append(f"- `{module}` — {meta[0]} ({ind.unit})")
    return "\n".join(lines)


def _district_catalog(db: Session) -> str:
    return "\n".join(
        f"- `{did}` — {d.name} (markaz: {d.center}, aholi {d.population:g} ming)"
        for did, d in st.district_names(db).items()
    )


def _num(value: float | None, digits: int = 1) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def retrieve_context(
    db: Session,
    *,
    year: int,
    district_id: str | None,
    module: str | None,
) -> tuple[str, int]:
    """
    Bazadan ixcham, o'qishga qulay kontekst yig'adi.

    Bazada 1000 dan ortiq ko'rsatkich bor — hammasini kontekstga solib
    bo'lmaydi. Shuning uchun tayanch sohalar (7 ta) × hududlar (17 ta)
    kesimi beriladi, ustiga tanlangan sohaning yillar qatori qo'shiladi.
    """
    primary = st.primary_indicators(db)
    lines: list[str] = []
    rows_used = 0

    lines.append(f"## {year}-yil · hududlar kesimi")
    lines.append("Format: hudud | kólemi | ósiw % | úlesi % | orın")

    for mod, ind in primary.items():
        meta = st.MODULE_META.get(mod)
        if meta is None or not ind.has_districts:
            continue
        layer = st.map_layer(db, ind, year)
        rows = [d for d in layer["districts"] if d["value"] is not None]
        if not rows:
            continue
        rows_used += len(rows)

        period = layer["period_caption"] if layer["partial"] else "to'liq yil"
        lines.append("")
        lines.append(f"### {meta[0]} ({ind.unit}, davr: {period})")
        if not layer["comparable"]:
            lines.append(
                f"_{year - 1}-yilda shu davr yo'q — o'sish hisoblanmagan._"
            )
        for r in rows:
            lines.append(
                f"{r['name']} | {_num(r['value'])} | {_num(r['yoy'])} | "
                f"{_num(r['share'])} | {r['rank']}"
            )

    overview = st.overview(db, year)
    lines.append("")
    lines.append("## Respublika bo'yicha yakun")
    for card in overview["modules"]:
        lines.append(
            f"- {card['full_name']}: {_num(card['value'])} {card['unit']} "
            f"({_num(card['yoy'])}%)"
        )

    # Tanlangan soha bo'yicha uzun qator — trendni ko'rish uchun
    target = primary.get(module or "")
    if target is not None:
        where = st.district_names(db)[district_id].name if district_id else "Respublika"
        points = st.series(db, target, district_id=district_id, year_to=year)
        if points:
            lines.append("")
            lines.append(f"## {target.name_kaa} — yillar qatori ({where})")
            for p in points:
                mark = f" [{p['caption']}]" if p["partial"] else ""
                lines.append(f"- {p['year']}{mark}: {_num(p['value'])} ({_num(p['yoy'])}%)")

    if district_id:
        profile = st.district_profile(db, district_id, year)
        if profile:
            lines.append("")
            lines.append(f"## {profile['district']['name']} — tarmoq tarkibi")
            for m in profile["modules"]:
                lines.append(
                    f"- {m['full_name']}: {_num(m['value'])} {m['unit']}, "
                    f"úlesi {_num(m['share'])}%, orın {m['rank']}/{m['of']}, "
                    f"ósiw {_num(m['yoy'])}%"
                )

    return "\n".join(lines), rows_used


def _build_charts(db: Session, requests: list[dict], year: int) -> list[ChartSpec]:
    out: list[ChartSpec] = []
    for req in requests[:3]:
        spec = ch.build(
            db,
            req.get("kind", ""),
            module=(req.get("module_id") or None),
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

    year = year or st.latest_year(db)
    if not year:
        return None

    context, sources = retrieve_context(
        db, year=year, district_id=district_id, module=module_id
    )

    districts = st.district_names(db)
    focus = []
    if district_id and district_id in districts:
        focus.append(f"Foydalanuvchi hozir **{districts[district_id].name}** hududini tanlagan.")
    if module_id in st.MODULE_META:
        focus.append(f"Faol soha filtri: **{st.MODULE_META[module_id][0]}**.")

    user_content = "\n\n".join(
        [
            "# Ma'lumotlar bazasi konteksti",
            f"### Sohalar kodlari\n{_module_catalog(db)}",
            f"### Hududlar kodlari\n{_district_catalog(db)}",
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
