"""Bazadagi ko'rsatkichlar ustidan agregatsiyalar.

Frontend'dagi `src/lib/analytics.ts` bilan bir xil qoidalar — bir xil raqamlar
ikkala tomonda ham chiqishi uchun.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import District, Indicator, Module

MONTHS_SHORT = [
    "Yan", "Fev", "Mar", "Apr", "May", "Iyn",
    "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek",
]


def status_from_ratio(ratio: float, lower_is_better: bool) -> str:
    """fact/plan nisbatidan holat. Inflyatsiyada nisbat teskari o'qiladi."""
    r = (1 / ratio if ratio else 1.0) if lower_is_better else ratio
    if r >= 1.0:
        return "completed"
    if r >= 0.9:
        return "in_progress"
    if r >= 0.75:
        return "at_risk"
    return "critical"


@dataclass
class Rollup:
    plan: float
    fact: float
    ratio: float
    performance: float
    status: str
    count: int


def rollup(rows: list[Indicator], lower_is_better: bool) -> Rollup:
    if not rows:
        return Rollup(0.0, 0.0, 1.0, 1.0, "in_progress", 0)

    plan_sum = sum(r.plan for r in rows)
    fact_sum = sum(r.fact for r in rows)
    # Inflyatsiya — foiz, shuning uchun yig'indi emas o'rtacha
    plan = plan_sum / len(rows) if lower_is_better else plan_sum
    fact = fact_sum / len(rows) if lower_is_better else fact_sum

    ratio = fact / plan if plan else 1.0
    performance = (1 / ratio if ratio else 1.0) if lower_is_better else ratio
    return Rollup(
        plan=round(plan, 2),
        fact=round(fact, 2),
        ratio=round(ratio, 4),
        performance=round(performance, 4),
        status=status_from_ratio(ratio, lower_is_better),
        count=len(rows),
    )


def module_map(db: Session) -> dict[str, Module]:
    return {m.id: m for m in db.scalars(select(Module)).all()}


def district_map(db: Session) -> dict[str, District]:
    return {d.id: d for d in db.scalars(select(District)).all()}


def fetch(
    db: Session,
    *,
    module_id: str | None = None,
    district_id: str | None = None,
    year: int | None = None,
    max_month: int | None = None,
) -> list[Indicator]:
    stmt = select(Indicator)
    if module_id:
        stmt = stmt.where(Indicator.module_id == module_id)
    if district_id:
        stmt = stmt.where(Indicator.district_id == district_id)
    if year:
        stmt = stmt.where(Indicator.year == year)
    if max_month:
        stmt = stmt.where(Indicator.month <= max_month)
    return list(db.scalars(stmt).all())


def latest_year(db: Session) -> int:
    return db.scalar(select(func.max(Indicator.year))) or 0


def latest_month(db: Session, year: int) -> int:
    return db.scalar(select(func.max(Indicator.month)).where(Indicator.year == year)) or 12


def district_scores(db: Session, module_id: str | None, year: int) -> list[dict]:
    """Har bir tumanning bajarilish darajasi — xarita ranglari uchun."""
    mods = module_map(db)
    dists = district_map(db)
    rows = fetch(db, module_id=module_id, year=year)

    by_district: dict[str, list[Indicator]] = {}
    for r in rows:
        by_district.setdefault(r.district_id, []).append(r)

    out = []
    for did, d in dists.items():
        group = by_district.get(did, [])
        if module_id:
            agg = rollup(group, mods[module_id].lower_is_better)
            performance = agg.performance
            plan, fact = agg.plan, agg.fact
        else:
            # Barcha modullar bo'yicha o'rtacha bajarilish
            per_module = []
            for mid, m in mods.items():
                sub = [r for r in group if r.module_id == mid]
                if sub:
                    per_module.append(rollup(sub, m.lower_is_better))
            performance = (
                sum(p.performance for p in per_module) / len(per_module)
                if per_module
                else 1.0
            )
            plan = sum(p.plan for p in per_module)
            fact = sum(p.fact for p in per_module)

        out.append(
            {
                "district_id": did,
                "name": d.name,
                "plan": round(plan, 2),
                "fact": round(fact, 2),
                "performance": round(performance, 4),
                "status": status_from_ratio(performance, False),
            }
        )
    out.sort(key=lambda x: x["performance"], reverse=True)
    return out


def monthly_series(
    db: Session, module_id: str, district_id: str | None, year: int
) -> list[dict]:
    m = module_map(db)[module_id]
    rows = fetch(db, module_id=module_id, district_id=district_id, year=year)

    by_month: dict[int, list[Indicator]] = {}
    for r in rows:
        if r.month:
            by_month.setdefault(r.month, []).append(r)

    points = []
    for month in sorted(by_month):
        group = by_month[month]
        agg = rollup(group, m.lower_is_better)
        points.append(
            {
                "label": MONTHS_SHORT[month - 1],
                "plan": agg.plan,
                "fact": agg.fact,
            }
        )
    return points


