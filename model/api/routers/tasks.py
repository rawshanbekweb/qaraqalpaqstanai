"""
Topshiriqlar API — Task Management
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from api.database import get_db, Task

router = APIRouter(prefix="/tasks", tags=["Topshiriqlar"])


class TaskCreate(BaseModel):
    title:       str
    module:      str
    region:      str
    description: Optional[str] = None
    deadline:    Optional[datetime] = None
    responsible: Optional[str] = None
    status:      str = "in_progress"
    priority:    str = "medium"


class TaskOut(BaseModel):
    id:          int
    title:       str
    module:      str
    region:      str
    description: Optional[str]
    deadline:    Optional[datetime]
    responsible: Optional[str]
    status:      str
    priority:    str
    created_at:  datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=TaskOut)
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    task = Task(**data.dict())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/", response_model=List[TaskOut])
def list_tasks(
    module:  Optional[str] = None,
    region:  Optional[str] = None,
    status:  Optional[str] = None,
    limit:   int = 100,
    db: Session = Depends(get_db)
):
    q = db.query(Task)
    if module: q = q.filter(Task.module == module)
    if region: q = q.filter(Task.region == region)
    if status: q = q.filter(Task.status == status)
    return q.order_by(Task.created_at.desc()).limit(limit).all()


@router.put("/{task_id}/status")
def update_task_status(task_id: int, status: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Topshiriq tabılmadı")
    task.status = status
    db.commit()
    return {"ok": True, "status": status}


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tabılmadı")
    db.delete(task)
    db.commit()
    return {"ok": True}
