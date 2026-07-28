"""
Excel'dan yuklangan haqiqiy statistika endpointlari.

Eski `/api/analytics/*` reja↔amalda demo ma'lumoti bilan ishlaydi va
admin paneli uchun qoladi. Bosh sahifa esa shu yerdagi `/api/stats/*`
dan oziqlanadi — 1084 ko'rsatkich, 24 199 o'lchov, 2010–2026 yillar.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StatIndicator
from app.services import stats as st

router = APIRouter(prefix="/api/stats", tags=["stats"])


def _resolve(
    db: Session, indicator_id: int | None, module: str | None
) -> StatIndicator:
    ind = st.resolve_indicator(db, indicator_id=indicator_id, module=module)
    if ind is None:
        raise HTTPException(404, "Kórsetkish tabılmadı")
    return ind


def _year(db: Session, year: int | None, indicator_id: int | None = None) -> int:
    return year or st.latest_year(db, indicator_id)


@router.get("/meta")
def meta(db: Session = Depends(get_db)):
    """Boshlang'ich ma'lumot: yillar, sohalar, kategoriyalar, hududlar."""
    return st.meta(db)


@router.get("/overview")
def overview(year: int | None = None, db: Session = Depends(get_db)):
    return st.overview(db, _year(db, year))


@router.get("/map")
def map_layer(
    module: str | None = None,
    indicator_id: int | None = None,
    year: int | None = None,
    db: Session = Depends(get_db),
):
    """Xarita qatlami — tuman kesimidagi qiymatlar va rang jadali."""
    ind = _resolve(db, indicator_id, module)
    if not ind.has_districts:
        raise HTTPException(400, "Bul kórsetkishte rayonlar kesimi joq")
    return st.map_layer(db, ind, _year(db, year, ind.id))


@router.get("/series")
def series(
    module: str | None = None,
    indicator_id: int | None = None,
    district_id: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    db: Session = Depends(get_db),
):
    """Yillar kesimidagi qator (2010–2026)."""
    ind = _resolve(db, indicator_id, module)
    return {
        "indicator": st.indicator_brief(ind),
        "district_id": district_id,
        "unit": ind.unit,
        "points": st.series(
            db, ind, district_id=district_id, year_from=year_from, year_to=year_to
        ),
    }


@router.get("/districts/{district_id}")
def district_profile(
    district_id: str, year: int | None = None, db: Session = Depends(get_db)
):
    profile = st.district_profile(db, district_id, _year(db, year))
    if profile is None:
        raise HTTPException(404, "Aymaq tabılmadı")
    return profile


@router.get("/categories")
def categories(db: Session = Depends(get_db)):
    return st.meta(db)["categories"]


@router.get("/indicators")
def indicators(
    q: str | None = None,
    category_id: str | None = None,
    module: str | None = None,
    has_districts: bool | None = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Ko'rsatkichlar ma'lumotnomasi — qidiruv va sahifalash bilan."""
    return st.search_indicators(
        db,
        q=q,
        category_id=category_id,
        module=module,
        has_districts=has_districts,
        limit=limit,
        offset=offset,
    )


@router.get("/indicators/{indicator_id}")
def indicator_detail(indicator_id: int, db: Session = Depends(get_db)):
    return st.indicator_detail(db, _resolve(db, indicator_id, None))