def quarterly_series(
    db: Session, module_id: str, district_id: str | None, year: int
) -> list[dict]:
    m = module_map(db)[module_id]
    rows = fetch(db, module_id=module_id, district_id=district_id, year=year)

    by_q: dict[int, list[Indicator]] = {}
    for r in rows:
        if r.quarter:
            by_q.setdefault(r.quarter, []).append(r)

    out = []
    for q in sorted(by_q):
        agg = rollup(by_q[q], m.lower_is_better)
        out.append({"label": f"{q}-chorak", "plan": agg.plan, "fact": agg.fact})
    return out


def yoy_growth(db: Session, module_id: str, district_id: str | None = None) -> float:
    """Yillik o'sish (%). Taqqoslash faqat mavjud oylar bo'yicha."""
    cur = latest_year(db)
    if not cur:
        return 0.0
    prev = cur - 1
    up_to = latest_month(db, cur)
    m = module_map(db)[module_id]

    def total(y: int) -> float:
        rows = fetch(
            db, module_id=module_id, district_id=district_id, year=y, max_month=up_to
        )
        if not rows:
            return 0.0
        s = sum(r.fact for r in rows)
        return s / len(rows) if m.lower_is_better else s

    a, b = total(prev), total(cur)
    if not a:
        return 0.0
    return round((b - a) / a * 100, 2)


def weak_spots(
    db: Session,
    year: int,
    *,
    module_id: str | None = None,
    district_id: str | None = None,
    limit: int = 12,
) -> list[dict]:
    """Reja bajarilmayotgan tuman × soha kesimlari — eng og'iridan boshlab."""
    mods = module_map(db)
    dists = district_map(db)
    rows = fetch(db, module_id=module_id, district_id=district_id, year=year)

    grouped: dict[tuple[str, str], list[Indicator]] = {}
    for r in rows:
        grouped.setdefault((r.district_id, r.module_id), []).append(r)

    out = []
    for (did, mid), group in grouped.items():
        m = mods[mid]
        agg = rollup(group, m.lower_is_better)
        if agg.performance >= 0.9:
            continue
        noted = next((g.note for g in group if g.note), None)
        gap = agg.fact - agg.plan if m.lower_is_better else agg.plan - agg.fact
        out.append(
            {
                "district_id": did,
                "district_name": dists[did].name,
                "module_id": mid,
                "module_name": m.name,
                "performance": agg.performance,
                "gap": round(gap, 2),
                "status": agg.status,
                "note": noted,
            }
        )
    out.sort(key=lambda x: x["performance"])
    return out[:limit]


def district_profile(db: Session, district_id: str, year: int) -> dict:
    """Bir tumanning barcha sohalar kesimi."""
    mods = module_map(db)
    d = district_map(db)[district_id]
    rows = fetch(db, district_id=district_id, year=year)

    modules = []
    for mid, m in mods.items():
        sub = [r for r in rows if r.module_id == mid]
        agg = rollup(sub, m.lower_is_better)
        modules.append(
            {
                "module_id": mid,
                "name": m.short or m.name,
                "unit": m.unit,
                "plan": agg.plan,
                "fact": agg.fact,
                "performance": agg.performance,
                "status": agg.status,
                "yoy": yoy_growth(db, mid, district_id),
            }
        )

    overall = sum(x["performance"] for x in modules) / len(modules) if modules else 1.0
    return {
        "district": {
            "id": d.id,
            "name": d.name,
            "center": d.center,
            "population": d.population,
            "area_km2": d.area_km2,
        },
        "modules": modules,
        "overall": round(overall, 4),
        "status": status_from_ratio(overall, False),
    }


def headline_stats(db: Session, module_id: str | None, year: int) -> dict:
    mods = module_map(db)
    ids = [module_id] if module_id else list(mods)

    perfs = []
    for mid in ids:
        rows = fetch(db, module_id=mid, year=year)
        perfs.append(rollup(rows, mods[mid].lower_is_better).performance)

    spots = weak_spots(db, year, module_id=module_id, limit=500)
    return {
        "performance": round(sum(perfs) / len(perfs), 4) if perfs else 1.0,
        "growth": round(sum(yoy_growth(db, mid) for mid in ids) / len(ids), 2) if ids else 0.0,
        "critical": sum(1 for s in spots if s["status"] == "critical"),
        "at_risk": sum(1 for s in spots if s["status"] == "at_risk"),
        "records": len(fetch(db, module_id=module_id, year=year)),
    }
