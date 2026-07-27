"""Demo ma'lumotlar bilan bazani to'ldirish.

Generator frontend'dagi `src/data/dataset.ts` bilan AYNAN bir xil algoritmga
ega (mulberry32 PRNG + FNV-1a xesh + bir xil profillar), shuning uchun backend
ulanganda ham raqamlar o'zgarmaydi.

Ishga tushirish:
    python -m app.seed
"""

from __future__ import annotations

import math
from datetime import date, timedelta

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import District, EconomicTask, Indicator, Module, User
from app.security import hash_password
from app.services.analytics import status_from_ratio

BASE_YEAR = 2025
CURRENT_YEAR = 2026
CURRENT_MONTH = 7

DISTRICTS: list[tuple[str, str, str, str, int, float]] = [
    ("amudaryo", "Amudaryo", "Амударья", "Mang'it", 2300, 200.3),
    ("beruniy", "Beruniy", "Беруни", "Beruniy", 4000, 205.1),
    ("bozatov", "Bo'zatov", "Бозатау", "Bo'zatov", 3000, 20.4),
    ("chimboy", "Chimboy", "Чимбай", "Chimboy", 3000, 120.9),
    ("ellikqala", "Ellikqal'a", "Элликкала", "Bo'ston", 4900, 155.8),
    ("karaozak", "Qorao'zak", "Караузяк", "Qorao'zak", 5800, 60.3),
    ("kegeyli", "Kegeyli", "Кегейли", "Kegeyli", 2200, 90.5),
    ("moynoq", "Mo'ynoq", "Муйнак", "Mo'ynoq", 37600, 30.2),
    ("nukus-shahri", "Nukus shahri", "город Нукус", "Nukus", 220, 335.8),
    ("nukus-tumani", "Nukus tumani", "Нукусский район", "Oqmang'it", 2000, 55.7),
    ("qanlikol", "Qanliko'l", "Канлыкуль", "Qanliko'l", 900, 45.6),
    ("qongirot", "Qo'ng'irot", "Кунград", "Qo'ng'irot", 78700, 130.4),
    ("shumanay", "Shumanay", "Шуманай", "Shumanay", 800, 55.1),
    ("taxiatosh", "Taxiatosh", "Тахиаташ", "Taxiatosh", 200, 45.9),
    ("taxtakopir", "Taxtako'pir", "Тахтакупыр", "Taxtako'pir", 20100, 40.7),
    ("tortkol", "To'rtko'l", "Турткуль", "To'rtko'l", 7900, 220.6),
    ("xojayli", "Xo'jayli", "Ходжейли", "Xo'jayli", 1300, 165.2),
]

MODULES: list[tuple[str, str, str, str, bool, str]] = [
    ("inflation", "Inflyatsiya", "Inflyatsiya", "%", True, "#e11d48"),
    ("industry", "Sanoat ishlab chiqarish", "Sanoat", "mlrd so'm", False, "#0284c7"),
    ("agriculture", "Qishloq xo'jaligi", "Qishloq x/j", "mlrd so'm", False, "#65a30d"),
    ("investment", "Investitsiyalar", "Investitsiya", "mlrd so'm", False, "#8b5cf6"),
    ("export", "Eksport hajmi", "Eksport", "mln $", False, "#0891b2"),
    ("employment", "Bandlik", "Bandlik", "ming kishi", False, "#d97706"),
    ("construction", "Qurilish", "Qurilish", "mlrd so'm", False, "#c026d3"),
    ("services", "Xizmatlar sohasi", "Xizmatlar", "mlrd so'm", False, "#059669"),
]

