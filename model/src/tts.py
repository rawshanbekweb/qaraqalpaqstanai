"""
Text-to-Speech (Ovozli javob) moduli
=====================================
Karakalpaqsha matnni ovozga aylantiradi.
Microsoft Edge TTS — Qozoq ovozi (kk-KZ)
Karakalpaqsha va Qozoqsha juda yaqin — ovoz ishlaydi.
"""

import os
import asyncio
import hashlib
import edge_tts

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

# Ovoz sozlamalari
OVOZLAR = {
    "ayol":  "kk-KZ-AigulNeural",   # Aigul — ayol ovozi
    "erkak": "kk-KZ-DauletNeural",  # Daulet — erkak ovozi
}
DEFAULT_OVOZ = "ayol"


async def _matn_ovozga(
    matn: str,
    ovoz_turi: str = DEFAULT_OVOZ,
    tezlik: str = "-5%",     # sekinroq = aniqroq
    ton: str = "+0Hz",
) -> str:
    """
    Matnni MP3 ga aylantiradi, fayl yo'lini qaytaradi.
    Cache: bir xil matn qayta generatsiya qilinmaydi.
    """
    ovoz = OVOZLAR.get(ovoz_turi, OVOZLAR["ayol"])

    # Cache kalit — matn + ovoz + sozlamalar
    cache_key  = hashlib.md5(f"{matn}{ovoz}{tezlik}".encode()).hexdigest()[:12]
    audio_path = os.path.join(AUDIO_DIR, f"{cache_key}.mp3")

    if os.path.exists(audio_path):
        return audio_path  # Cache dan qaytarish

    comm = edge_tts.Communicate(matn, ovoz, rate=tezlik, pitch=ton)
    await comm.save(audio_path)
    return audio_path


def matn_ovozga(
    matn: str,
    ovoz_turi: str = DEFAULT_OVOZ,
    tezlik: str = "-5%",
) -> str:
    """
    Sinxron wrapper — asyncio loop yaratadi.
    FastAPI thread pool da chaqirish uchun.
    """
    # Matnni tozalash
    import re
    clean = re.sub(r"#+\s*", "", matn)    # markdown headings
    clean = re.sub(r"\*+", "", clean)      # bold/italic
    clean = re.sub(r"-{3,}", "", clean)    # dividers
    clean = clean.strip()

    # Uzun matnni qisqartirish (TTS uchun max ~2000 belgi)
    if len(clean) > 2000:
        clean = clean[:1950] + "..."

    loop = asyncio.new_event_loop()
    try:
        path = loop.run_until_complete(
            _matn_ovozga(clean, ovoz_turi, tezlik)
        )
    finally:
        loop.close()
    return path


def tozala_cache(max_fayllar: int = 100):
    """Eski audio fayllarni o'chirish."""
    fayllar = sorted(
        [os.path.join(AUDIO_DIR, f) for f in os.listdir(AUDIO_DIR)
         if f.endswith(".mp3")],
        key=os.path.getmtime
    )
    if len(fayllar) > max_fayllar:
        for f in fayllar[:-max_fayllar]:
            os.remove(f)
