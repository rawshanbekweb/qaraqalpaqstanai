"""
Haqiqiy statistika ustidan grafik spetsifikatsiyalari.

AI faqat "qaysi grafik kerak" degan qarorni qabul qiladi; raqamlarni esa
har doim shu modul bazadan oladi. Shu sabab javobda o'ylab topilgan son
paydo bo'lishi mumkin emas.

Eski `charts.py` reja↔amalda demo ma'lumoti bilan ishlaydi va admin
paneli uchun qoladi. Bu yerdagi grafiklar reja tushunchasisiz: hajm,
o'sish, ulush.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models import StatIndicator
from app.schemas import ChartSeries, ChartSpec
from app.services import stats as st

#: Grafik uchun qulay bo'lgan tuman soni — 17 tasi gorizontal ustunda
#: o'qiladi, undan ko'pi allaqachon jadval.
TOP_N = 17


def _uid() -> str:
    return f"chart-{uuid.uuid4().hex[:8]}"


def _period_note(layer: dict) -> str:
    return f" ({layer['period_caption']})" if layer.get("partial") else ""


def dynamics_chart(
    db: Session, indicator: StatIndicator, district_id: str | None, year: int
) -> ChartSpec | None:
    """Yillar kesimidagi dinamika (2010–2026)."""
    points = st.series(db, indicator, district_id=district_id, year_to=year)
    if len(points) < 2:
        return None

    meta = st.MODULE_META.get(indicator.module or "")
    where = st.district_names(db)[district_id].name if district_id else "Respublika"
    return ChartSpec(
        id=_uid(),
        kind="area",
        title=f"{indicator.name_kaa[:60]} — jıllar boyınsha",
        subtitle=f"{where} · {points[0]['year']}–{points[-1]['year']}",
        unit=indicator.unit,
        series=[
            ChartSeries(
                key="value",
                label=meta[1] if meta else "Kólemi",
                color=meta[2] if meta else "#38bdf8",
            )
        ],
        data=[{"label": p["label"], "value": p["value"]} for p in points],
    )


def ranking_chart(db: Session, indicator: StatIndicator, year: int) -> ChartSpec | None:
    """Rayonlar hajm bo'yicha — gorizontal ustunlar (uzun nomlar uchun)."""
    layer = st.map_layer(db, indicator, year)
    rows = [d for d in layer["districts"] if d["value"] is not None]
    if not rows:
        return None

    meta = st.MODULE_META.get(indicator.module or "")
    return ChartSpec(
        id=_uid(),
        kind="bar",
        title="Rayonlar boyınsha kólemi",
        subtitle=f"{indicator.name_kaa[:60]} · {year}-jıl{_period_note(layer)}",
        unit=indicator.unit,
        series=[ChartSeries(key="value", label=meta[1] if meta else "Kólemi")],
        data=[{"label": r["name"], "value": r["value"]} for r in rows[:TOP_N]],
    )


def growth_chart(db: Session, indicator: StatIndicator, year: int) -> ChartSpec | None:
    """O'sish sur'ati — qutbli o'lchov, shuning uchun noldan ikki tomonga."""
    layer = st.map_layer(db, indicator, year)
    rows = [d for d in layer["districts"] if d["yoy"] is not None]
    if not rows:
        return None
    rows.sort(key=lambda r: r["yoy"], reverse=True)

    return ChartSpec(
        id=_uid(),
        kind="diverging-bar",
        title="Ósiw pátleri",
        subtitle=f"{indicator.name_kaa[:60]} · {year - 1} → {year}, %",
        unit="%",
        series=[ChartSeries(key="value", label="Ósiw")],
        data=[{"label": r["name"], "value": r["yoy"]} for r in rows[:TOP_N]],
    )


