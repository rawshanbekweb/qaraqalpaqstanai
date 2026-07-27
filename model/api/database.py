"""
PostgreSQL ulanıwı — SQLAlchemy
"""

import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/karakalpak_monitoring"
)

engine = engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ─────────────────────────────────────────────────────────────
#  STATUS ENUM
# ─────────────────────────────────────────────────────────────
class StatusEnum(str, enum.Enum):
    in_progress = "in_progress"
    completed   = "completed"
    at_risk     = "at_risk"
    critical    = "critical"


class PeriodEnum(str, enum.Enum):
    monthly   = "monthly"
    quarterly = "quarterly"
    yearly    = "yearly"


# ─────────────────────────────────────────────────────────────
#  JADWALLAR (TABLES)
# ─────────────────────────────────────────────────────────────
class EconomicIndicator(Base):
    """
    Tiykarǵı ekonomikalıq kórsetkishler jadvali.
    Admin panel arqalı toltiriladi.
    """
    __tablename__ = "economic_indicators"

    id          = Column(Integer, primary_key=True, index=True)
    module      = Column(String(50),  nullable=False)   # inflation, industry, agriculture...
    region      = Column(String(100), nullable=False)   # Nukus, Amudaryo, QR umumiy...
    period      = Column(String(20),  nullable=False)   # 2025-Q1, 2025-01, 2025
    period_type = Column(String(20),  default="yearly") # monthly/quarterly/yearly
    year        = Column(Integer,     nullable=False)
    month       = Column(Integer,     nullable=True)
    quarter     = Column(Integer,     nullable=True)

    kpi_planned = Column(Float,   nullable=True)   # Rejalashtirilgan
    kpi_actual  = Column(Float,   nullable=True)   # Amaldagi
    unit        = Column(String(30), default="mlrd. som")

    status      = Column(String(20), default="in_progress")
    comment     = Column(Text, nullable=True)   # "Eksport 12% kamaydi, sababi..."

    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Task(Base):
    """
    Iqtisodiy topshiriqlar (Task Management).
    """
    __tablename__ = "tasks"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(200), nullable=False)
    module      = Column(String(50),  nullable=False)
    region      = Column(String(100), nullable=False)
    description = Column(Text,     nullable=True)
    deadline    = Column(DateTime, nullable=True)
    responsible = Column(String(100), nullable=True)
    status      = Column(String(20),  default="in_progress")
    priority    = Column(String(20),  default="medium")
    created_at  = Column(DateTime, default=datetime.utcnow)


class AIAnalysis(Base):
    """
    AI tahlil natijalari cache (qayta hisoblamasliq ushın).
    """
    __tablename__ = "ai_analysis"

    id          = Column(Integer, primary_key=True, index=True)
    module      = Column(String(50),  nullable=True)
    region      = Column(String(100), nullable=True)
    year        = Column(Integer,     nullable=True)
    analysis_type = Column(String(50))   # weak_spot / forecast / summary
    result_json = Column(Text)           # JSON formatda
    kk_text     = Column(Text)           # Karakalpaksha matn
    created_at  = Column(DateTime, default=datetime.utcnow)


class VoteTypeEnum(str, enum.Enum):
    ha_yoq     = "ha_yoq"      # Ha / Yo'q
    baho        = "baho"        # 1-5 yulduz
    tanlov      = "tanlov"      # Ko'p variant


class Golosovanie(Base):
    """
    Ovoz berish (Golosovanie) jadvali.
    Har qanday mavzu bo'yicha ovoz olish uchun.
    """
    __tablename__ = "golosovanie"

    id          = Column(Integer, primary_key=True, index=True)
    sarlavha    = Column(String(300), nullable=False)   # Ovoz mavzusi
    tavsif      = Column(Text,    nullable=True)
    tur         = Column(String(20), default="ha_yoq")  # ha_yoq / baho / tanlov
    variantlar  = Column(Text,    nullable=True)        # JSON: ["Ha", "Yo'q", "Boshqa"]
    modul       = Column(String(50),  nullable=True)    # bog'liq modul
    region      = Column(String(100), nullable=True)
    yaratuvchi  = Column(String(100), nullable=True)
    muddati     = Column(DateTime, nullable=True)
    holat       = Column(String(20), default="ochiq")   # ochiq / yopiq
    created_at  = Column(DateTime, default=datetime.utcnow)


class Ovoz(Base):
    """
    Har bir foydalanuvchi ovozi.
    """
    __tablename__ = "ovozlar"

    id              = Column(Integer, primary_key=True, index=True)
    golosovanie_id  = Column(Integer, nullable=False, index=True)
    foydalanuvchi   = Column(String(100), nullable=False)  # user ID yoki nom
    variant         = Column(String(200), nullable=False)   # tanlangan variant
    izoh            = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Jadwallar jaratıldı ✓")