#: Tumanning modul bo'yicha "bajarilish kayfiyati" (1.0 = rejaga to'liq mos)
PROFILE: dict[str, dict[str, float]] = {
    "amudaryo": {"agriculture": 0.71, "export": 0.68, "employment": 0.92},
    "beruniy": {"agriculture": 0.74, "export": 0.72, "investment": 0.95},
    "moynoq": {"agriculture": 0.58, "employment": 0.79, "investment": 0.83, "services": 0.86},
    "taxtakopir": {"industry": 0.81, "services": 0.84, "investment": 0.88},
    "bozatov": {"industry": 0.83, "services": 0.87, "agriculture": 0.9},
    "karaozak": {"industry": 0.89, "export": 0.87},
    "qanlikol": {"investment": 0.88, "industry": 0.91},
    "shumanay": {"export": 0.86, "investment": 0.9},
    "kegeyli": {"agriculture": 0.94},
    "chimboy": {"agriculture": 1.02, "export": 0.93},
    "nukus-shahri": {"services": 1.12, "industry": 1.08, "investment": 1.14, "employment": 1.06},
    "nukus-tumani": {"construction": 1.06, "services": 1.03},
    "qongirot": {"industry": 1.15, "export": 1.09, "investment": 1.07},
    "xojayli": {"industry": 1.04, "construction": 1.05},
    "taxiatosh": {"industry": 1.09, "employment": 1.02},
    "tortkol": {"agriculture": 1.06, "employment": 1.01},
    "ellikqala": {"agriculture": 1.04, "construction": 0.93},
}

NOTES: dict[str, list[str]] = {
    "agriculture": [
        "Sug'orish suvi limiti qisqartirildi, ekin maydonlarining bir qismi quruq qoldi.",
        "Tomchilatib sug'orish tizimi rejadagidan sekin joriy etilmoqda.",
        "Yer sho'rlanishi darajasi oshdi, hosildorlik pasaydi.",
        "Urug'lik va mineral o'g'it narxlari oshgani tannarxni ko'tardi.",
    ],
    "export": [
        "Logistika narxlari oshgani eksport tannarxini qimmatlashtirdi.",
        "Asosiy xaridor bozorida talab pasaydi, shartnomalar qayta ko'rib chiqilmoqda.",
        "Sertifikatlash muddatlari cho'zilib, jo'natmalar kechikdi.",
    ],
    "industry": [
        "Ishlab chiqarish quvvatlari to'liq yuklanmagan, xom ashyo yetkazib berish uzildi.",
        "Elektr ta'minotidagi uzilishlar smenalar sonini kamaytirdi.",
        "Yangi ishlab chiqarish liniyasi ishga tushirildi, quvvat oshdi.",
    ],
    "investment": [
        "Xorijiy investor bilan shartnoma imzolanish bosqichida.",
        "Loyiha hujjatlarini tasdiqlash kechikdi, moliyalashtirish sekinlashdi.",
        "Bank kreditlari stavkasi oshgani xususiy investitsiyani sekinlashtirdi.",
    ],
    "employment": [
        "Mavsumiy ish o'rinlari qisqardi, mehnat migratsiyasi kuchaydi.",
        "Yangi korxona ochilishi bilan doimiy ish o'rinlari yaratildi.",
        "Kasb-hunar o'quv markazlari bitiruvchilari bandligi past.",
    ],
    "inflation": [
        "Oziq-ovqat guruhida narxlar sezilarli oshdi.",
        "Yoqilg'i va transport xarajatlari inflyatsiyani kuchaytirdi.",
        "Narxlar barqarorlashdi, mavsumiy pasayish kuzatildi.",
    ],
    "construction": [
        "Qurilish materiallari yetkazib berish kechikdi.",
        "Ijtimoiy obyektlar qurilishi jadvaldan oldinda bormoqda.",
    ],
    "services": [
        "Turizm oqimi oshdi, xizmatlar hajmi kengaydi.",
        "Raqamli xizmatlar ulushi sekin o'smoqda.",
    ],
}

