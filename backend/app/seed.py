"""
Ma'lumotnomalarni bazaga sinxronlash.

Statistika (ko'rsatkichlar va o'lchovlar) bu yerda GENERATSIYA
QILINMAYDI — u Excel'dan `app.ingest.loader` orqali keladi. Bu skript
faqat ular tayanadigan ma'lumotnomalarni to'ldiradi: hududlar, tayanch
sohalar va foydalanuvchilar.

Ishga tushirish:
    python -m app.seed
"""

from __future__ import annotations

import sys
from datetime import date

from sqlalchemy import select, text

from app.database import Base, SessionLocal, engine
from app.models import District, EconomicTask, Module, User
from app.security import hash_password
from app.services.stats import MODULE_META

CURRENT_YEAR = 2026

DISTRICTS: list[tuple[str, str, str, str, int, float]] = [
    ("amudaryo", "Ámiwdárya", "Амударья", "Mańǵıt", 2300, 200.3),
    ("beruniy", "Beruniy", "Беруни", "Beruniy", 4000, 205.1),
    ("bozatov", "Bozataw", "Бозатау", "Bozataw", 3000, 20.4),
    ("chimboy", "Shımbay", "Чимбай", "Shımbay", 3000, 120.9),
    ("ellikqala", "Ellikqala", "Элликкала", "Bostan", 4900, 155.8),
    ("karaozak", "Qaraózek", "Караузяк", "Qaraózek", 5800, 60.3),
    ("kegeyli", "Kegeyli", "Кегейли", "Kegeyli", 2200, 90.5),
    ("moynoq", "Moynaq", "Муйнак", "Moynaq", 37600, 30.2),
    ("nukus-shahri", "Nókis qalası", "город Нукус", "Nókis", 220, 335.8),
    ("nukus-tumani", "Nókis rayonı", "Нукусский район", "Aqmańǵıt", 2000, 55.7),
    ("qanlikol", "Qanlıkól", "Канлыкуль", "Qanlıkól", 900, 45.6),
    ("qongirot", "Qońırat", "Кунград", "Qońırat", 78700, 130.4),
    ("shumanay", "Shomanay", "Шуманай", "Shomanay", 800, 55.1),
    ("taxiatosh", "Taqıyatas", "Тахиаташ", "Taqıyatas", 200, 45.9),
    ("taxtakopir", "Taxtakópir", "Тахтакупыр", "Taxtakópir", 20100, 40.7),
    ("tortkol", "Tórtkúl", "Турткуль", "Tórtkúl", 7900, 220.6),
    ("xojayli", "Xojeli", "Ходжейли", "Xojeli", 1300, 165.2),
]

#: Topshiriq namunalari — (sarlavha, tayanch soha kodi)
TASK_TEMPLATES: list[tuple[str, str]] = [
    ("Tamshılatıp suwǵarıw maydanların 20% ke keńeytiw", "awil_xojaligi"),
    ("Sorlanǵan jerlerdi melioraciyalaw baǵdarlaması", "awil_xojaligi"),
    ("Kishi sanaat zonasın keńeytiw", "sanaat"),
    ("Islep shıǵarıw quwatların modernizaciyalaw", "sanaat"),
    ("Shet el investorları menen 3 shártnama imzalaw", "investitsiya"),
    ("Social turaq-jay qurılısın juwmaqlaw", "qurilis"),
    ("Turizm infradúzilmesin rawajlandırıw", "xizmetler"),
    ("Logistika orayın iske túsiriw", "transport"),
    ("Awıllarda sawda noqatların kóbeytiw", "sawda"),
]

ASSIGNEES = [
    "R. Sultanov",
    "G. Qalandarova",
    "A. Yusupov",
    "M. Seytniyazova",
    "B. Reymov",
    "N. Allambergenova",
    "J. Qurbanbaev",
]


