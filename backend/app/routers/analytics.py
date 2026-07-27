from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import analytics as an
from app.services import charts as ch

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _year(db: Session, year: int | None) -> int:
    return year or an.latest_year(db)


@router.get("/overview")
def overview(module_id: str | None = None, year: int | None = None, db: Session = Depends(get_db)):
    y = _year(db, year)
    return {
        "year": y,
        "stats": an.headline_stats(db, module_id, y),
        "districts": an.district_scores(db, module_id, y),
        "weak_spots": an.weak_spots(db, y, module_id=module_id, limit=8),
    }


@router.get("/districts/{district_id}")
def district_detail(district_id: str, year: int | None = None, db: Session = Depends(get_db)):
    return an.district_profile(db, district_id, _year(db, year))


@router.get("/series")
def series(
    module_id: str,
    district_id: str | None = None,
    period: str = "month",
    year: int | None = None,
    db: Session = Depends(get_db),
):
    y = _year(db, year)
    if period == "quarter":
        return an.quarterly_series(db, module_id, district_id, y)
    return an.monthly_series(db, module_id, district_id, y)


@router.get("/weak-spots")
def weak_spots(
    module_id: str | None = None,
    district_id: str | None = None,
    year: int | None = None,
    limit: int = 12,
    db: Session = Depends(get_db),
):
    return an.weak_spots(
        db, _year(db, year), module_id=module_id, district_id=district_id, limit=limit
    )


@router.get("/charts/{kind}")
def chart(
    kind: str,
    module_id: str | None = None,
    district_id: str | None = None,
    year: int | None = None,
    db: Session = Depends(get_db),
):
    """Tayyor ChartSpec qaytaradi — frontend uni to'g'ridan-to'g'ri chizadi."""
    spec = ch.build(db, kind, module_id=module_id, district_id=district_id, year=_year(db, year))
    return spec
