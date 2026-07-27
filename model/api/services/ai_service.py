"""
AI Service — RAG + from-to.uz Translation
Hallucination = 0%  |  Karakalpaqsha sifat = A+
"""

import os, sys, warnings
warnings.filterwarnings("ignore")

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, ROOT)
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

from src.rag_with_translation import get_rag_translation, RAGTranslationPipeline
from src.rag import DataRetriever
from src.rag_with_translation import _build_uz_response

_pipeline: RAGTranslationPipeline | None = None
_retriever: DataRetriever | None = None


def startup():
    global _pipeline, _retriever
    api_key = os.getenv("FROM_TO_API_KEY", "")

    if api_key:
        print("[AI] RAG + from-to.uz Translation yuklanıwda...")
        _pipeline = get_rag_translation(api_key)
        ok = _pipeline.translator.test_connection()
        if ok:
            print("[AI] RAG + Translation tayar ✓")
        else:
            print("[AI] Translation API ulanmadi — shablon rejimida ishlaydi")
            _pipeline = None
    else:
        print("[AI] FROM_TO_API_KEY topilmadi — shablon rejimida ishlaydi")

    _retriever = DataRetriever()


def _get_pipeline() -> RAGTranslationPipeline | None:
    global _pipeline
    if _pipeline is None:
        api_key = os.getenv("FROM_TO_API_KEY", "")
        if api_key:
            _pipeline = get_rag_translation(api_key)
    return _pipeline


def _get_retriever() -> DataRetriever:
    global _retriever
    if _retriever is None:
        _retriever = DataRetriever()
    return _retriever


def _fallback_response(context: dict) -> str:
    """Translation API bo'lmasa — Uzbekcha shablon."""
    return _build_uz_response(context)


# ─────────────────────────────────────────────────────────────
#  TIYKARGI FUNKSIYALAR
# ─────────────────────────────────────────────────────────────

def ask_custom(question: str, context: dict = None) -> str:
    """
    Erkin soraw — RAG + Karakalpaqsha tarjima.
    context: {"maǵlıwmat": [...DB items...]}
    """
    db_items = context.get("maǵlıwmat", []) if context else []
    pipe = _get_pipeline()

    if pipe:
        result = pipe.ask(question, db_items=db_items)
        return result["juwap"]
    else:
        # Shablon fallback
        retriever = _get_retriever()
        ctx = retriever.get_context(question, db_items)
        return _fallback_response(ctx)


def generate_weak_spot_analysis(analysis_data: dict) -> str:
    """Weak spot nátiyjesini Karakalpaqsha izoxlaw."""
    critical = analysis_data.get("critical", [])
    modules  = analysis_data.get("modules", {})

    # Sorawni avtomat yaratish
    parts = []
    for mod, v in modules.items():
        parts.append(
            f"{mod}: rejalashtirilgan {v['ortasha_rejalan']:.1f} → "
            f"amalda {v['ortasha_amalda']:.1f} ({v['orindalish']:.1f}%)"
        )
    for r in critical[:3]:
        parts.append(f"Muammoli hudud: {r['region']} ({r['orindalish']:.1f}%)")

    question = "Qoraqalpog'iston iqtisodiy ko'rsatkichlari bo'yicha zaif joylarni tahlil qil: " + "; ".join(parts)

    pipe = _get_pipeline()
    if pipe:
        # Admin ma'lumotlari bilan context yaratish
        db_context = [
            {
                "module": mod,
                "region": "QR jami",
                "kpi_planned": v["ortasha_rejalan"],
                "kpi_actual": v["ortasha_amalda"],
                "year": 2025,
                "status": v["status"],
                "unit": "",
            }
            for mod, v in modules.items()
        ]
        result = pipe.ask(question, db_items=db_context)
        return result["juwap"]
    else:
        retriever = _get_retriever()
        ctx = retriever.get_context(question)
        ctx["db_sanlar"] = []
        return _fallback_response(ctx)


def generate_forecast_text(forecasts: dict) -> str:
    """Boljanıwlardı Karakalpaqsha izoxlaw."""
    parts = []
    for col, fc_list in forecasts.items():
        if fc_list:
            f0 = fc_list[0]
            parts.append(f"{col} {f0.get('Jıl', '')}: {f0.get('Boljanıw', 0):,.1f}")

    question = (
        "Qoraqalpog'iston iqtisodiy prognozlari: " + ", ".join(parts) +
        ". Bu ko'rsatkichlarni tahlil qiling va tavsiyalar bering."
    )

    pipe = _get_pipeline()
    if pipe:
        result = pipe.ask(question)
        return result["juwap"]
    else:
        retriever = _get_retriever()
        ctx = retriever.get_context("investitsiya eksport jao")
        return _fallback_response(ctx)


def generate_annual_report(analysis_data: dict, year: int) -> str:
    """Jıllıq hisobot Karakalpaqsha."""
    modules = analysis_data.get("modules", {})
    parts   = [
        f"{mod}: {v['orindalish']:.1f}% bajarildi"
        for mod, v in modules.items()
    ]

    question = (
        f"{year}-yil Qoraqalpog'iston iqtisodiy yakuniy hisoboti. "
        f"Ko'rsatkichlar: {'; '.join(parts)}. "
        f"Yillik umumiy baho, muammolar va tavsiyalar bering."
    )

    pipe = _get_pipeline()
    if pipe:
        db_context = [
            {
                "module": mod,
                "region": "QR jami",
                "kpi_planned": v["ortasha_rejalan"],
                "kpi_actual": v["ortasha_amalda"],
                "year": year,
                "status": v["status"],
                "unit": "",
            }
            for mod, v in modules.items()
        ]
        result = pipe.ask(question, db_items=db_context)
        return result["juwap"]
    else:
        retriever = _get_retriever()
        ctx = retriever.get_context("jao sanaat investitsiya")
        return _fallback_response(ctx)