def seed_reference(db) -> None:
    """
    Ma'lumotnomalarni bazaga sinxronlaydi.

    Hududlar MAVJUD bo'lsa ham yangilanadi: nomlar o'zgarganda (masalan
    o'zbekchadan qoraqalpoqchaga o'tishda) shunchaki "bor ekan" deb
    o'tib ketilsa, baza eski nomlar bilan qolib ketardi. O'lchovlar
    `district_id` ga bog'langani uchun bu xavfsiz.
    """
    for row in DISTRICTS:
        did, name, name_ru, center, area, pop = row
        existing = db.get(District, did)
        if existing is None:
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
        else:
            existing.name = name
            existing.name_ru = name_ru
            existing.center = center
            existing.area_km2 = area
            existing.population = pop

    # Sohalar ro'yxati bitta joyda — `services/stats.py` dagi MODULE_META.
    # `modules` jadvali topshiriqlarni turkumlash uchun kerak (ular unga
    # tashqi kalit bilan bog'langan), shuning uchun o'sha manbadan to'ldiriladi.
    for module, (name, short, color, _sort) in MODULE_META.items():
        existing = db.get(Module, module)
        if existing is None:
            db.add(Module(id=module, name=name, short=short, color=color))
        else:
            existing.name = name
            existing.short = short
            existing.color = color
    db.commit()


def seed_tasks(db) -> int:
    """Namoyish uchun bir nechta topshiriq — baza bo'sh bo'lsa."""
    if db.scalar(select(EconomicTask).limit(1)) is not None:
        return 0

    created = 0
    for i, (title, module) in enumerate(TASK_TEMPLATES):
        district = DISTRICTS[(i * 5) % len(DISTRICTS)]
        progress = (i * 17 + 10) % 100
        db.add(
            EconomicTask(
                title=title,
                description=f"{district[1]} boyınsha tapsırma.",
                district_id=district[0],
                module_id=module,
                status=(
                    "completed"
                    if progress >= 100
                    else "in_progress"
                    if progress >= 60
                    else "at_risk"
                    if progress >= 30
                    else "critical"
                ),
                progress=progress,
                deadline=date(CURRENT_YEAR, 1 + (i % 12), 28),
                assignee=ASSIGNEES[i % len(ASSIGNEES)],
            )
        )
        created += 1
    db.commit()
    return created


def seed_users(db) -> int:
    demo = [
        ("admin", "Bas administrator", "admin123", "admin"),
        ("rahbar", "Basshılıq wákili", "rahbar123", "viewer"),
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


#: Eski demo modeli (reja↔amalda) sohalari — endi ishlatilmaydi
LEGACY_MODULES = [
    "inflation", "industry", "agriculture", "investment",
    "export", "employment", "construction", "services",
]


def drop_legacy(db) -> tuple[int, int]:
    """
    Eski demo modelining qoldiqlarini o'chiradi.

    Faqat `--reset-demo` bilan chaqiriladi: topshiriqlar generatordan
    chiqqan bo'lsa ham foydalanuvchi kiritgan bo'lishi mumkin, shuning
    uchun jimgina o'chirilmaydi.
    """
    tasks = db.scalars(
        select(EconomicTask).where(EconomicTask.module_id.in_(LEGACY_MODULES))
    ).all()
    for t in tasks:
        db.delete(t)
    db.flush()

    # `indicators` jadvali eski modeldan qolgan va endi hech qayerda
    # ishlatilmaydi. U sohalarga tashqi kalit bilan bog'langani uchun
    # avval o'zi olib tashlanmasa, sohalarni o'chirib bo'lmaydi.
    db.execute(text("DROP TABLE IF EXISTS indicators"))
    db.flush()

    modules = db.scalars(select(Module).where(Module.id.in_(LEGACY_MODULES))).all()
    for m in modules:
        db.delete(m)
    db.commit()
    return len(tasks), len(modules)


def main() -> None:
    reset = "--reset-demo" in sys.argv

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_reference(db)
        if reset:
            dropped_tasks, dropped_modules = drop_legacy(db)
            print(
                f"Eski demo modeli tozalandi: {dropped_tasks} topshiriq, "
                f"{dropped_modules} soha o'chirildi.\n"
            )
        tasks = seed_tasks(db)
        users = seed_users(db)

    print("Baza tayyor.")
    print(f"  hududlar:     {len(DISTRICTS)}")
    print(f"  sohalar:      {len(MODULE_META)}")
    print(f"  topshiriqlar: {tasks} ta yangi")
    print(f"  foydalanuvchi:{users} ta yangi")
    if users:
        print("\n  admin / admin123   (administrator)")
        print("  rahbar / rahbar123 (ko'ruvchi)")
    print("\nStatistikani yuklash uchun: python -m app.ingest.loader ../model/data")


if __name__ == "__main__":
    main()
