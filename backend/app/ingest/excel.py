"""
Statistika Excel fayllarini bir xil yozuvlar oqimiga aylantiradi.

Fayllar to'rt ko'rinishda uchraydi va to'rttasi ham o'qiladi:

  1. RAYON kesimi — qatorlar hudud nomlari, ustunlar davrlar.
     Eng ko'p uchraydigan va xarita uchun eng qimmatlisi.

  2. KO'RSATKICH kesimi — qatorlar ko'rsatkich nomlari (respublika
     bo'yicha), ustunlar davrlar. Ko'pincha o'lchov birligi ustuni bor.

  3. DAVRLAR QATORDA — birinchi ustunda "2010 j." kabi yillar, ustunlar
     esa ko'rsatkich yoki tarkib (`parse_vertical`). Yil "blok sarlavhasi"
     bo'lib, undan keyingi qatorlar hududlar bo'lishi ham mumkin.

  4. HUDUDLAR USTUNDA — jadval yon tomonga o'girilgan, davr sahifa
     nomida (`parse_district_columns`).

Davr sarlavhalari bir necha shaklda: "2010 j.", "2014", "2015.0" (Excel
sonni float qilib beradi), "2025 jıl yanvar-dekabr" (to'liq yil),
"2026 jıl yanvar-iyun" (yil boshidan yig'indi — hali tugamagan yil),
"2019M1" (oy), "2018Q1" (chorak) va yilsiz "Yanvar-fevral" (yil
yuqoridagi qatorda turadi).
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

PeriodKind = Literal["year", "ytd", "quarter", "month"]

#: Ma'lumot yo'qligini bildiruvchi belgilar
_MISSING = {"-", "–", "—", "х", "x", "", "...", "nan", "*", "n/a"}

_MONTHS = {
    "yanvar": 1, "fevral": 2, "mart": 3, "aprel": 4, "may": 5, "iyun": 6,
    "iyul": 7, "avgust": 8, "sentyabr": 9, "oktyabr": 10, "noyabr": 11, "dekabr": 12,
}

_YEAR_RE = re.compile(r"(19|20)\d{2}")
_QUARTER_RE = re.compile(r"([1-4])\s*-?\s*sherek")

#: "2019M1" (oy), "2018Q1" (chorak) — ixcham davr kodlari.
#: Bu shakl TEKSHIRILISHI SHART: yilning o'zi ham shu katakda turgani
#: uchun oddiy yil qidiruvi bir yilning 12 oyini (yoki 4 chorakini)
#: bitta yillik qiymatga aylantirib, qolganini yo'qotardi.
_CODE_RE = re.compile(
    r"^\s*(?P<year>(19|20)\d{2})\s*(?P<kind>[mм]|[qк])\s*(?P<no>\d{1,2})\s*$", re.I
)

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

    if m := _CODE_RE.match(text):
        year, no = int(m.group("year")), int(m.group("no"))
        month_like = m.group("kind").lower() in ("m", "м")
        limit = 12 if month_like else 4
        if _YEAR_MIN <= year <= _YEAR_MAX and 1 <= no <= limit:
            return year, ("month" if month_like else "quarter"), no

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


#: "Yanvar", "Yanvar-fevral", "Yanvar - iyun" — yilsiz oy oralig'i.
#: Bunday sarlavhalarda yil YUQORIDAGI qatorda alohida katakda turadi.
_SPAN_RE = re.compile(
    r"^\s*(yanvar|yanvar\s*-\s*(?P<to>[a-zıáǵńóú]+))\s*[¹²³⁴*]*\s*$", re.IGNORECASE
)


def parse_month_span(raw) -> tuple[PeriodKind, int | None] | None:
    """
    Yilsiz oy oralig'ini o'qiydi: "Yanvar" → 1-oygacha, "Yanvar-dekabr"
    → to'liq yil. Yilni chaqiruvchi tomon qo'shadi.
    """
    text = _clean(raw)
    if not text or _YEAR_RE.search(text):
        return None
    m = _SPAN_RE.match(text.replace("\n", " "))
    if not m:
        return None
    to = (m.group("to") or "yanvar").lower()
    month = _MONTHS.get(to)
    if month is None:
        return None
    return ("year", None) if month == 12 else ("ytd", month)


def _year_above(df: pd.DataFrame, row: int) -> int | None:
    """Sarlavha qatoridan yuqoridagi eng yaqin "2026-jıl" kabi katak."""
    for i in range(row - 1, -1, -1):
        for v in df.iloc[i]:
            text = _clean(v)
            if not text or len(text) > 20:
                continue
            m = _YEAR_RE.search(text)
            if m and _YEAR_MIN <= int(m.group()) <= _YEAR_MAX:
                return int(m.group())
    return None


def row_periods(df: pd.DataFrame, row: int) -> dict[int, tuple[int, PeriodKind, int | None]]:
    """
    Qatordagi davr ustunlari.

    Ikki shakl qo'llab-quvvatlanadi: katakda yilning o'zi bo'lishi
    ("2015", "2026-jıl yanvar-iyun") yoki faqat oy oralig'i bo'lib,
    yil ustidagi qatorda turishi ("2026-jıl" / "Yanvar | Yanvar-fevral | …").
    Ikkinchisi oylik qatorni beradi — u faqat shu ko'rinishda uchraydi.
    """
    direct = {}
    for col in range(df.shape[1]):
        if p := parse_period(df.iat[row, col]):
            direct[col] = p
    if len(direct) >= 3:
        return direct

    spans = {}
    for col in range(df.shape[1]):
        if s := parse_month_span(df.iat[row, col]):
            spans[col] = s
    if len(spans) >= 3:
        year = _year_above(df, row)
        if year is not None:
            return {c: (year, kind, no) for c, (kind, no) in spans.items()}
    return direct


def _header_row(df: pd.DataFrame, limit: int = 10) -> int | None:
    """Davr sarlavhalari joylashgan qatorni topadi."""
    best, best_hits = None, 0
    for i in range(min(limit, len(df))):
        hits = len(row_periods(df, i))
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


def _parents(
    df: pd.DataFrame, hr: int, value_cols: list[int], label_col: int = 0
) -> dict[int, str]:
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
        if _clean(df.iat[i, label_col]).lower().strip() in _BREAKDOWN_MARKERS
    ]
    if not markers:
        return {}

    # Har bir marker uchun otasi — undan oldingi eng yaqin ma'lumotli qator
    parent_of: dict[int, int] = {}
    for m in markers:
        for i in range(m - 1, hr, -1):
            if has_value.get(i) and _clean(df.iat[i, label_col]):
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
            out[row] = _clean(df.iat[p, label_col])
    return out


def _column_groups(
    df: pd.DataFrame, hr: int, periods: dict[int, tuple]
) -> dict[int, str]:
    """
    Davr ustunlari USTIDAGI guruh sarlavhalari.

    Bir varaqda bir necha jadval yonma-yon turishi mumkin: "Dizimnen
    ótken | Hárekettegi | Háreketsiz | …", har birida bir xil yillar.
    Guruh nomisiz ularning barchasi bitta ko'rsatkichga tushib, faqat
    birinchisi saqlanib qolardi.
    """
    cols = sorted(periods)
    if len(cols) < 4:
        return {}

    for row in range(hr - 1, -1, -1):
        marks = {
            c: text
            for c in range(cols[0], cols[-1] + 1)
            if (text := _clean(df.iat[row, c])) and len(text) < 60
        }
        # Guruh sarlavhasi siyrak bo'ladi: har ustunda emas, jadval boshida
        if not 2 <= len(marks) <= len(cols) // 2:
            continue
        out: dict[int, str] = {}
        current = ""
        for col in range(cols[0], cols[-1] + 1):
            if col in marks:
                current = marks[col]
            if col in periods:
                out[col] = current
        if len(set(out.values())) >= 2:
            return out
    return {}


def _label_col(df: pd.DataFrame, hr: int, first_value_col: int) -> int:
    """
    Qatorlar nomi qaysi ustunda.

    Odatda birinchi ustunda, lekin ba'zi fayllarda chap chekkada bo'sh
    ustun turadi va nomlar ikkinchisiga siljigan. Bunday varaqda 0-ustunni
    o'qish butun sahifani bo'sh qoldiradi.
    """
    for col in range(min(first_value_col, df.shape[1])):
        filled = sum(1 for r in range(hr + 1, len(df)) if _clean(df.iat[r, col]))
        if filled >= 3:
            return col
    return 0


def parse_sheet(df: pd.DataFrame, *, category: str, source: str) -> Iterator[Record]:
    """
    Bitta varaqni yozuvlarga aylantiradi.

    Uch xil tuzilish uchraydi va uchalasi ham sinab ko'riladi:
      1. davrlar USTUNDA (eng keng tarqalgani) — shu funksiya;
      2. davrlar QATORDA, ustunlar ko'rsatkich yoki tarkib — `parse_vertical`;
      3. ustunlar HUDUD, davr esa sarlavhada — `parse_district_columns`.
    """
    produced = False
    for record in _parse_wide(df, category=category, source=source):
        produced = True
        yield record
    if produced:
        return

    for record in parse_vertical(df, category=category, source=source):
        produced = True
        yield record
    if produced:
        return

    yield from parse_district_columns(df, category=category, source=source)


def _parse_wide(df: pd.DataFrame, *, category: str, source: str) -> Iterator[Record]:
    """Davrlar ustun sarlavhalarida turgan varaq."""
    hr = _header_row(df)
    if hr is None:
        return

    periods = row_periods(df, hr)
    if not periods:
        return

    preamble = _preamble(df, hr)
    title = _title(preamble)
    label_col = _label_col(df, hr, min(periods))

    # Davr ustunlaridan oldingi ustun ko'pincha o'lchov birligini saqlaydi
    # ("Ólshem birligi": mlrd. swm / ósiw páti, % da). Aynan shu ustun bir
    # varaq ichidagi ustma-ust jadvallarni ajratib beradi — usiz "hajm" va
    # "o'sish sur'ati" qatorlari bir xil nom olib, biri yo'qoladi.
    unit_col = min(periods) - 1 if min(periods) - label_col >= 2 else None

    parent_of_row = _parents(df, hr, list(periods), label_col)
    groups = _column_groups(df, hr, periods)

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
        raw_label = _clean(df.iat[row, label_col])
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
            # Yonma-yon jadvallar bir xil yillarni takrorlaydi — guruh
            # nomi ularni ajratib turadi
            group = groups.get(col, "")
            full = f"{indicator} — {group}" if group else indicator
            yield Record(
                category=category,
                indicator=full.strip(" —")[:300],
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


def _column_names(df: pd.DataFrame, upto: int) -> dict[int, str]:
    """
    Ustun sarlavhalari — `upto` qatorigacha bo'lgan matnlar birlashtirilgan.

    Sarlavha bir necha qatorga yoyilgan bo'ladi: "Barshe túrdegi
    xojalıqlar" / "Fermer xojalıqları" / "Jámi". Uchalasi bitta nomga
    qo'shiladi, aks holda qo'shni ustunlar bir xil nom olib qoladi.
    """
    # Guruh sarlavhasi birlashtirilgan katakda turadi: matn faqat guruhning
    # BIRINCHI ustunida bo'ladi, qolganlari bo'sh. Uni o'ngga tarqatmasak,
    # qo'shni guruhlarning ustunlari bir xil nom olib, qiymatlari bitta
    # kalitga tushib qolardi.
    spread: list[dict[int, str]] = []
    for row in range(upto):
        filled: dict[int, str] = {}
        current = ""
        for col in range(df.shape[1]):
            text = _clean(df.iat[row, col]).replace("\n", " ").strip()
            if text:
                current = text
            if current and current.lower() not in _BREAKDOWN_MARKERS:
                filled[col] = current
        spread.append(filled)

    names: dict[int, str] = {}
    for col in range(1, df.shape[1]):
        parts: list[str] = []
        for filled in spread:
            text = filled.get(col, "")
            if text and text not in parts:
                parts.append(text)
        if parts:
            names[col] = " — ".join(parts)
    return names


def parse_vertical(df: pd.DataFrame, *, category: str, source: str) -> Iterator[Record]:
    """
    Davrlar QATORLARDA turgan varaq (birinchi ustunda "2010 j.", "2024").

    Ikki ko'rinishi bor va ikkalasi ham shu yerda hal qilinadi:
      · davr qatorining o'zida qiymatlar bor — respublika qatori;
      · davr qatori bo'sh, undan keyingi qatorlar hududlar — u holda davr
        keyingi davrgacha amal qiladi (tug'ilish, o'lim, aholi fayllari).
    """
    periods: dict[int, tuple[int, PeriodKind, int | None]] = {}
    for row in range(len(df)):
        if p := parse_period(df.iat[row, 0]):
            periods[row] = p
    if len(periods) < 3:
        return

    first = min(periods)
    names = _column_names(df, first)
    if not names:
        return

    preamble = _preamble(df, first)
    title = _title(preamble)
    ordered = sorted(periods)

    # O'lchov birligi ustunning O'Z nomida bo'lishi mumkin ("Aymaǵı (mıń km2)").
    # Bunday varaqda sarlavhadagi umumiy birlikni qolgan ustunlarga tarqatib
    # bo'lmaydi: "Rayonlar — 16" ni "mıń km2" deb belgilash xato bo'lardi.
    own_units = {col: _unit([], name) for col, name in names.items()}
    shared_unit = "" if any(own_units.values()) else _unit(preamble)

    for idx, row in enumerate(ordered):
        year, kind, no = periods[row]
        end = ordered[idx + 1] if idx + 1 < len(ordered) else len(df)

        for target in range(row, end):
            label = _clean(df.iat[target, 0])
            # Davr qatorining o'zi hudud emas — u respublika yig'masi
            district = None if target == row else resolve(label)
            if target != row and district is None:
                continue

            for col, name in names.items():
                val = _numeric(df.iat[target, col])
                if val is None:
                    continue
                yield Record(
                    category=category,
                    indicator=f"{title} — {name}".strip(" —")[:300],
                    unit=own_units[col] or shared_unit,
                    district_id=None if district in (None, REPUBLIC) else district,
                    year=year,
                    period=kind,
                    period_no=no,
                    value=val,
                    source=source,
                    row=target,
                    block=0,
                )


def parse_district_columns(df: pd.DataFrame, *, category: str, source: str) -> Iterator[Record]:
    """
    Hududlar USTUNLARDA turgan varaq — jadval yon tomonga o'girilgan.

    Bunday varaqda davr sarlavha qatorida emas, sahifa nomida bo'ladi
    ("2026-jıl yanvar-iyun ..."), qatorlar esa ko'rsatkichlar.
    """
    header, columns = None, {}
    for row in range(min(12, len(df))):
        found = {}
        for col in range(df.shape[1]):
            if did := resolve(_clean(df.iat[row, col])):
                found[col] = did
        if len(found) >= 5:
            header, columns = row, found
            break
    if header is None:
        return

    preamble = _preamble(df, header + 1)
    period = next((p for text in preamble if (p := parse_period(text))), None)
    if period is None:
        return
    year, kind, no = period
    title = _title(preamble)

    for row in range(header + 1, len(df)):
        label = _clean(df.iat[row, 0])
        if not label or label.lower() in _BREAKDOWN_MARKERS:
            continue
        for col, district in columns.items():
            val = _numeric(df.iat[row, col])
            if val is None:
                continue
            yield Record(
                category=category,
                indicator=f"{title} — {label}".strip(" —")[:300],
                unit=_unit(preamble, label),
                district_id=None if district == REPUBLIC else district,
                year=year,
                period=kind,
                period_no=no,
                value=val,
                source=source,
                row=row,
                block=0,
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