def share_chart(db: Session, district_id: str, year: int) -> ChartSpec | None:
    """Hududning tarmoq tarkibi — respublikadagi ulush bo'yicha."""
    profile = st.district_profile(db, district_id, year)
    if not profile or not profile["modules"]:
        return None

    rows = sorted(
        (m for m in profile["modules"] if m["share"] is not None),
        key=lambda m: m["share"],
        reverse=True,
    )
    return ChartSpec(
        id=_uid(),
        kind="bar",
        title=f"{profile['district']['name']} — tarawlar keseginde",
        subtitle=f"{year}-jıl · respublikadaǵı úlesi, %",
        unit="%",
        series=[ChartSeries(key="value", label="Úlesi")],
        data=[{"label": m["name"], "value": m["share"]} for m in rows],
    )


def structure_chart(db: Session, year: int) -> ChartSpec | None:
    """Sohalar o'sishi — bir yilning yakuniy manzarasi."""
    overview = st.overview(db, year)
    rows = [m for m in overview["modules"] if m["yoy"] is not None]
    if not rows:
        return None
    rows.sort(key=lambda m: m["yoy"], reverse=True)

    return ChartSpec(
        id=_uid(),
        kind="bar",
        title="Tarawlar boyınsha ósiw",
        subtitle=f"{year - 1} → {year} · ótken jılǵa salıstırǵanda, %",
        unit="%",
        series=[ChartSeries(key="value", label="Ósiw")],
        data=[{"label": m["name"], "value": m["yoy"], "color": m["color"]} for m in rows],
    )


def compare_chart(
    db: Session, indicator: StatIndicator, district_id: str, year: int
) -> ChartSpec | None:
    """
    Bitta hudud ↔ respublika o'rtachasi.

    17 rayonning o'rtachasi ataylab olinadi, yig'indi emas: yig'indi
    bilan taqqoslaganda har bir rayon "juda kichik" bo'lib chiqadi va
    grafik hech narsa aytmaydi.
    """
    layer = st.map_layer(db, indicator, year)
    rows = [d for d in layer["districts"] if d["value"] is not None]
    target = next((d for d in rows if d["district_id"] == district_id), None)
    if not target or not rows:
        return None

    avg = sum(d["value"] for d in rows) / len(rows)
    meta = st.MODULE_META.get(indicator.module or "")
    return ChartSpec(
        id=_uid(),
        kind="grouped-bar",
        title=f"{target['name']} hám respublika ortashası",
        subtitle=f"{indicator.name_kaa[:60]} · {year}-jıl{_period_note(layer)}",
        unit=indicator.unit,
        series=[
            ChartSeries(key="local", label=target["name"], color=meta[2] if meta else "#0891b2"),
            ChartSeries(key="republic", label="Ortasha", color="#5a6588"),
        ],
        data=[
            {
                "label": meta[1] if meta else "Kólemi",
                "local": target["value"],
                "republic": round(avg, 2),
            }
        ],
    )


#: AI so'rashi mumkin bo'lgan grafik turlari
CHART_KINDS = ["dynamics", "ranking", "growth", "share", "structure", "compare"]


def build(
    db: Session,
    kind: str,
    *,
    module: str | None,
    district_id: str | None,
    year: int,
) -> ChartSpec | None:
    """AI qaytargan grafik so'rovini haqiqiy ChartSpec'ga aylantiradi."""
    primary = st.primary_indicators(db)
    indicator = primary.get(module or "") or next(iter(primary.values()), None)
    if indicator is None:
        return None

    try:
        if kind == "dynamics":
            return dynamics_chart(db, indicator, district_id, year)
        if kind == "ranking":
            return ranking_chart(db, indicator, year)
        if kind == "growth":
            return growth_chart(db, indicator, year)
        if kind == "share":
            return share_chart(db, district_id, year) if district_id else None
        if kind == "structure":
            return structure_chart(db, year)
        if kind == "compare":
            return compare_chart(db, indicator, district_id, year) if district_id else None
    except (KeyError, IndexError, ZeroDivisionError):
        return None
    return None
