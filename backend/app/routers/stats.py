"""
Excel'dan yuklangan haqiqiy statistika endpointlari.

Eski `/api/analytics/*` reja↔amalda demo ma'lumoti bilan ishlaydi va
admin paneli uchun qoladi. Bosh sahifa esa shu yerdagi `/api/stats/*`
dan oziqlanadi — 1084 ko'rsatkich, 24 199 o'lchov, 2010–2026 yillar.
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingest.excel import parse_bytes
from app.ingest.loader import CATEGORIES, keep_known, load_records
from app.models import StatCategory, StatIndicator, StatObservation
from app.security import require_admin
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


# ── Admin ────────────────────────────────────────────────────────────


@router.get("/summary", dependencies=[Depends(require_admin)])
def summary(db: Session = Depends(get_db)):
    """Admin paneli uchun bazaning holati."""
    per_category = db.execute(
        select(
            StatCategory.id,
            StatCategory.name_kaa,
            StatCategory.source_dir,
            StatCategory.color,
            func.count(StatIndicator.id),
        )
        .outerjoin(StatIndicator, StatIndicator.category_id == StatCategory.id)
        .group_by(StatCategory.id)
        .order_by(StatCategory.sort)
    ).all()

    observations = dict(
        db.execute(
            select(StatIndicator.category_id, func.count(StatObservation.id))
            .join(StatObservation, StatObservation.indicator_id == StatIndicator.id)
            .group_by(StatIndicator.category_id)
        ).all()
    )

    years = st.available_years(db)
    return {
        "years": years,
        "latest_year": years[-1] if years else None,
        "indicators": db.scalar(select(func.count()).select_from(StatIndicator)) or 0,
        "observations": db.scalar(select(func.count()).select_from(StatObservation)) or 0,
        "districts": db.scalar(
            select(func.count(func.distinct(StatObservation.district_id)))
        ) or 0,
        "with_districts": db.scalar(
            select(func.count()).select_from(StatIndicator).where(
                StatIndicator.has_districts.is_(True)
            )
        ) or 0,
        "categories": [
            {
                "id": cid,
                "name": name,
                "source_dir": source_dir,
                "color": color,
                "indicators": n,
                "observations": observations.get(cid, 0),
            }
            for cid, name, source_dir, color, n in per_category
        ],
        #: Yuklash formasidagi tanlov — manba papkalari
        "source_dirs": sorted(CATEGORIES),
        #: Har bir tayanch soha uchun hozir qaysi ko'rsatkich ishlatilyapti
        "modules": [
            {
                "id": module,
                "name": st.MODULE_META[module][0],
                "color": st.MODULE_META[module][2],
                "indicator_id": ind.id,
                "indicator_name": ind.name_kaa,
                "unit": ind.unit,
            }
            for module, ind in st.primary_indicators(db).items()
            if module in st.MODULE_META
        ],
    }


class IndicatorPatch(BaseModel):
    """Ko'rsatkichni tayanch soha sifatida belgilash yoki bo'shatish."""

    #: `sanaat`, `awil_xojaligi`, ... yoki bo'sh satr — biriktirishni uzish
    module: str | None = None
    lower_is_better: bool | None = None


@router.patch("/indicators/{indicator_id}", dependencies=[Depends(require_admin)])
def update_indicator(
    indicator_id: int, payload: IndicatorPatch, db: Session = Depends(get_db)
):
    ind = db.get(StatIndicator, indicator_id)
    if ind is None:
        raise HTTPException(404, "Kórsetkish tabılmadı")

    fields = payload.model_dump(exclude_unset=True)
    if "module" in fields:
        module = (fields["module"] or "").strip() or None
        if module is not None and module not in st.MODULE_META:
            raise HTTPException(400, f"Belgisiz taraw: {module}")
        if module is not None and not ind.has_districts:
            # Tayanch ko'rsatkich xaritani bo'yaydi — rayon kesimisiz
            # xarita bo'sh qoladi, shuning uchun bunday biriktirish rad etiladi
            raise HTTPException(400, "Bul kórsetkishte rayonlar kesimi joq")
        ind.module = module
    if "lower_is_better" in fields:
        ind.lower_is_better = bool(fields["lower_is_better"])

    db.commit()
    db.refresh(ind)
    return st.indicator_detail(db, ind)


@router.post("/upload", dependencies=[Depends(require_admin)])
async def upload_workbook(
    file: UploadFile = File(...),
    category: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Statistika Excel faylini bazaga yuklaydi.

    Fayl qaysi bo'limga tegishli ekani nomidan bilinmaydi (manba
    papkalarida turgan), shuning uchun `category` ochiq beriladi.
    Yuklash faqat SHU fayl tegib o'tgan ko'rsatkichlarni yangilaydi.
    """
    if category not in CATEGORIES:
        raise HTTPException(400, f"Belgisiz bólim: {category}")
    if not (file.filename or "").lower().endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Tek ǵana .xlsx yamasa .xls fayl qabıl etiledi")

    raw = await file.read()
    try:
        records = keep_known(
            parse_bytes(raw, category=category, filename=file.filename or "upload.xlsx")
        )
    except Exception as exc:  # noqa: BLE001 — buzuq fayl 500 bermasin
        raise HTTPException(400, f"Faydı oqıp bolmadı: {exc}") from exc

    if not records:
        raise HTTPException(
            400,
            "Fayldan bir de jazıw alınbadı — dáwir atları bar sarlawha qatarı tabılmadı",
        )

    stats = load_records(records, db, replace_all=False)
    return {"file": file.filename, "category": category, **stats}
