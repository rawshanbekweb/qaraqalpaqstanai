"""Ma'lumotnomalar, ko'rsatkichlar (CRUD + bulk import) va topshiriqlar."""

from __future__ import annotations

import io

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import District, EconomicTask, Indicator, Module
from app.schemas import (
    BulkImportResult,
    DistrictOut,
    IndicatorIn,
    IndicatorOut,
    ModuleOut,
    TaskIn,
    TaskOut,
    TaskUpdate,
)
from app.security import require_admin
from app.services import analytics as an

router = APIRouter(prefix="/api", tags=["data"])


# ── Ma'lumotnomalar ──────────────────────────────────────────────────


@router.get("/districts", response_model=list[DistrictOut])
def list_districts(db: Session = Depends(get_db)):
    return db.scalars(select(District).order_by(District.name)).all()


@router.get("/modules", response_model=list[ModuleOut])
def list_modules(db: Session = Depends(get_db)):
    return db.scalars(select(Module)).all()


# ── Ko'rsatkichlar ───────────────────────────────────────────────────


@router.get("/indicators", response_model=list[IndicatorOut])
def list_indicators(
    db: Session = Depends(get_db),
    module_id: str | None = None,
    district_id: str | None = None,
    year: int | None = None,
    status: str | None = None,
    limit: int = Query(default=500, le=5000),
    offset: int = 0,
):
    stmt = select(Indicator)
    if module_id:
        stmt = stmt.where(Indicator.module_id == module_id)
    if district_id:
        stmt = stmt.where(Indicator.district_id == district_id)
    if year:
        stmt = stmt.where(Indicator.year == year)
    if status:
        stmt = stmt.where(Indicator.status == status)
    stmt = stmt.order_by(Indicator.year.desc(), Indicator.month.desc()).limit(limit).offset(offset)
    return db.scalars(stmt).all()


