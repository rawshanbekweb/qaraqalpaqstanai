from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class District(Base):
    """Qoraqalpog'iston Respublikasi tumani yoki shahri."""

    __tablename__ = "districts"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(80), default="")
    center: Mapped[str] = mapped_column(String(80), default="")
    area_km2: Mapped[int] = mapped_column(Integer, default=0)
    population: Mapped[float] = mapped_column(Float, default=0)

    indicators: Mapped[list["Indicator"]] = relationship(back_populates="district")
    tasks: Mapped[list["EconomicTask"]] = relationship(back_populates="district")


class Module(Base):
    """Iqtisodiy soha (inflyatsiya, sanoat, qishloq xo'jaligi, ...)."""

    __tablename__ = "modules"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    short: Mapped[str] = mapped_column(String(60), default="")
    unit: Mapped[str] = mapped_column(String(40), default="")
    # Inflyatsiyada ko'rsatkichning pasayishi yaxshi hisoblanadi
    lower_is_better: Mapped[bool] = mapped_column(default=False)
    color: Mapped[str] = mapped_column(String(16), default="#0284c7")

    indicators: Mapped[list["Indicator"]] = relationship(back_populates="module")


class Indicator(Base):
    """Bitta tuman × soha × davr kesimidagi reja va amaldagi ko'rsatkich."""

    __tablename__ = "indicators"
    __table_args__ = (
        UniqueConstraint(
            "district_id", "module_id", "year", "month", name="uq_indicator_period"
        ),
        Index("ix_indicator_lookup", "module_id", "year", "district_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), nullable=False)
    module_id: Mapped[str] = mapped_column(ForeignKey("modules.id"), nullable=False)

    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quarter: Mapped[int | None] = mapped_column(Integer, nullable=True)

    plan: Mapped[float] = mapped_column(Float, default=0)
    fact: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(20), default="in_progress")

    #: Admin qoldirgan izoh. AI kontekstiga aynan shu matn uzatiladi.
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    district: Mapped[District] = relationship(back_populates="indicators")
    module: Mapped[Module] = relationship(back_populates="indicators")


class EconomicTask(Base):
    """Iqtisodiy topshiriq / loyiha."""

    __tablename__ = "economic_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), nullable=False)
    module_id: Mapped[str] = mapped_column(ForeignKey("modules.id"), nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    deadline: Mapped[date] = mapped_column(Date, nullable=False)
    assignee: Mapped[str] = mapped_column(String(120), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    district: Mapped[District] = relationship(back_populates="tasks")


class User(Base):
    """Platforma foydalanuvchisi (admin yoki ko'ruvchi)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), default="")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="viewer")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
