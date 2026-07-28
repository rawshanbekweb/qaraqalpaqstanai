"""
Statistika Excel fayllarini bir xil yozuvlar oqimiga aylantiradi.

Fayllar ikki ko'rinishda uchraydi:

  1. RAYON kesimi — qatorlar hudud nomlari, ustunlar davrlar.
     Eng ko'p uchraydigan va xarita uchun eng qimmatlisi.

  2. KO'RSATKICH kesimi — qatorlar ko'rsatkich nomlari (respublika
     bo'yicha), ustunlar davrlar. Ko'pincha o'lchov birligi ustuni bor.

Davr sarlavhalari bir necha shaklda: "2010 j.", "2014", "2015.0" (Excel
sonni float qilib beradi), "2025 jıl yanvar-dekabr" (to'liq yil) va
"2026 jıl yanvar-iyun" (yil boshidan yig'indi — hali tugamagan yil).
"""

from __future__ import annotations

import datetime as dt
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

import pandas as pd

from app.ingest.districts_map import REPUBLIC, resolve

PeriodKind = Literal["year", "ytd", "quarter"]

#: Ma'lumot yo'qligini bildiruvchi belgilar
_MISSING = {"-", "–", "—", "х", "x", "", "...", "nan", "*", "n/a"}

_MONTHS = {
    "yanvar": 1, "fevral": 2, "mart": 3, "aprel": 4, "may": 5, "iyun": 6,
    "iyul": 7, "avgust": 8, "sentyabr": 9, "oktyabr": 10, "noyabr": 11, "dekabr": 12,
}

_YEAR_RE = re.compile(r"(19|20)\d{2}")
_QUARTER_RE = re.compile(r"([1-4])\s*-?\s*sherek")

# Statistika 2005-yildan boshlanadi, prognozlar 2031-yilgacha boradi.
# Chegara MAJBURIY: usiz "20.55" kabi foiz qiymatlari 2055-yil deb
# o'qiladi va sarlavha qatori noto'g'ri aniqlangan fayllarda ma'lumot
# buziladi (109 fayldan bittasida aynan shunday bo'lgan).
_YEAR_MIN, _YEAR_MAX = 2000, 2032


@dataclass(frozen=True, slots=True)
class Record:
    """Bitta o'lchov: hudud × ko'rsatkich × davr."""

    category: str
    indicator: str
    unit: str
    #: hudud ID'si, REPUBLIC, yoki None (respublika kesimidagi fayllarda)
    district_id: str | None
    year: int
    period: PeriodKind
    #: ytd uchun — nechanchi oygacha; quarter uchun — chorak raqami
    period_no: int | None
    value: float
    source: str
    #: Varaqdagi qator raqami — bir xil nomli qatorlarni ajratish uchun
    row: int = -1
    #: Varaq ichidagi ustma-ust jadval raqami (0 = birinchisi)
    block: int = 0


def _clean(v) -> str:
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()


def parse_period(raw) -> tuple[int, PeriodKind, int | None] | None:
    """Sarlavha katagidan (yil, davr turi, raqam) ni ajratadi."""
    if isinstance(raw, (dt.datetime, dt.date, pd.Timestamp)):
        return int(raw.year), "year", None

    text = _clean(raw)
    if not text:
        return None

    # "2015.0" — Excel yilni float qilib beradi
    try:
        f = float(text)
        if f == int(f) and _YEAR_MIN <= f <= _YEAR_MAX:
            return int(f), "year", None
        # Butun bo'lmagan son — bu o'lchov qiymati, sarlavha emas
        return None
    except ValueError:
        pass

    m = _YEAR_RE.search(text)
    if not m:
        return None
    year = int(m.group())
    if not _YEAR_MIN <= year <= _YEAR_MAX:
        return None
    low = text.lower()

    if q := _QUARTER_RE.search(low):
        return year, "quarter", int(q.group(1))

    # "yanvar-dekabr" = to'liq yil; "yanvar-iyun" = yil boshidan yig'indi
    months = [n for name, n in _MONTHS.items() if name in low]
    if months:
        last = max(months)
        return (year, "year", None) if last == 12 else (year, "ytd", last)

    return year, "year", None


def _header_row(df: pd.DataFrame, limit: int = 10) -> int | None:
    """Davr sarlavhalari joylashgan qatorni topadi."""
    best, best_hits = None, 0
    for i in range(min(limit, len(df))):
        hits = sum(1 for v in df.iloc[i] if parse_period(v))
        if hits > best_hits:
            best, best_hits = i, hits
    return best if best_hits >= 3 else None


def _preamble(df: pd.DataFrame, header_row: int) -> list[str]:
    """Sarlavha qatoridan yuqoridagi barcha matnlar."""
    out = []
    for i in range(header_row):
        for v in df.iloc[i]:
            if (t := _clean(v)) and len(t) > 3:
                out.append(t.replace("\n", " ").strip())
    return out


def _title(preamble: list[str]) -> str:
    return max(preamble, key=len) if preamble else ""


_UNIT_RE = re.compile(r"\(([^)]{2,60})\)")
#: O'lchov birligini bildiruvchi kalit so'zlar (qoraqalpoq/o'zbek/rus)
_UNIT_HINTS = (
    "swm", "som", "so'm", "sum", "mln", "mlrd", "mıń", "min ", "%", "protsent",
    "adam", "birlik", "tonna", "dana", "km", "gektar", "ga)", "dollar", "kishi",
)


def _looks_like_unit(text: str) -> bool:
    """Qisqa va birlik kalit so'zi bor matngina o'lchov birligi hisoblanadi."""
    t = text.strip()
    if not t or len(t) > 60:
        return False
    return any(k in t.lower() for k in _UNIT_HINTS)


def _unit(preamble: list[str], row_label: str = "") -> str:
    """
    O'lchov birligi ko'pincha sarlavhaning OSTIDAGI qatorda, qavs ichida
    beriladi: "(ámeldegi baxalarda, mlrd. swm)". Shuning uchun sarlavha
    ustidagi barcha matnlar ko'rib chiqiladi, faqat eng uzuni emas.
    """
    for src in [row_label, *preamble]:
        for m in _UNIT_RE.finditer(src):
            body = m.group(1).lower()
            if any(k in body for k in _UNIT_HINTS):
                return m.group(1).strip()
    # Qavssiz shakl: "mlrd. swm" to'g'ridan-to'g'ri katakda turishi mumkin
    for src in preamble:
        low = src.lower()
        if len(src) < 40 and any(k in low for k in ("mlrd", "mln", "mıń")):
            return src.strip()
    return ""


def _numeric(v) -> float | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    t = str(v).strip().replace(" ", "").replace(" ", "").replace(",", ".")
    if t.lower() in _MISSING:
        return None
    try:
        return float(t)
    except ValueError:
        return None


#: "shundan:" — keyingi qatorlar yuqoridagi ko'rsatkichning tarkibiy qismi
_BREAKDOWN_MARKERS = {"sonnan", "sonnan:", "sonnan :", "onnan", "shundan", "shundan:", "in the number"}


def _parents(df: pd.DataFrame, hr: int, value_cols: list[int]) -> dict[int, str]:
    """
    Ierarxik qatorlar uchun ota-nomlarni aniqlaydi.

    Fayllarda tarkibiy qismlar "sonnan:" markeridan keyin keladi va ularning
    nomlari (masalan "dıyqanshılıq") bir varaqda bir necha marta — har xil
    ota ko'rsatkich ostida — takrorlanadi. Otasiz ular bir xil nom olib,
    faqat bittasi saqlanib qolardi.

    Qaytaradi: {qator raqami -> ota ko'rsatkich nomi}
    """
    has_value = {
        i: any(not pd.isna(df.iat[i, c]) for c in value_cols)
        for i in range(hr + 1, len(df))
    }
    markers = [
        i for i in range(hr + 1, len(df))
        if _clean(df.iat[i, 0]).lower().strip() in _BREAKDOWN_MARKERS
    ]
    if not markers:
        return {}

    # Har bir marker uchun otasi — undan oldingi eng yaqin ma'lumotli qator
    parent_of: dict[int, int] = {}
    for m in markers:
        for i in range(m - 1, hr, -1):
            if has_value.get(i) and _clean(df.iat[i, 0]):
                parent_of[m] = i
                break

    out: dict[int, str] = {}
    for idx, m in enumerate(markers):
        p = parent_of.get(m)
        if p is None:
            continue
        # Bolalar keyingi markerning otasigacha davom etadi
        nxt = markers[idx + 1] if idx + 1 < len(markers) else len(df)
        end = parent_of.get(nxt, nxt)
        for row in range(m + 1, end):
            out[row] = _clean(df.iat[p, 0])
    return out


