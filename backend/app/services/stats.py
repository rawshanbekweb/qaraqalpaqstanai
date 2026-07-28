"""
Excel'dan yuklangan haqiqiy statistika ustidan agregatsiyalar.

Eski `services/analytics.py` reja↔amalda modeli bilan ishlaydi; manba
statistikada esa reja yo'q — faqat o'lchangan qiymat. Shuning uchun bu
yerdagi ko'rsatkichlar boshqacha: qiymat, o'tgan yilga nisbatan o'sish,
respublikadagi ulush va o'rin.

Manbadagi davr turlari faqat ikkita: to'liq yil (`year`) va yil boshidan
yig'indi (`ytd`, `period_no` — nechanchi oygacha). Oylik/choraklik qator
umuman yo'q, shuning uchun bu yerda ham yo'q.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import District, StatCategory, StatIndicator, StatObservation
from app.text import normalize

MONTHS_KAA = [
    "yanvar", "fevral", "mart", "aprel", "may", "iyun",
    "iyul", "avgust", "sentyabr", "oktyabr", "noyabr", "dekabr",
]

#: Xarita va asosiy panel ishlaydigan tayanch sohalar.
#: module -> (to'liq nom, qisqa nom, rang, tartib)
MODULE_META: dict[str, tuple[str, str, str, int]] = {
    "sanaat": ("Sanaat ónimi kólemi", "Sanaat", "#0ea5e9", 1),
    "awil_xojaligi": ("Awıl xojalıǵı ónimleri", "Awıl xojalıǵı", "#a3e635", 2),
    "investitsiya": ("Tiykarǵı kapitalǵa investitsiyalar", "Investitsiya", "#818cf8", 3),
    "qurilis": ("Qurılıs jumısları", "Qurılıs", "#c084fc", 4),
    "xizmetler": ("Kórsetilgen xızmetler kólemi", "Xızmetler", "#34d399", 5),
    "transport": ("Tasılǵan júkler kólemi", "Transport", "#fbbf24", 6),
    "sawda": ("Usaqlap satıw tovar aylanısı", "Sawda", "#f97316", 7),
}

#: Nomida shu parcha bo'lsa — bu hajm emas, o'sish sur'ati (foizda).
#: Xarita hajm bilan ishlaydi, shuning uchun bunday ko'rsatkichlar
#: tayanch sifatida tanlanmaydi.
GROWTH_HINTS = ("ósim", "ósiw", "o'siw", "osim", "osiw", "%")


# ── Davrlar ──────────────────────────────────────────────────────────


def period_label(period: str, period_no: int | None) -> str:
    """Davrning qoraqalpoqcha nomi: "jıl" yoki "yanvar–iyun"."""
    if period == "ytd" and period_no:
        if period_no <= 1:
            return MONTHS_KAA[0]
        return f"{MONTHS_KAA[0]}–{MONTHS_KAA[min(period_no, 12) - 1]}"
    return "jıl"


@dataclass(frozen=True)
class Period:
    """Bitta yil uchun manbada mavjud bo'lgan davr."""

    year: int
    period: str
    period_no: int | None

    @property
    def partial(self) -> bool:
        return self.period != "year"

    @property
    def label(self) -> str:
        return str(self.year) if not self.partial else f"{self.year}*"

    @property
    def caption(self) -> str:
        return period_label(self.period, self.period_no)

    def same_span(self, other: "Period") -> bool:
        """Ikki davrni taqqoslash mumkinmi (to'liq yil ↔ yarim yil emas)."""
        return self.period == other.period and self.period_no == other.period_no


def periods_for(db: Session, indicator_id: int) -> dict[int, Period]:
    """Ko'rsatkichda qaysi yilda qanday davr borligi.

    Bir yilda ikkala tur ham uchrasa to'liq yil ustun turadi — u to'liqroq.
    """
    rows = db.execute(
        select(StatObservation.year, StatObservation.period, StatObservation.period_no)
        .where(StatObservation.indicator_id == indicator_id)
        .distinct()
    ).all()
    out: dict[int, Period] = {}
    for year, period, period_no in rows:
        current = out.get(year)
        if current is None or (current.partial and period == "year"):
            out[year] = Period(year, period, period_no)
    return out


