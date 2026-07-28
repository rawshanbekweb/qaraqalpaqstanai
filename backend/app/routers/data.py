"""Ma'lumotnomalar (hududlar, sohalar) va iqtisodiy topshiriqlar.

Statistika ko'rsatkichlari bu yerda emas — ular `/api/stats/*` da.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import District, EconomicTask, Module
from app.schemas import DistrictOut, ModuleOut, TaskIn, TaskOut, TaskUpdate
from app.security import require_admin

router = APIRouter(prefix="/api", tags=["data"])


# ── Ma'lumotnomalar ──────────────────────────────────────────────────


@router.get("/districts", response_model=list[DistrictOut])
def list_districts(db: Session = Depends(get_db)):
    return db.scalars(select(District).order_by(District.name)).all()


@router.get("/modules", response_model=list[ModuleOut])
def list_modules(db: Session = Depends(get_db)):
    return db.scalars(select(Module)).all()


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
        raise HTTPException(400, f"Belgisiz aymaq: {payload.district_id}")
    if db.get(Module, payload.module_id) is None:
        raise HTTPException(400, f"Belgisiz taraw: {payload.module_id}")

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
        raise HTTPException(404, "Tapsırma tabılmadı")

    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(400, "Jańalaw ushın bir de maydan jiberilmedi")

    for key, value in fields.items():
        setattr(task, key, value)

    # Status ochiq berilmagan bo'lsa — bajarilish foizidan kelib chiqib aniqlanadi
    if "progress" in fields and "status" not in fields:
        task.status = _status_from_progress(task.progress)

    db.commit()
    db.refresh(task)
    return task


@router.delete("/tasks/{task_id}", dependencies=[Depends(require_admin)])
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(EconomicTask, task_id)
    if not task:
        raise HTTPException(404, "Tapsırma tabılmadı")
    db.delete(task)
    db.commit()
    return {"ok": True}
