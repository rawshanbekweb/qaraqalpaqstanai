"""
Excel yozuvlarini PostgreSQL'ga yuklaydi.

Ishga tushirish:
    python -m app.ingest.loader "C:/.../model/data"

Qayta ishga tushirish xavfsiz: ko'rsatkichlar `slug` bo'yicha, o'lchovlar
esa (ko'rsatkich, hudud, yil, davr) bo'yicha yagona — takror yozilmaydi.
"""

from __future__ import annotations

import hashlib
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.ingest.excel import Record, parse_tree
from app.models import District, StatCategory, StatIndicator, StatObservation

#: Manba papkasi -> (id, qoraqalpoqcha nom, o'zbekcha nom, rang, tartib)
CATEGORIES: dict[str, tuple[str, str, str, str, int]] = {
    "01_Makroekonomika": ("makro", "Makroekonomika", "Makroiqtisodiyot", "#38bdf8", 1),
    "02_Sanaat": ("sanaat", "Sanaat", "Sanoat", "#0ea5e9", 2),
    "03_Aw_lXojal___": ("awil_xojaligi", "Awıl xojalıǵı", "Qishloq xo'jaligi", "#a3e635", 3),
    "04_Investitsiya": ("investitsiya", "Investitsiya", "Investitsiyalar", "#818cf8", 4),
    "05_S_rtq_Sawda": ("sirtqi_sawda", "Sırtqı sawda", "Tashqi savdo", "#22d3ee", 5),
    "06_X_zmetler": ("xizmetler", "Xızmetler", "Xizmatlar", "#34d399", 6),
    "07_Transport": ("transport", "Transport", "Transport", "#fbbf24", 7),
    "08_MiynetBazar": ("miynet", "Miynet bazarı", "Mehnat bozori", "#fb7185", 8),
    "09_Xaliq": ("xaliq", "Xalıq", "Aholi", "#a78bfa", 9),
    "09_Xal_q": ("xaliq", "Xalıq", "Aholi", "#a78bfa", 9),
    "10_Bilimlendiriw": ("bilimlendiriw", "Bilimlendiriw", "Ta'lim", "#e879f9", 10),
    "11_Densawl_q": ("densawliq", "Densawlıq saqlaw", "Sog'liqni saqlash", "#f43f5e", 11),
    "12_Sawda_Bahalar": ("sawda", "Sawda hám bahalar", "Savdo va narxlar", "#f97316", 12),
    "13_Isbilermenlik": ("isbilermenlik", "Isbilermenlik", "Tadbirkorlik", "#14b8a6", 13),
    "14_Madeniyat": ("madeniyat", "Mádeniyat", "Madaniyat", "#c084fc", 14),
    "15_Finanslar": ("finanslar", "Finanslar", "Moliya", "#64748b", 15),
}

#: Butunlay takroriy papka — 100% tekshirildi, hamma yozuvi boshqa fayllarda bor
SKIP_DIRS = {"00_Duplikatlar"}

#: Xarita va asosiy panel uchun tayanch ko'rsatkichlar.
#: Kalit — ko'rsatkich nomida qidiriladigan parcha (kichik harfda).
CORE_MODULES: list[tuple[str, str]] = [
    ("rayonlar boyınsha sanaat ónimi kólemi", "sanaat"),
    ("aymaqlar boyınsha awıl xojalıǵı ónimleri", "awil_xojaligi"),
    ("aymaqlar boyınsha awıl xojalıģı ónimleri", "awil_xojaligi"),
    ("tiykarǵı kapitalǵa ózlestirilgen investitsiyalar", "investitsiya"),
    ("тiykarģı kapitalǵa ózlestirilgen investitsiyalar", "investitsiya"),
    ("qurılıs jumısları", "qurilis"),
    ("aymaqlar boyınsha kórsetilgen xızmetler kólemi", "xizmetler"),
    ("avtomobil transportinda tasılǵan júkler kólemi", "transport"),
    ("usaqlap satıw tovar aylanısınıń kólemi", "sawda"),
]

#: Pasayishi yaxshi bo'lgan ko'rsatkichlar
LOWER_IS_BETTER = ("inflyatsiya", "jumıssız", "jumissiz", "kóship ketken")


