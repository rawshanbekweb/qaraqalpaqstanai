"""
Qaraqalpaqstan Ekonomikalıq Monitoring API
==========================================
Ishlatiw: uvicorn api.main:app --reload --port 8000
"""

import sys, os, io, warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
warnings.filterwarnings("ignore")

if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except AttributeError:
        pass

from dotenv import load_dotenv
load_dotenv()  # .env fayldan API key va DB URL yuklash

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.database import create_tables
from api.routers import indicators, analytics, tasks, voice
from api.services import ml_service, ai_service

app = FastAPI(
    title="Qaraqalpaqstan Ekonomikalıq Monitoring API",
    description="Admin panel, ML analitika va Karakalpaksha AI tavsiyalar",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS (React frontend uchun)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routerlar
app.include_router(indicators.router)
app.include_router(analytics.router)
app.include_router(tasks.router)
app.include_router(voice.router)


@app.on_event("startup")
async def startup_event():
    print("=== API ISHGA TUSHURILDI ===")
    # DB jadvallar
    try:
        create_tables()
    except Exception as e:
        print(f"[DB] Muammo: {e} — PostgreSQL ulanganligini tekshiring")

    # ML modelleri yuklaw
    ml_service.startup()

    # AI model (fine-tuned Qwen3)
    ai_service.startup()
    print("=== API TAYAR ===")


@app.get("/")
def root():
    return {
        "xizmat":   "Qaraqalpaqstan Ekonomikalıq Monitoring API",
        "versiya":  "1.0.0",
        "hujjat":   "/docs",
        "endpointlar": {
            "korsatkishlar": "/indicators",
            "ai_analitika":  "/analytics",
            "topshiriqlar":  "/tasks",
            "ovozli_javob":  "/voice",
        }
    }


@app.get("/health")
def health():
    import torch
    return {
        "status": "ok",
        "gpu":    torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }
