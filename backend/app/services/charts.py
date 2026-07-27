"""Grafik spetsifikatsiyalarini BAZADAN quradi.

AI faqat "qaysi grafik kerak" degan qarorni qabul qiladi; raqamlarni esa
har doim shu modul SQL'dan oladi. Shu sabab javobda o'ylab topilgan son
paydo bo'lishi mumkin emas.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.schemas import ChartSeries, ChartSpec
from app.services import analytics as an

CONTEXT_GRAY = "#5a6588"


def _uid() -> str:
    return f"chart-{uuid.uuid4().hex[:8]}"


def dynamics_chart(db: Session, module_id: str, district_id: str | None, year: int) -> ChartSpec:
    m = an.module_map(db)[module_id]
    where = an.district_map(db)[district_id].name if district_id else "Respublika"
    return ChartSpec(
        id=_uid(),
        kind="area",
        title=f"{m.name} — oylik dinamika",
        subtitle=f"{where}, {year}-yil · reja va amaldagi ko'rsatkich",
        unit=m.unit,
        series=[
            ChartSeries(key="plan", label="Reja", color=CONTEXT_GRAY),
            ChartSeries(key="fact", label="Amalda", color=m.color),
        ],
        data=an.monthly_series(db, module_id, district_id, year),
    )


def quarter_chart(db: Session, module_id: str, district_id: str | None, year: int) -> ChartSpec:
    m = an.module_map(db)[module_id]
    where = an.district_map(db)[district_id].name if district_id else "Respublika"
    return ChartSpec(
        id=_uid(),
        kind="grouped-bar",
        title=f"{m.name} — choraklar kesimi",
        subtitle=f"{where}, {year}-yil",
        unit=m.unit,
        series=[
            ChartSeries(key="plan", label="Reja", color=CONTEXT_GRAY),
            ChartSeries(key="fact", label="Amalda", color=m.color),
        ],
        data=an.quarterly_series(db, module_id, district_id, year),
    )


def deviation_chart(db: Session, module_id: str | None, year: int, limit: int = 10) -> ChartSpec:
    """Rejadan chetlanish — qutbli o'lchov, shuning uchun noldan ikki tomonga."""
    rows = an.district_scores(db, module_id, year)
    worst = list(reversed(rows[-limit:]))
    title = "Rejadan chetlanish"
    if module_id:
        title = f"{an.module_map(db)[module_id].name} — rejadan chetlanish"
    return ChartSpec(
        id=_uid(),
        kind="diverging-bar",
        title=title,
        subtitle=f"{year}-yil · 100% rejaga nisbatan, punkt",
        series=[ChartSeries(key="value", label="Chetlanish")],
        data=[
            {"label": r["name"], "value": round(r["performance"] * 100 - 100, 1)}
            for r in worst
        ],
    )


def comparison_chart(db: Session, module_id: str, year: int, limit: int = 10) -> ChartSpec:
    m = an.module_map(db)[module_id]
    rows = an.district_scores(db, module_id, year)[:limit]
    return ChartSpec(
        id=_uid(),
        kind="grouped-bar",
        title=f"{m.name} — tumanlar reytingi",
        subtitle=f"{year}-yil · reja va amalda",
        unit=m.unit,
        series=[
            ChartSeries(key="plan", label="Reja", color=CONTEXT_GRAY),
            ChartSeries(key="fact", label="Amalda", color=m.color),
        ],
        data=[{"label": r["name"], "plan": r["plan"], "fact": r["fact"]} for r in rows],
    )


def structure_chart(db: Session, year: int) -> ChartSpec:
    """Sohalar tarkibi — gorizontal ustunlar (doiraviy diagramma emas)."""
    mods = an.module_map(db)
    rows = []
    for mid, m in mods.items():
        if m.lower_is_better:  # inflyatsiya hajm emas, uni tarkibga qo'shmaymiz
            continue
        agg = an.rollup(an.fetch(db, module_id=mid, year=year), m.lower_is_better)
        rows.append({"label": m.short or m.name, "value": round(agg.fact, 1), "color": m.color})
    rows.sort(key=lambda r: r["value"], reverse=True)

    return ChartSpec(
        id=_uid(),
        kind="bar",
        title="Iqtisodiyot tarkibi",
        subtitle=f"{year}-yil · sohalar bo'yicha amaldagi hajm",
        series=[ChartSeries(key="value", label="Amaldagi hajm")],
        data=rows,
    )


def yoy_chart(db: Session, year: int) -> ChartSpec:
    mods = an.module_map(db)
    return ChartSpec(
        id=_uid(),
        kind="bar",
        title="Yillik o'sish sur'ati",
        subtitle=f"{year - 1} → {year} · taqqoslanadigan oylar bo'yicha",
        unit="%",
        series=[ChartSeries(key="value", label="O'sish")],
        data=[
            {"label": m.short or m.name, "value": an.yoy_growth(db, mid)}
            for mid, m in mods.items()
        ],
    )


def profile_chart(db: Session, district_id: str, year: int) -> ChartSpec:
    """Tuman ↔ respublika o'rtachasi: har soha uchun ikki qiymat -> dumbbell."""
    d = an.district_map(db)[district_id]
    mods = an.module_map(db)

    data = []
    for mid, m in mods.items():
        local = an.rollup(an.fetch(db, module_id=mid, district_id=district_id, year=year), m.lower_is_better)
        rep = an.rollup(an.fetch(db, module_id=mid, year=year), m.lower_is_better)
        data.append(
            {
                "label": m.short or m.name,
                "local": round(min(130, local.performance * 100), 1),
                "republic": round(min(130, rep.performance * 100), 1),
            }
        )

    return ChartSpec(
        id=_uid(),
        kind="dumbbell",
        title=f"{d.name} — sohalar kesimi",
        subtitle="Tuman va respublika o'rtachasi taqqoslamasi, bajarilish %",
        unit="%",
        series=[
            ChartSeries(key="local", label=d.name, color="#0891b2"),
            ChartSeries(key="republic", label="Respublika o'rtachasi", color="#8b5cf6"),
        ],
        data=data,
    )


#: AI so'ragan grafik turini quruvchi funksiyaga bog'lash
BUILDERS = {
    "dynamics": dynamics_chart,
    "quarters": quarter_chart,
    "deviation": deviation_chart,
    "comparison": comparison_chart,
    "structure": structure_chart,
    "growth": yoy_chart,
    "profile": profile_chart,
}


def build(
    db: Session,
    kind: str,
    *,
    module_id: str | None,
    district_id: str | None,
    year: int,
) -> ChartSpec | None:
    """AI qaytargan grafik so'rovini haqiqiy ChartSpec'ga aylantiradi."""
    mods = an.module_map(db)
    fallback_module = module_id if module_id in mods else next(iter(mods))

    try:
        if kind == "dynamics":
            return dynamics_chart(db, fallback_module, district_id, year)
        if kind == "quarters":
            return quarter_chart(db, fallback_module, district_id, year)
        if kind == "deviation":
            return deviation_chart(db, module_id if module_id in mods else None, year)
        if kind == "comparison":
            return comparison_chart(db, fallback_module, year)
        if kind == "structure":
            return structure_chart(db, year)
        if kind == "growth":
            return yoy_chart(db, year)
        if kind == "profile":
            if not district_id:
                return None
            return profile_chart(db, district_id, year)
    except (KeyError, IndexError):
        return None
    return None
