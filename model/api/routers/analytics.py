"""
AI Analitika API — Weak Spot, Forecast, Yillik hisobot
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import json

from api.database import get_db, EconomicIndicator, AIAnalysis
from api.services import ml_service, ai_service

router = APIRouter(prefix="/analytics", tags=["AI Analitika"])


# ─── WEAK SPOT ───────────────────────────────────────────────
@router.get("/weak-spots")
def weak_spots(year: Optional[int] = None, db: Session = Depends(get_db)):
    """
    XGBoost arqalı qauipli rayonlarni aniqlaw.
    Natija: Karakalpaksha AI tahlil + JSON maǵlıwmat.
    """
    # ML tahlil
    critical = ml_service.get_critical_regions(year=year)

    # DB maǵlıwmatlaridan qosimcha kontekst
    q = db.query(EconomicIndicator)
    if year:
        q = q.filter(EconomicIndicator.year == year)
    items = q.all()
    db_analysis = ml_service.analyze_db_indicators(
        [{"module": i.module, "region": i.region,
          "kpi_planned": i.kpi_planned, "kpi_actual": i.kpi_actual,
          "year": i.year} for i in items]
    )

    # AI matn generatsiyası
    combined = {**db_analysis, "ml_critical": critical[:10]}
    kk_text = ai_service.generate_weak_spot_analysis(combined)

    return {
        "ml_natiyjeler": critical[:10],
        "db_natiyjeler": db_analysis,
        "ai_tahlil":     kk_text,
        "jami_qauipli":  len([r for r in critical if r["status"] == "Qauipli"]),
    }


# ─── FORECAST ────────────────────────────────────────────────
@router.get("/forecast")
def forecast(
    indicator: Optional[str] = None,
    periods:   int = Query(default=5, ge=1, le=10),
):
    """
    Prophet + LSTM arqalı keleshek boljanıwları.
    indicator: JAO, Sanaat, Eksport... (bo'sh = hammasi)
    """
    if indicator:
        fc = ml_service.get_forecast(indicator, periods)
        forecasts = {indicator: fc} if fc else {}
    else:
        forecasts = ml_service.get_all_forecasts(periods)

    kk_text = ai_service.generate_forecast_text(forecasts)

    return {
        "boljaniwlar": forecasts,
        "ai_tahlil":   kk_text,
        "periods":     periods,
    }


# ─── YILLIK HISOBOT ──────────────────────────────────────────
@router.get("/annual-report/{year}")
def annual_report(year: int, db: Session = Depends(get_db)):
    """
    Bir yillik juwmaqlawshı AI tahlil.
    Admin kiritgan barcha ma'lumotlar asosida.
    """
    items = db.query(EconomicIndicator).filter(
        EconomicIndicator.year == year
    ).all()

    if not items:
        return {"xabar": f"{year}-jıl ushın maǵlıwmat kiritilmegen"}

    analysis = ml_service.analyze_db_indicators([
        {"module": i.module, "region": i.region,
         "kpi_planned": i.kpi_planned, "kpi_actual": i.kpi_actual,
         "year": i.year, "status": i.status}
        for i in items
    ])

    kk_text = ai_service.generate_annual_report(analysis, year)

    return {
        "jil":       year,
        "statistika": analysis,
        "ai_hisobot": kk_text,
        "jami_qator": len(items),
    }


# ─── ERKIN SORAW ─────────────────────────────────────────────
class QuestionRequest(BaseModel):
    soraw:   str
    year:    Optional[int] = None
    region:  Optional[str] = None
    module:  Optional[str] = None


@router.post("/ask")
def ask_ai(req: QuestionRequest, db: Session = Depends(get_db)):
    """
    Erkin soraw — AI Karakalpaksha juwap beriw.
    Masalan: 'Amudaryo rayon 2025-jilgi ahvali qanday?'
    """
    # Context yigiw
    q = db.query(EconomicIndicator)
    if req.year:   q = q.filter(EconomicIndicator.year   == req.year)
    if req.region: q = q.filter(EconomicIndicator.region == req.region)
    if req.module: q = q.filter(EconomicIndicator.module == req.module)
    items = q.limit(50).all()

    context = [
        {"module": i.module, "region": i.region, "year": i.year,
         "planned": i.kpi_planned, "actual": i.kpi_actual,
         "status": i.status, "comment": i.comment}
        for i in items
    ]

    kk_text = ai_service.ask_custom(req.soraw, {"maǵlıwmat": context})

    return {
        "soraw":   req.soraw,
        "juwap":   kk_text,
        "kontekst_qator": len(context),
    }


# ─── DASHBOARD SUMMARY ───────────────────────────────────────
@router.get("/dashboard")
def dashboard_summary(year: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Frontend Dashboard ushın tolıq summary.
    Barcha ma'lumotlar bir so'rovda.
    """
    # Statistika
    q = db.query(EconomicIndicator)
    if year:
        q = q.filter(EconomicIndicator.year == year)
    items = q.all()

    status_counts = {"in_progress": 0, "completed": 0, "at_risk": 0, "critical": 0}
    for i in items:
        if i.status in status_counts:
            status_counts[i.status] += 1

    # Modul boyinsha
    module_summary = {}
    for i in items:
        if i.module not in module_summary:
            module_summary[i.module] = {"planned": [], "actual": []}
        if i.kpi_planned: module_summary[i.module]["planned"].append(i.kpi_planned)
        if i.kpi_actual:  module_summary[i.module]["actual"].append(i.kpi_actual)

    import numpy as np
    modules_out = {}
    for mod, v in module_summary.items():
        p = float(np.mean(v["planned"])) if v["planned"] else 0
        a = float(np.mean(v["actual"]))  if v["actual"]  else 0
        modules_out[mod] = {
            "planned": round(p, 2),
            "actual":  round(a, 2),
            "pct":     round(a/p*100, 1) if p else 0,
        }

    # Forecast (keyingi 3 yil)
    forecasts = ml_service.get_all_forecasts(periods=3)

    # AI insight (qisqa)
    db_an = ml_service.analyze_db_indicators([
        {"module": i.module, "region": i.region,
         "kpi_planned": i.kpi_planned, "kpi_actual": i.kpi_actual,
         "year": i.year} for i in items
    ])
    ai_insight = ai_service.generate_weak_spot_analysis(db_an)

    return {
        "jami_korsatkich": len(items),
        "status_sanaq":    status_counts,
        "modullar":        modules_out,
        "boljaniwlar":     forecasts,
        "ai_insight":      ai_insight[:500] + "...",  # qisqa versiya
        "qauipli_rayonlar": db_an.get("critical", [])[:5],
    }