TASK_TEMPLATES = [
    ("Tomchilatib sug'orish maydonlarini 20% ga kengaytirish", "agriculture"),
    ("Sho'rlangan yerlarni melioratsiya qilish dasturi", "agriculture"),
    ("Eksport yo'nalishlarini diversifikatsiya qilish", "export"),
    ("Logistika markazini ishga tushirish", "export"),
    ("Kichik sanoat zonasini kengaytirish", "industry"),
    ("Ishlab chiqarish quvvatlarini modernizatsiya qilish", "industry"),
    ("Xorijiy investorlar bilan 3 ta shartnoma imzolash", "investment"),
    ("Yoshlar tadbirkorligini qo'llab-quvvatlash dasturi", "employment"),
    ("Kasb-hunar markazlarida qayta tayyorlash kurslari", "employment"),
    ("Ijtimoiy uy-joy qurilishini yakunlash", "construction"),
    ("Turizm infratuzilmasini rivojlantirish", "services"),
    ("Iste'mol savatidagi narxlarni monitoring qilish", "inflation"),
]

ASSIGNEES = [
    "R. Sultonov",
    "G. Qalandarova",
    "A. Yusupov",
    "M. Seytniyazova",
    "B. Reymov",
    "N. Allambergenova",
    "J. Qurbonboyev",
]

U32 = 0xFFFFFFFF


def mulberry32(seed: int):
    """JS `mulberry32` ning aynan ekvivalenti (32-bitli arifmetika)."""
    state = seed & U32

    def rnd() -> float:
        nonlocal state
        state = (state + 0x6D2B79F5) & U32
        t = state
        t = (t ^ (t >> 15)) * (1 | t) & U32
        t = (t + ((t ^ (t >> 7)) * (61 | t) & U32)) & U32
        t = t ^ (t >> 14)
        return (t & U32) / 4294967296

    return rnd


def fnv1a(text: str) -> int:
    h = 2166136261
    for ch in text:
        h ^= ord(ch)
        h = (h * 16777619) & U32
    return h & U32


def scale_for(district: tuple, module_id: str) -> float:
    _, _, _, _, area, pop = district
    if module_id == "inflation":
        return 1.0
    if module_id == "employment":
        return pop * 0.42
    if module_id == "industry":
        return pop * 7.4 + area * 0.05
    if module_id == "agriculture":
        return pop * 5.1 + area * 0.02
    if module_id == "investment":
        return pop * 4.3
    if module_id == "export":
        return pop * 0.55
    if module_id == "construction":
        return pop * 3.1
    return pop * 6.2  # services


def seasonality(module_id: str, month: int) -> float:
    m = month - 1
    if module_id == "agriculture":
        return 0.55 + 0.9 * max(0.0, math.sin(((m - 2) / 12) * math.pi * 1.6))
    if module_id == "construction":
        return 0.6 + 0.7 * max(0.0, math.sin(((m - 1.5) / 12) * math.pi * 1.7))
    if module_id == "export":
        return 0.82 + 0.36 * math.sin(((m - 3) / 12) * math.pi * 2)
    if module_id == "inflation":
        return 1.0
    return 0.93 + 0.14 * math.sin((m / 12) * math.pi * 2)


def seed_reference(db) -> None:
    for row in DISTRICTS:
        did, name, name_ru, center, area, pop = row
        if db.get(District, did) is None:
            db.add(
                District(
                    id=did,
                    name=name,
                    name_ru=name_ru,
                    center=center,
                    area_km2=area,
                    population=pop,
                )
            )
    for mid, name, short, unit, lower, color in MODULES:
        if db.get(Module, mid) is None:
            db.add(
                Module(
                    id=mid,
                    name=name,
                    short=short,
                    unit=unit,
                    lower_is_better=lower,
                    color=color,
                )
            )
    db.commit()