def parse_sheet(df: pd.DataFrame, *, category: str, source: str) -> Iterator[Record]:
    """Bitta varaqni yozuvlarga aylantiradi."""
    hr = _header_row(df)
    if hr is None:
        return

    periods: dict[int, tuple[int, PeriodKind, int | None]] = {}
    for col in range(df.shape[1]):
        if p := parse_period(df.iat[hr, col]):
            periods[col] = p
    if not periods:
        return

    preamble = _preamble(df, hr)
    title = _title(preamble)

    # Davr ustunlaridan oldingi ustun ko'pincha o'lchov birligini saqlaydi
    # ("Ólshem birligi": mlrd. swm / ósiw páti, % da). Aynan shu ustun bir
    # varaq ichidagi ustma-ust jadvallarni ajratib beradi — usiz "hajm" va
    # "o'sish sur'ati" qatorlari bir xil nom olib, biri yo'qoladi.
    unit_col = min(periods) - 1 if min(periods) >= 2 else None

    parent_of_row = _parents(df, hr, list(periods))

    #: Bo'sh nomli qator oldingi ko'rsatkichning davomi bo'ladi
    last_label = ""

    # Bir varaqda hududlar ro'yxati bir necha marta takrorlanishi mumkin —
    # har biri alohida jadval (masalan moliyalashtirish manbalari bo'yicha).
    # Hudud qayta uchraganda yangi blok boshlanadi; bloklarni ajratmasak,
    # ularning qiymatlari bir xil kalitga tushib, faqat birinchisi qoladi.
    block_seen: set[str] = set()
    block_caption = ""
    pending_caption = ""
    block_no = 0

    for row in range(hr + 1, len(df)):
        raw_label = _clean(df.iat[row, 0])
        row_unit = _clean(df.iat[row, unit_col]) if unit_col is not None else ""

        if raw_label.lower().strip() in _BREAKDOWN_MARKERS:
            continue
        if raw_label:
            last_label = raw_label
        label = raw_label or last_label
        if not label:
            continue

        # Davr ustunidan oldingi ustun HAR DOIM birlik emas: tashqi savdo
        # fayllarida u tovar nomini saqlaydi. Nomga qo'shiladi, lekin
        # birlik sifatida faqat haqiqatan birlikka o'xshasa qabul qilinadi.
        extra = row_unit if row_unit and row_unit != label else ""
        if not _looks_like_unit(row_unit):
            row_unit = ""

        district = resolve(label)
        # Hudud nomi topilmasa — bu ko'rsatkich kesimidagi qator
        if district:
            if district in block_seen:
                block_seen = set()
                block_no += 1
                block_caption = pending_caption
            block_seen.add(district)
            indicator = f"{title} — {block_caption}" if block_caption else title
        else:
            pending_caption = label
            # Qo'shimcha ustun nomga qo'shiladi: bitta ko'rsatkichning hajmi
            # va o'sish sur'ati alohida yozuv bo'lib qolishi kerak
            parts = [p for p in (title, parent_of_row.get(row, ""), label, extra) if p]
            indicator = " — ".join(parts)

        unit = row_unit or _unit(preamble, label)

        for col, (year, kind, no) in periods.items():
            val = _numeric(df.iat[row, col])
            if val is None:
                continue
            yield Record(
                category=category,
                indicator=indicator.strip(" —")[:300],
                unit=unit,
                district_id=None if district == REPUBLIC else district,
                year=year,
                period=kind,
                period_no=no,
                value=val,
                source=source,
                row=row,
                block=block_no,
            )


def _parse_excel(xl: pd.ExcelFile, *, category: str, filename: str) -> Iterator[Record]:
    for sheet in xl.sheet_names:
        try:
            df = xl.parse(sheet, header=None)
        except Exception:  # noqa: BLE001
            continue
        yield from parse_sheet(df, category=category, source=f"{filename}#{sheet}")


def parse_workbook(path: Path, *, category: str | None = None) -> Iterator[Record]:
    """Fayldagi barcha varaqlarni o'qiydi."""
    try:
        xl = pd.ExcelFile(path)
    except Exception:  # noqa: BLE001 — buzuq fayl butun yuklashni to'xtatmasin
        return
    yield from _parse_excel(xl, category=category or path.parent.name, filename=path.name)


def parse_bytes(data: bytes, *, category: str, filename: str) -> Iterator[Record]:
    """
    Yuklangan faylni diskka yozmasdan o'qiydi.

    Kategoriya papka nomidan kelmaydi, shuning uchun ochiq beriladi —
    admin uni yuklash formasida tanlaydi.
    """
    yield from _parse_excel(pd.ExcelFile(io.BytesIO(data)), category=category, filename=filename)


def parse_tree(root: Path) -> Iterator[Record]:
    """data/ ostidagi hamma .xlsx fayl."""
    for f in sorted(root.rglob("*.xlsx")):
        yield from parse_workbook(f)