# ── Ko'rsatkichlar ───────────────────────────────────────────────────


def is_volume(indicator: StatIndicator) -> bool:
    """Hajm ko'rsatkichimi yoki o'sish sur'atimi (foiz)."""
    text = f"{indicator.name_kaa} {indicator.unit}".lower()
    return not any(hint in text for hint in GROWTH_HINTS)


def primary_indicators(db: Session) -> dict[str, StatIndicator]:
    """
    Har bir tayanch soha uchun bitta "asosiy" ko'rsatkich.

    Bitta sohaga bir nechta ko'rsatkich tegishli bo'ladi (hajm, o'sish
    sur'ati, respublika kesimi, tuman kesimi). Xarita uchun rayon kesimidagi
    HAJM keragi — tanlov shu tartibda: rayon kesimi bor → hajm →
    o'lchovi ko'proq → id kichikroq (barqarorlik uchun).
    """
    counts = dict(
        db.execute(
            select(StatObservation.indicator_id, func.count(StatObservation.id))
            .group_by(StatObservation.indicator_id)
        ).all()
    )
    candidates = db.scalars(
        select(StatIndicator).where(StatIndicator.module.is_not(None))
    ).all()

    best: dict[str, StatIndicator] = {}
    for ind in candidates:
        current = best.get(ind.module or "")
        key = (ind.has_districts, is_volume(ind), counts.get(ind.id, 0), -ind.id)
        if current is None:
            best[ind.module or ""] = ind
            continue
        cur_key = (
            current.has_districts,
            is_volume(current),
            counts.get(current.id, 0),
            -current.id,
        )
        if key > cur_key:
            best[ind.module or ""] = ind
    return best


def resolve_indicator(
    db: Session, *, indicator_id: int | None = None, module: str | None = None
) -> StatIndicator | None:
    """`indicator_id` yoki `module` bo'yicha ko'rsatkichni topadi."""
    if indicator_id is not None:
        return db.get(StatIndicator, indicator_id)
    if module:
        return primary_indicators(db).get(module)
    return None


def indicator_brief(ind: StatIndicator) -> dict:
    meta = MODULE_META.get(ind.module or "")
    return {
        "id": ind.id,
        "slug": ind.slug,
        "category_id": ind.category_id,
        "name": ind.name_kaa,
        "name_uz": ind.name_uz or "",
        "unit": ind.unit,
        "module": ind.module,
        "module_name": meta[1] if meta else None,
        "color": meta[2] if meta else None,
        "has_districts": ind.has_districts,
        "lower_is_better": ind.lower_is_better,
        "source": ind.source,
    }


# ── Umumiy ma'lumotnomalar ───────────────────────────────────────────


def available_years(db: Session) -> list[int]:
    return sorted(
        y for (y,) in db.execute(select(StatObservation.year).distinct()).all()
    )


def latest_year(db: Session, indicator_id: int | None = None) -> int:
    stmt = select(func.max(StatObservation.year))
    if indicator_id is not None:
        stmt = stmt.where(StatObservation.indicator_id == indicator_id)
    return db.scalar(stmt) or 0


def district_names(db: Session) -> dict[str, District]:
    return {d.id: d for d in db.scalars(select(District)).all()}


