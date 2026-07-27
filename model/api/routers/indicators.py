"""
Kórsetkishler API — CRUD + AI tahlil
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import pandas as pd, io

from api.database import get_db, EconomicIndicator
from api.services import ml_service, ai_service

router = APIRouter(prefix="/indicators", tags=["Kórsetkishler"])


# ─── SXEMALAR ────────────────────────────────────────────────
class IndicatorCreate(BaseModel):
    module:      str
    region:      str
    period:      str
    period_type: str = "yearly"
    year:        int
    month:       Optional[int] = None
    quarter:     Optional[int] = None
    kpi_planned: Optional[float] = None
    kpi_actual:  Optional[float] = None
    unit:        str = "mlrd. som"
    status:      str = "in_progress"
    comment:     Optional[str] = None


class IndicatorOut(BaseModel):
    id:          int
    module:      str
    region:      str
    period:      str
    kpi_planned: Optional[float]
    kpi_actual:  Optional[float]
    unit:        str
    status:      str
    comment:     Optional[str]
    created_at:  datetime

    class Config:
        from_attributes = True


# ─── ENDPOINTLAR ─────────────────────────────────────────────
@router.post("/", response_model=IndicatorOut)
def create_indicator(data: IndicatorCreate, db: Session = Depends(get_db)):
    """Yangi kórsetkish qosiw (manual forma)."""
    item = EconomicIndicator(**data.dict())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/", response_model=List[IndicatorOut])
def list_indicators(
    module:  Optional[str] = None,
    region:  Optional[str] = None,
    year:    Optional[int] = None,
    status:  Optional[str] = None,
    limit:   int = 100,
    db: Session = Depends(get_db)
):
    """Filtrlar bilan kórsetkishlar ro'yhati."""
    q = db.query(EconomicIndicator)
    if module: q = q.filter(EconomicIndicator.module == module)
    if region: q = q.filter(EconomicIndicator.region == region)
    if year:   q = q.filter(EconomicIndicator.year == year)
    if status: q = q.filter(EconomicIndicator.status == status)
    return q.order_by(EconomicIndicator.created_at.desc()).limit(limit).all()


@router.put("/{item_id}", response_model=IndicatorOut)
def update_indicator(item_id: int, data: IndicatorCreate, db: Session = Depends(get_db)):
    """Kórsetkishni yangilash."""
    item = db.query(EconomicIndicator).filter(EconomicIndicator.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Tabılmadı")
    for k, v in data.dict().items():
        setattr(item, k, v)
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}")
def delete_indicator(item_id: int, db: Session = Depends(get_db)):
    item = db.query(EconomicIndicator).filter(EconomicIndicator.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Tabılmadı")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.post("/bulk-upload")
async def bulk_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    CSV/Excel fayl orqali ko'plab kórsetkish yuklash.
    Jadval ustunlari: module, region, period, year, kpi_planned, kpi_actual, unit, status, comment
    """
    content = await file.read()
    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Fayl oqilmadi: {e}")

    required = ["module", "region", "year"]
    for col in required:
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"'{col}' ustuni kerak")

    saved = 0
    errors = []
    for _, row in df.iterrows():
        try:
            item = EconomicIndicator(
                module      = str(row.get("module", "")),
                region      = str(row.get("region", "")),
                period      = str(row.get("period", str(row.get("year", "")))),
                period_type = str(row.get("period_type", "yearly")),
                year        = int(row["year"]),
                month       = int(row["month"])   if "month"   in row and pd.notna(row["month"])   else None,
                quarter     = int(row["quarter"]) if "quarter" in row and pd.notna(row["quarter"]) else None,
                kpi_planned = float(row["kpi_planned"]) if "kpi_planned" in row and pd.notna(row["kpi_planned"]) else None,
                kpi_actual  = float(row["kpi_actual"])  if "kpi_actual"  in row and pd.notna(row["kpi_actual"])  else None,
                unit        = str(row.get("unit", "mlrd. som")),
                status      = str(row.get("status", "in_progress")),
                comment     = str(row["comment"]) if "comment" in row and pd.notna(row["comment"]) else None,
            )
            db.add(item)
            saved += 1
        except Exception as e:
            errors.append(str(e))

    db.commit()
    return {
        "saqlandi": saved,
        "qateler":  len(errors),
        "xabar":    f"{saved} qator muvaffaqiyatli yuklandi"
    }


@router.get("/summary/by-module")
def summary_by_module(year: Optional[int] = None, db: Session = Depends(get_db)):
    """Modul boyınsha juwmaq statistikası."""
    q = db.query(EconomicIndicator)
    if year:
        q = q.filter(EconomicIndicator.year == year)
    items = q.all()

    result = {}
    for item in items:
        mod = item.module
        if mod not in result:
            result[mod] = {"planned": [], "actual": [], "count": 0, "critical": 0}
        if item.kpi_planned: result[mod]["planned"].append(item.kpi_planned)
        if item.kpi_actual:  result[mod]["actual"].append(item.kpi_actual)
        result[mod]["count"] += 1
        if item.status in ("critical", "at_risk"):
            result[mod]["critical"] += 1

    import numpy as np
    summary = {}
    for mod, v in result.items():
        p_avg = float(np.mean(v["planned"])) if v["planned"] else 0
        a_avg = float(np.mean(v["actual"]))  if v["actual"]  else 0
        summary[mod] = {
            "ortasha_rejalan": round(p_avg, 2),
            "ortasha_amalda":  round(a_avg, 2),
            "orindalish_pct":  round(a_avg / p_avg * 100, 1) if p_avg else 0,
            "jámi":            v["count"],
            "qauipli":         v["critical"],
        }
    return summary
