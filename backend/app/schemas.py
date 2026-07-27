from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

StatusId = Literal["completed", "in_progress", "at_risk", "critical"]
Horizon = Literal["short", "mid", "long"]
ChartKind = Literal["line", "area", "bar", "grouped-bar", "dumbbell", "diverging-bar"]


# ── Ma'lumotnomalar ──────────────────────────────────────────────────


class DistrictOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    name_ru: str
    center: str
    area_km2: int
    population: float


class ModuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    short: str
    unit: str
    lower_is_better: bool
    color: str


# ── Ko'rsatkichlar ───────────────────────────────────────────────────


class IndicatorIn(BaseModel):
    district_id: str
    module_id: str
    year: int = Field(ge=2000, le=2100)
    month: int | None = Field(default=None, ge=1, le=12)
    plan: float
    fact: float
    status: StatusId | None = None
    note: str | None = None


class IndicatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    district_id: str
    module_id: str
    year: int
    month: int | None
    quarter: int | None
    plan: float
    fact: float
    unit: str
    status: str
    note: str | None


class BulkImportResult(BaseModel):
    imported: int
    updated: int
    errors: list[str]


# ── Topshiriqlar ─────────────────────────────────────────────────────


class TaskIn(BaseModel):
    title: str
    description: str | None = None
    district_id: str
    module_id: str
    deadline: date
    assignee: str = ""
    progress: int = Field(default=0, ge=0, le=100)
    status: StatusId | None = None


class TaskUpdate(BaseModel):
    """Topshiriqni qisman yangilash — faqat yuborilgan maydonlar o'zgaradi."""

    title: str | None = None
    description: str | None = None
    deadline: date | None = None
    assignee: str | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    status: StatusId | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    district_id: str
    module_id: str
    status: str
    progress: int
    deadline: date
    assignee: str


# ── Analitika ────────────────────────────────────────────────────────


class Rollup(BaseModel):
    plan: float
    fact: float
    ratio: float
    performance: float
    status: StatusId
    count: int


class DistrictScore(BaseModel):
    district_id: str
    name: str
    plan: float
    fact: float
    performance: float
    status: StatusId


class WeakSpot(BaseModel):
    district_id: str
    district_name: str
    module_id: str
    module_name: str
    performance: float
    gap: float
    status: StatusId
    note: str | None = None


# ── Grafiklar (frontend ChartSpec bilan bir xil shakl) ────────────────


class ChartSeries(BaseModel):
    key: str
    label: str
    color: str | None = None


class ChartSpec(BaseModel):
    id: str
    kind: ChartKind
    title: str
    subtitle: str | None = None
    unit: str | None = None
    series: list[ChartSeries]
    data: list[dict[str, str | float | int | None]]


# ── AI ───────────────────────────────────────────────────────────────


class AiInsight(BaseModel):
    headline: str
    body: str
    severity: StatusId
    districts: list[str] = []
    module_id: str | None = None


class Recommendation(BaseModel):
    horizon: Horizon
    title: str
    actions: list[str]
    impact: str


class ChatRequest(BaseModel):
    prompt: str
    district_id: str | None = None
    module_id: str | None = None
    year: int | None = None


class ChatResponse(BaseModel):
    text: str
    charts: list[ChartSpec] = []
    insight: AiInsight | None = None
    recommendations: list[Recommendation] = []
    #: Kontekstga olingan baza yozuvlari soni — RAG shaffofligi uchun
    sources: int = 0
    highlight: list[str] = []
    #: Claude API ishlatildimi yoki mahalliy dvigatelmi
    engine: Literal["claude", "local"] = "local"


# ── Auth ─────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    full_name: str
    role: str