def meta(db: Session) -> dict:
    """Frontend uchun bitta "boshlang'ich" javob."""
    primary = primary_indicators(db)
    modules = []
    for module, (name, short, color, sort) in sorted(
        MODULE_META.items(), key=lambda kv: kv[1][3]
    ):
        ind = primary.get(module)
        if ind is None:
            continue
        # Har sohaning o'z yillar shkalasi bor — biri 2000 dan, boshqasi
        # 2010 dan boshlanadi. Filtr shu ro'yxatga qarab quriladi.
        module_years = sorted(periods_for(db, ind.id))
        modules.append(
            {
                "id": module,
                "name": name,
                "short": short,
                "color": color,
                "sort": sort,
                "unit": ind.unit,
                "indicator_id": ind.id,
                "has_districts": ind.has_districts,
                "years": module_years,
                "latest_year": module_years[-1] if module_years else None,
            }
        )

    categories = [
        {
            "id": c.id,
            "name": c.name_kaa,
            "name_uz": c.name_uz,
            "color": c.color,
            "sort": c.sort,
            "indicators": n,
        }
        for c, n in db.execute(
            select(StatCategory, func.count(StatIndicator.id))
            .outerjoin(StatIndicator, StatIndicator.category_id == StatCategory.id)
            .group_by(StatCategory.id)
            .order_by(StatCategory.sort)
        ).all()
    ]

    districts = [
        {
            "id": d.id,
            "name": d.name,
            "name_ru": d.name_ru,
            "center": d.center,
            "area_km2": d.area_km2,
            "population": d.population,
        }
        for d in db.scalars(select(District).order_by(District.name)).all()
    ]

    years = available_years(db)
    return {
        "years": years,
        "latest_year": years[-1] if years else 0,
        "modules": modules,
        "categories": categories,
        "districts": districts,
        "indicators": db.scalar(select(func.count()).select_from(StatIndicator)) or 0,
        "observations": db.scalar(select(func.count()).select_from(StatObservation)) or 0,
    }


# ── Qator (yillar bo'yicha) ──────────────────────────────────────────


def series(
    db: Session,
    indicator: StatIndicator,
    *,
    district_id: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict]:
    """
    Yillar kesimidagi qator.

    `district_id` berilmasa — respublika bo'yicha. Manbada respublika
    qatori har doim ham yo'q, shuning uchun u bo'lmasa tumanlar yig'indisi
    olinadi (`aggregated` bayrog'i bilan belgilanadi).
    """
    stmt = select(
        StatObservation.year,
        StatObservation.period,
        StatObservation.period_no,
        StatObservation.district_id,
        StatObservation.value,
    ).where(StatObservation.indicator_id == indicator.id)

    aggregated = False
    if district_id:
        stmt = stmt.where(StatObservation.district_id == district_id)
    else:
        has_republic = db.scalar(
            select(func.count(StatObservation.id)).where(
                StatObservation.indicator_id == indicator.id,
                StatObservation.district_id.is_(None),
            )
        )
        aggregated = not has_republic
        stmt = (
            stmt.where(StatObservation.district_id.is_not(None))
            if aggregated
            else stmt.where(StatObservation.district_id.is_(None))
        )

    if year_from:
        stmt = stmt.where(StatObservation.year >= year_from)
    if year_to:
        stmt = stmt.where(StatObservation.year <= year_to)

    # Bir yilda ikkala davr turi uchrasa — to'liq yil ustun
    by_year: dict[int, tuple[Period, dict[str | None, float]]] = {}
    for year, period, period_no, did, value in db.execute(stmt).all():
        p = Period(year, period, period_no)
        current = by_year.get(year)
        if current is None or (current[0].partial and not p.partial):
            current = (p, {})
            by_year[year] = current
        elif not current[0].same_span(p):
            continue  # boshqa davr turi — aralashtirilmaydi
        current[1][did] = current[1].get(did, 0.0) + float(value or 0)

    points: list[dict] = []
    for year in sorted(by_year):
        p, values = by_year[year]
        value = sum(values.values())
        previous = by_year.get(year - 1)

        yoy = None
        if previous and previous[0].same_span(p):
            # Hududlar qamrovi yillar bo'yicha o'zgaradi (masalan Bo'zatov
            # 2016 dan keyin paydo bo'ladi). O'sishni butun yig'indidan
            # hisoblasak, yangi hudud qo'shilishi "o'sish" bo'lib ko'rinadi —
            # shuning uchun taqqoslash faqat ikkala yilda ham bor hududlar
            # kesimida bajariladi.
            common = values.keys() & previous[1].keys()
            base = sum(previous[1][k] for k in common)
            if common and base:
                yoy = round((sum(values[k] for k in common) - base) / abs(base) * 100, 2)

        points.append(
            {
                "year": year,
                "label": p.label,
                "caption": p.caption,
                "partial": p.partial,
                "value": round(value, 2),
                "yoy": yoy,
                "sources": len(values),
                "aggregated": aggregated,
            }
        )
    return points