def slugify(text: str) -> str:
    """
    O'qiladigan, lekin YAGONA kalit.

    Oxiridagi hash MAJBURIY: ko'p ko'rsatkich nomlari uzun umumiy sarlavha
    bilan boshlanib, ularni ajratib turadigan qism (iqtisodiy faoliyat turi)
    oxirida keladi. Faqat qirqilgan nomdan slug yasalsa, bir faylning
    o'nlab turli qatori bitta kalitga tushib, ma'lumot yo'qoladi.
    """
    s = unicodedata.normalize("NFKD", text.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.translate(str.maketrans({"ı": "i", "ǵ": "g", "ğ": "g", "ń": "n", "ó": "o", "ú": "u"}))
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    digest = hashlib.blake2s(text.strip().lower().encode("utf-8"), digest_size=4).hexdigest()
    return f"{s[:100] or 'korsetkish'}-{digest}"


def record_slug(r: Record) -> str:
    """
    Yozuv uchun ko'rsatkich kaliti.

    RAYON kesimidagi fayllarda bitta varaq = bitta ko'rsatkich, qatorlar
    esa hududlar — nomning o'zi yetarli.

    RESPUBLIKA kesimidagi fayllarda esa bir varaqda o'nlab ko'rsatkich
    bo'lib, ularning nomlari (ierarxik tarkibiy qismlar) takrorlanadi.
    109 ta faylning har bir tuzilish variantini nom orqali ajratib bo'lmadi,
    shuning uchun kalitga manba varaq va qator raqami qo'shiladi: nom
    o'qiladigan bo'lib qoladi, ma'lumot esa yo'qolmaydi.
    """
    if r.district_id:
        # Blok raqami: bir varaqdagi ustma-ust jadvallar sarlavhasiz
        # bo'lishi mumkin, u holda nomning o'zi ularni ajratmaydi
        suffix = f"|{r.source}|b{r.block}" if r.block else ""
        return slugify(f"{r.indicator}{suffix}")
    return slugify(f"{r.indicator}|{r.source}|{r.row}")


def core_module(name: str) -> str | None:
    low = name.lower()
    for needle, module in CORE_MODULES:
        if needle in low:
            return module
    return None


def load_records(
    records: list[Record], db: Session, *, replace_all: bool = True
) -> dict[str, int]:
    """
    Yozuvlar oqimini bazaga yozadi.

    `replace_all=True` — to'liq qayta yuklash (butun `data/` papkasi):
    barcha o'lchovlar tozalanadi. Admin bitta fayl yuklaganda esa FALSE
    bo'ladi va faqat SHU fayl tegib o'tgan ko'rsatkichlarning o'lchovlari
    almashtiriladi — aks holda bitta fayl yuklash butun bazani o'chirib
    yuborardi.
    """
    if not records:
        return {"kategoriya": 0, "korsetkish": 0, "olshov": 0, "otkazib_yuborilgan": 0}

    known_districts = {d.id for d in db.scalars(select(District))}
    if not known_districts:
        raise SystemExit("districts jadvali bo'sh — avval `python -m app.seed` ni ishga tushiring")

    # ── Kategoriyalar ──
    for src_dir in {r.category for r in records}:
        cid, kaa, uz, color, sort = CATEGORIES[src_dir]
        if db.get(StatCategory, cid) is None:
            db.add(StatCategory(
                id=cid, source_dir=src_dir, name_kaa=kaa, name_uz=uz, color=color, sort=sort
            ))
    db.flush()

    # ── Ko'rsatkichlar ──
    grouped: dict[str, list[Record]] = defaultdict(list)
    for r in records:
        grouped[record_slug(r)].append(r)

    indicator_ids: dict[str, int] = {}
    for slug, rows in grouped.items():
        first = rows[0]
        ind = db.scalar(select(StatIndicator).where(StatIndicator.slug == slug))
        if ind is None:
            ind = StatIndicator(slug=slug, category_id=CATEGORIES[first.category][0])
            db.add(ind)
        ind.name_kaa = first.indicator[:300]
        ind.unit = next((r.unit for r in rows if r.unit), "")[:80]
        ind.has_districts = any(r.district_id for r in rows)
        ind.module = core_module(first.indicator)
        ind.lower_is_better = any(k in first.indicator.lower() for k in LOWER_IS_BETTER)
        ind.source = first.source[:200]
        db.flush()
        indicator_ids[slug] = ind.id

    # ── O'lchovlar: eski qiymatlarni tozalab, yangidan yozamiz ──
    if replace_all:
        db.execute(delete(StatObservation))
    else:
        db.execute(
            delete(StatObservation).where(
                StatObservation.indicator_id.in_(list(indicator_ids.values()))
            )
        )
    db.flush()

    seen: set[tuple] = set()
    added = skipped = 0
    for r in records:
        did = r.district_id
        if did and did not in known_districts:
            skipped += 1
            continue
        key = (indicator_ids[record_slug(r)], did, r.year, r.period, r.period_no)
        if key in seen:  # bir xil o'lchov ikki faylda uchrashi mumkin
            skipped += 1
            continue
        seen.add(key)
        db.add(StatObservation(
            indicator_id=key[0], district_id=did, year=r.year,
            period=r.period, period_no=r.period_no, value=r.value,
        ))
        added += 1

    db.commit()
    return {
        "kategoriya": len({r.category for r in records}),
        "korsetkish": len(indicator_ids),
        "olshov": added,
        "otkazib_yuborilgan": skipped,
    }


def keep_known(records) -> list[Record]:
    """Ma'lum kategoriyaga tegishli va takrorlanmagan yozuvlar."""
    return [
        r for r in records
        if r.category not in SKIP_DIRS and r.category in CATEGORIES
    ]


def load(data_root: Path, db: Session) -> dict[str, int]:
    records = keep_known(parse_tree(data_root))
    if not records:
        raise SystemExit(f"'{data_root}' ichidan yozuv topilmadi")
    return load_records(records, db, replace_all=True)


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "../model/data")
    if not root.exists():
        raise SystemExit(f"papka topilmadi: {root}")

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        stats = load(root, db)

    print("Yuklandi.")
    for k, v in stats.items():
        print(f"  {k:22} {v:,}" if isinstance(v, int) else f"  {k:22} {v}")


if __name__ == "__main__":
    main()
