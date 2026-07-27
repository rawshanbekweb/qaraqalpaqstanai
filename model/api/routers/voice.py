"""
Voice (Ovozli javob) API
==========================
Foydalanuvchi mavzu aytadi → RAG javob → Karakalpaqsha ovoz

Endpointlar:
  POST /voice/ask         — Mavzu bo'yicha ovozli javob
  GET  /voice/listen/{id} — Audio faylni yuklash/eshitish
  GET  /voice/ovozlar     — Mavjud ovozlar ro'yhati
"""

import os
import sys

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from api.database import get_db
from src.tts import matn_ovozga, OVOZLAR, tozala_cache

router = APIRouter(prefix="/voice", tags=["Ovozli javob"])


class VoiceRequest(BaseModel):
    mavzu:      str                    # "investitsiya", "eksport", "jumissizliq"...
    til:        str  = "kk"           # kk = Karakalpaqsha (default)
    ovoz:       str  = "ayol"         # ayol | erkak
    tezlik:     str  = "-5%"          # sekin: -10%, normal: +0%, tez: +10%
    year:       Optional[int] = None
    region:     Optional[str] = None


@router.post("/ask")
def voice_ask(
    req: VoiceRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Mavzu bo'yicha Karakalpaqsha ovozli javob.
    1. RAG → naqiy sanlar bilan matn
    2. from-to.uz → Karakalpaqsha tarjima
    3. edge-tts → MP3 audio
    """
    from api.services import ai_service

    # 1. DB dan kontekst (admin kiritgan ma'lumotlar)
    from api.database import EconomicIndicator
    q = db.query(EconomicIndicator)
    if req.year:   q = q.filter(EconomicIndicator.year   == req.year)
    if req.region: q = q.filter(EconomicIndicator.region == req.region)
    db_items = [
        {"module": i.module, "region": i.region, "year": i.year,
         "kpi_planned": i.kpi_planned, "kpi_actual": i.kpi_actual,
         "status": i.status, "comment": i.comment, "unit": i.unit}
        for i in q.limit(20).all()
    ]

    # 2. AI Karakalpaqsha matn
    soraw = req.mavzu
    if req.year:   soraw += f" {req.year}-jil"
    if req.region: soraw += f" {req.region} rayonida"

    kk_matn = ai_service.ask_custom(soraw, {"maǵlıwmat": db_items})

    # 3. Ovozga aylantirish
    try:
        audio_path = matn_ovozga(kk_matn, req.ovoz, req.tezlik)
        audio_name = os.path.basename(audio_path)

        # Eski fayllarni fondan tozalash
        background_tasks.add_task(tozala_cache, 200)

        return {
            "mavzu":      req.mavzu,
            "kk_matn":    kk_matn,
            "audio_url":  f"/voice/listen/{audio_name}",
            "ovoz":       req.ovoz,
            "format":     "mp3",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS xatosi: {e}")


@router.get("/listen/{fayl_nomi}")
def listen(fayl_nomi: str):
    """
    Audio faylni qaytarish (brauzer yoki mobil uchun).
    Frontend: <audio src='/voice/listen/abc.mp3' controls />
    """
    # Xavfsizlik: faqat mp3 fayllarga ruxsat
    if not fayl_nomi.endswith(".mp3") or "/" in fayl_nomi or ".." in fayl_nomi:
        raise HTTPException(status_code=400, detail="Noto'g'ri fayl nomi")

    audio_dir  = os.path.join(os.path.dirname(__file__), "..", "..", "results", "audio")
    audio_path = os.path.join(audio_dir, fayl_nomi)

    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio fayl topilmadi")

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        headers={"Content-Disposition": f"inline; filename={fayl_nomi}"},
    )


@router.get("/ovozlar")
def ovozlar_royxati():
    """Mavjud ovozlar."""
    return {
        "ovozlar": [
            {"id": "ayol",  "nomi": "Aigul",  "jinsi": "Ayol",  "til": "Karakalpaq/Qozoq"},
            {"id": "erkak", "nomi": "Daulet", "jinsi": "Erkak", "til": "Karakalpaq/Qozoq"},
        ],
        "tezliklar": {
            "sekin":   "-15%",
            "normal":  "+0%",
            "tez":     "+15%",
        },
        "misol": {
            "POST /voice/ask": {
                "mavzu":  "investitsiya",
                "ovoz":   "ayol",
                "tezlik": "-5%",
                "year":   2025,
            }
        }
    }