# ── Xarita qatlami ───────────────────────────────────────────────────


def _values_by_district(
    db: Session, indicator_id: int, year: int
) -> tuple[dict[str, float], Period | None]:
    period = periods_for(db, indicator_id).get(year)
    if period is None:
        return {}, None
    rows = db.execute(
        select(StatObservation.district_id, func.sum(StatObservation.value))
        .where(
            StatObservation.indicator_id == indicator_id,
            StatObservation.year == year,
            StatObservation.period == period.period,
            StatObservation.district_id.is_not(None),
        )
        .group_by(StatObservation.district_id)
    ).all()
    return {did: float(v or 0) for did, v in rows}, period


def map_layer(db: Session, indicator: StatIndicator, year: int) -> dict:
    """
    Xarita uchun tuman kesimi: qiymat, ulush, o'rin, o'sish va rang jadali.

    Rang jadali (`intensity`) eng katta qiymatga nisbatan hisoblanadi —
    reja bo'lmagani uchun "bajarilish" tushunchasi bu yerda yo'q.
    """
    values, period = _values_by_district(db, indicator.id, year)
    prev_values, prev_period = _values_by_district(db, indicator.id, year - 1)
    comparable = bool(period and prev_period and period.same_span(prev_period))

    dists = district_names(db)
    total = sum(values.values())
    top = max(values.values(), default=0.0)

    rows = []
    for did, d in dists.items():
        value = values.get(did)
        prev = prev_values.get(did) if comparable else None
        yoy = round((value - prev) / abs(prev) * 100, 2) if value is not None and prev else None
        rows.append(
            {
                "district_id": did,
                "name": d.name,
                "value": round(value, 2) if value is not None else None,
                "share": round(value / total * 100, 2) if value is not None and total else None,
                "yoy": yoy,
                "intensity": round(value / top, 4) if value is not None and top else None,
            }
        )

    ranked = sorted(
        (r for r in rows if r["value"] is not None), key=lambda r: r["value"], reverse=True
    )
    for i, r in enumerate(ranked, start=1):
        r["rank"] = i
    for r in rows:
        r.setdefault("rank", None)
    rows.sort(key=lambda r: (r["rank"] is None, r["rank"] or 0))

    return {
        "indicator": indicator_brief(indicator),
        "year": year,
        "period": period.period if period else None,
        "period_caption": period.caption if period else None,
        "partial": period.partial if period else False,
        "comparable": comparable,
        "unit": indicator.unit,
        "total": round(total, 2),
        "max": round(top, 2),
        "covered": len(ranked),
        "districts": rows,
    }


# ── Hudud profili ────────────────────────────────────────────────────


def district_profile(db: Session, district_id: str, year: int) -> dict | None:
    d = db.get(District, district_id)
    if d is None:
        return None

    modules = []
    for module, ind in primary_indicators(db).items():
        meta_row = MODULE_META.get(module)
        if meta_row is None or not ind.has_districts:
            continue
        points = series(db, ind, district_id=district_id, year_to=year)
        current = next((p for p in reversed(points) if p["year"] == year), None)
        if current is None:
            continue

        values, _ = _values_by_district(db, ind.id, year)
        total = sum(values.values())
        ordered = sorted(values.items(), key=lambda kv: kv[1], reverse=True)
        rank = next((i for i, (did, _) in enumerate(ordered, 1) if did == district_id), None)

        modules.append(
            {
                "module": module,
                "name": meta_row[1],
                "full_name": meta_row[0],
                "color": meta_row[2],
                "sort": meta_row[3],
                "indicator_id": ind.id,
                "unit": ind.unit,
                "value": current["value"],
                "yoy": current["yoy"],
                "partial": current["partial"],
                "share": round(current["value"] / total * 100, 2) if total else None,
                "rank": rank,
                "of": len(ordered),
                "trend": [p["value"] for p in points[-8:]],
            }
        )
    modules.sort(key=lambda m: m["sort"])

    growths = [m["yoy"] for m in modules if m["yoy"] is not None]
    return {
        "district": {
            "id": d.id,
            "name": d.name,
            "name_ru": d.name_ru,
            "center": d.center,
            "area_km2": d.area_km2,
            "population": d.population,
        },
        "year": year,
        "modules": modules,
        "avg_growth": round(sum(growths) / len(growths), 2) if growths else None,
    }


