import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine
from app.routers import ai, analytics, auth, data

logging.basicConfig(level=logging.INFO)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Jadvallar mavjud bo'lmasa yaratiladi (mavjudlariga tegmaydi)."""
    Base.metadata.create_all(engine)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Qoraqalpog'iston — Iqtisodiy monitoring va AI analitika",
    description=(
        "Admin kiritgan ko'rsatkichlar PostgreSQL'da saqlanadi; AI javoblari "
        "aynan shu bazadan olingan kontekst asosida quriladi (RAG)."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(data.router)
app.include_router(analytics.router)
app.include_router(ai.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "claude_enabled": bool(settings.anthropic_api_key)}