def seed_indicators(db) -> int:
    if db.scalar(select(Indicator).limit(1)) is not None:
        return 0

    district_by_id = {d[0]: d for d in DISTRICTS}
    created = 0

    for district in DISTRICTS:
        did = district[0]
        for mid, _, _, unit, lower_is_better, _ in MODULES:
            rnd = mulberry32(fnv1a(f"{did}:{mid}"))
            profile = PROFILE.get(did, {}).get(mid, 1.0)
            base_scale = scale_for(district_by_id[did], mid)
            yoy = 1.0 if mid == "inflation" else 1.05 + rnd() * 0.09

            for year in (BASE_YEAR, CURRENT_YEAR):
                last_month = CURRENT_MONTH if year == CURRENT_YEAR else 12
                for month in range(1, last_month + 1):
                    year_factor = yoy if year == CURRENT_YEAR else 1.0
                    season = seasonality(mid, month)

                    if mid == "inflation":
                        plan = 7.5 - (year - BASE_YEAR) * 0.6
                        pressure = (1 / profile - 1) * 6
                        fact = (
                            plan
                            + pressure
                            + 1.6 * math.sin(((month - 2) / 12) * math.pi * 2)
                            + (rnd() - 0.45) * 1.5
                        )
                        fact = max(2.4, fact)
                    else:
                        plan = (base_scale * season * year_factor) / 12
                        plan = round(plan * 10) / 10
                        noise = 0.94 + rnd() * 0.13
                        fact = plan * profile * noise

                    plan = round(plan * 10) / 10
                    fact = round(fact * 10) / 10
                    ratio = fact / plan if plan else 1.0
                    status = status_from_ratio(ratio, lower_is_better)

                    note = None
                    pool = NOTES.get(mid)
                    if pool and status in ("critical", "at_risk") and rnd() > 0.55:
                        note = pool[int(rnd() * len(pool))]

                    db.add(
                        Indicator(
                            district_id=did,
                            module_id=mid,
                            year=year,
                            month=month,
                            quarter=(month - 1) // 3 + 1,
                            plan=plan,
                            fact=fact,
                            unit=unit,
                            status=status,
                            note=note,
                        )
                    )
                    created += 1

    db.commit()
    return created


def seed_tasks(db) -> int:
    if db.scalar(select(EconomicTask).limit(1)) is not None:
        return 0

    rnd = mulberry32(20260727)
    created = 0
    for di, district in enumerate(DISTRICTS):
        count = 2 + int(rnd() * 3)
        for i in range(count):
            title, mid = TASK_TEMPLATES[int(rnd() * len(TASK_TEMPLATES))]
            progress = int(rnd() * 100)
            status = (
                "completed"
                if progress >= 100
                else "in_progress"
                if progress >= 60
                else "at_risk"
                if progress >= 30
                else "critical"
            )
            month = 1 + int(rnd() * 12)
            day = 1 + int(rnd() * 27)
            db.add(
                EconomicTask(
                    title=title,
                    description=f"{district[1]} tumani bo'yicha topshiriq.",
                    district_id=district[0],
                    module_id=mid,
                    status=status,
                    progress=progress,
                    deadline=date(CURRENT_YEAR, month, min(day, 28)),
                    assignee=ASSIGNEES[(di + i) % len(ASSIGNEES)],
                )
            )
            created += 1
    db.commit()
    return created


def seed_users(db) -> int:
    demo = [
        ("admin", "Bosh administrator", "admin123", "admin"),
        ("rahbar", "Rahbariyat vakili", "rahbar123", "viewer"),
    ]
    created = 0
    for username, full_name, password, role in demo:
        if db.scalar(select(User).where(User.username == username)):
            continue
        db.add(
            User(
                username=username,
                full_name=full_name,
                password_hash=hash_password(password),
                role=role,
            )
        )
        created += 1
    db.commit()
    return created


def main() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_reference(db)
        indicators = seed_indicators(db)
        tasks = seed_tasks(db)
        users = seed_users(db)

    print("Baza tayyor.")
    print(f"  hududlar:     {len(DISTRICTS)}")
    print(f"  sohalar:      {len(MODULES)}")
    print(f"  ko'rsatkich:  {indicators} ta yangi yozuv")
    print(f"  topshiriqlar: {tasks} ta")
    print(f"  foydalanuvchi:{users} ta")
    if users:
        print("\n  admin / admin123   (administrator)")
        print("  rahbar / rahbar123 (ko'ruvchi)")


if __name__ == "__main__":
    main()