# ── Umumiy ko'rinish ─────────────────────────────────────────────────


def overview(db: Session, year: int) -> dict:
    """Bosh sahifaning yuqori qatori: har bir soha bo'yicha yakun."""
    cards = []
    for module, ind in primary_indicators(db).items():
        meta_row = MODULE_META.get(module)
        if meta_row is None:
            continue
        points = series(db, ind, year_to=year)
        current = next((p for p in reversed(points) if p["year"] == year), None)
        if current is None:
            continue

        values, _ = _values_by_district(db, ind.id, year)
        ordered = sorted(values.items(), key=lambda kv: kv[1], reverse=True)
        dists = district_names(db)

        def named(pair: tuple[str, float] | None) -> dict | None:
            if pair is None:
                return None
            did, value = pair
            name = dists[did].name if did in dists else did
            return {"district_id": did, "name": name, "value": round(value, 2)}

        cards.append(
            {
                "module": module,
                "name": meta_row[1],
                "full_name": meta_row[0],
                "color": meta_row[2],
                "sort": meta_row[3],
                "indicator_id": ind.id,
                "unit": ind.unit,
                "value": current["value"],
                "yoy": current["yoy"],
                "partial": current["partial"],
                "caption": current["caption"],
                "leader": named(ordered[0] if ordered else None),
                "laggard": named(ordered[-1] if ordered else None),
                "trend": [
                    {"year": p["year"], "value": p["value"]} for p in points[-10:]
                ],
            }
        )
    cards.sort(key=lambda c: c["sort"])

    growths = [c["yoy"] for c in cards if c["yoy"] is not None]
    return {
        "year": year,
        "years": available_years(db),
        "modules": cards,
        "avg_growth": round(sum(growths) / len(growths), 2) if growths else None,
        "growing": sum(1 for g in growths if g > 0),
        "declining": sum(1 for g in growths if g < 0),
    }


# ── Ko'rsatkichlar ma'lumotnomasi ────────────────────────────────────


def search_indicators(
    db: Session,
    *,
    q: str | None = None,
    category_id: str | None = None,
    module: str | None = None,
    has_districts: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    stmt = select(StatIndicator)
    if category_id:
        stmt = stmt.where(StatIndicator.category_id == category_id)
    if module:
        stmt = stmt.where(StatIndicator.module == module)
    if has_districts is not None:
        stmt = stmt.where(StatIndicator.has_districts.is_(has_districts))

    rows = list(
        db.scalars(
            stmt.order_by(StatIndicator.category_id, StatIndicator.name_kaa)
        ).all()
    )

    if q and q.strip():
        # Diakritikaga bog'liq bo'lmagan qidiruv ("xaliq" → "xalıq").
        # Ko'rsatkichlar ~1000 ta — filtr Python tomonida bemalol bajariladi.
        needle = normalize(q)
        rows = [r for r in rows if needle in normalize(r.name_kaa)]

    return {
        "total": len(rows),
        "limit": limit,
        "offset": offset,
        "items": [indicator_brief(r) for r in rows[offset : offset + limit]],
    }


def indicator_detail(db: Session, indicator: StatIndicator) -> dict:
    periods = periods_for(db, indicator.id)
    return {
        **indicator_brief(indicator),
        "years": sorted(periods),
        "latest_year": max(periods) if periods else None,
        "observations": db.scalar(
            select(func.count(StatObservation.id)).where(
                StatObservation.indicator_id == indicator.id
            )
        )
        or 0,
    }