def _upsert_indicator(db: Session, payload: IndicatorIn) -> tuple[Indicator, bool]:
    module = db.get(Module, payload.module_id)
    if module is None:
        raise HTTPException(400, f"Noma'lum soha: {payload.module_id}")
    if db.get(District, payload.district_id) is None:
        raise HTTPException(400, f"Noma'lum hudud: {payload.district_id}")

    ratio = payload.fact / payload.plan if payload.plan else 1.0
    status = payload.status or an.status_from_ratio(ratio, module.lower_is_better)

    existing = db.scalar(
        select(Indicator).where(
            Indicator.district_id == payload.district_id,
            Indicator.module_id == payload.module_id,
            Indicator.year == payload.year,
            Indicator.month == payload.month,
        )
    )
    if existing:
        existing.plan = payload.plan
        existing.fact = payload.fact
        existing.status = status
        existing.unit = module.unit
        if payload.note is not None:
            existing.note = payload.note
        return existing, False

    row = Indicator(
        district_id=payload.district_id,
        module_id=payload.module_id,
        year=payload.year,
        month=payload.month,
        quarter=((payload.month - 1) // 3 + 1) if payload.month else None,
        plan=payload.plan,
        fact=payload.fact,
        unit=module.unit,
        status=status,
        note=payload.note,
    )
    db.add(row)
    return row, True


@router.post("/indicators", response_model=IndicatorOut, dependencies=[Depends(require_admin)])
def create_indicator(payload: IndicatorIn, db: Session = Depends(get_db)):
    row, _ = _upsert_indicator(db, payload)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/indicators/{indicator_id}", dependencies=[Depends(require_admin)])
def delete_indicator(indicator_id: int, db: Session = Depends(get_db)):
    row = db.get(Indicator, indicator_id)
    if not row:
        raise HTTPException(404, "Yozuv topilmadi")
    db.delete(row)
    db.commit()
    return {"ok": True}


# ── Fayl orqali yuklash ──────────────────────────────────────────────

COLUMN_ALIASES = {
    "modul": "module_id",
    "module": "module_id",
    "soha": "module_id",
    "hudud": "district_id",
    "tuman": "district_id",
    "district": "district_id",
    "yil": "year",
    "oy": "month",
    "reja": "plan",
    "amalda": "fact",
    "izoh": "note",
}


@router.post(
    "/indicators/import",
    response_model=BulkImportResult,
    dependencies=[Depends(require_admin)],
)
async def import_indicators(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Excel (.xlsx/.xls) yoki CSV faylni bazaga yuklaydi.

    Ustunlar: modul · hudud · yil · oy · reja · amalda · izoh
    """
    raw = await file.read()
    name = (file.filename or "").lower()

    try:
        if name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(raw))
        else:
            df = pd.read_csv(io.BytesIO(raw))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"Faylni o'qib bo'lmadi: {exc}") from exc

    df.columns = [COLUMN_ALIASES.get(str(c).strip().lower(), str(c).strip().lower()) for c in df.columns]

    modules = {m.id: m for m in db.scalars(select(Module)).all()}
    module_lookup = {**{m.id.lower(): m.id for m in modules.values()}}
    for m in modules.values():
        module_lookup[m.name.lower()] = m.id
        module_lookup[(m.short or "").lower()] = m.id

    district_lookup: dict[str, str] = {}
    for d in db.scalars(select(District)).all():
        district_lookup[d.id.lower()] = d.id
        district_lookup[d.name.lower().replace("'", "")] = d.id
        district_lookup[(d.name_ru or "").lower()] = d.id

    imported = updated = 0
    errors: list[str] = []

    for idx, record in df.iterrows():
        line = int(idx) + 2  # sarlavha qatorini hisobga olib
        try:
            module_id = module_lookup.get(str(record.get("module_id", "")).strip().lower())
            district_id = district_lookup.get(
                str(record.get("district_id", "")).strip().lower().replace("'", "")
            )
            if not module_id:
                errors.append(f"{line}-qator: soha tanilmadi ({record.get('module_id')})")
                continue
            if not district_id:
                errors.append(f"{line}-qator: hudud tanilmadi ({record.get('district_id')})")
                continue

            month = record.get("month")
            month_val = int(month) if pd.notna(month) else None
            if month_val is not None and not 1 <= month_val <= 12:
                errors.append(f"{line}-qator: oy 1–12 oralig'ida bo'lishi kerak")
                continue

            note = record.get("note")
            payload = IndicatorIn(
                module_id=module_id,
                district_id=district_id,
                year=int(record["year"]),
                month=month_val,
                plan=float(record["plan"]),
                fact=float(record["fact"]),
                note=str(note) if pd.notna(note) else None,
            )
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{line}-qator: {exc}")
            continue

        _, created = _upsert_indicator(db, payload)
        imported += created
        updated += 0 if created else 1

    db.commit()
    return BulkImportResult(imported=imported, updated=updated, errors=errors[:20])


# ── Topshiriqlar ─────────────────────────────────────────────────────


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(
    db: Session = Depends(get_db),
    district_id: str | None = None,
    module_id: str | None = None,
    status: str | None = None,
):
    stmt = select(EconomicTask)
    if district_id:
        stmt = stmt.where(EconomicTask.district_id == district_id)
    if module_id:
        stmt = stmt.where(EconomicTask.module_id == module_id)
    if status:
        stmt = stmt.where(EconomicTask.status == status)
    return db.scalars(stmt.order_by(EconomicTask.deadline)).all()


def _status_from_progress(progress: int) -> str:
    if progress >= 100:
        return "completed"
    if progress >= 60:
        return "in_progress"
    if progress >= 30:
        return "at_risk"
    return "critical"


@router.post("/tasks", response_model=TaskOut, dependencies=[Depends(require_admin)])
def create_task(payload: TaskIn, db: Session = Depends(get_db)):
    if db.get(District, payload.district_id) is None:
        raise HTTPException(400, f"Noma'lum hudud: {payload.district_id}")
    if db.get(Module, payload.module_id) is None:
        raise HTTPException(400, f"Noma'lum soha: {payload.module_id}")

    task = EconomicTask(
        title=payload.title,
        description=payload.description,
        district_id=payload.district_id,
        module_id=payload.module_id,
        deadline=payload.deadline,
        assignee=payload.assignee,
        progress=payload.progress,
        status=payload.status or _status_from_progress(payload.progress),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/tasks/{task_id}", response_model=TaskOut, dependencies=[Depends(require_admin)])
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
):
    task = db.get(EconomicTask, task_id)
    if not task:
        raise HTTPException(404, "Topshiriq topilmadi")

    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(400, "Yangilash uchun hech qanday maydon yuborilmadi")

    for key, value in fields.items():
        setattr(task, key, value)

    # Status ochiq berilmagan bo'lsa — bajarilish foizidan kelib chiqib aniqlanadi
    if "progress" in fields and "status" not in fields:
        task.status = _status_from_progress(task.progress)

    db.commit()
    db.refresh(task)
    return task
