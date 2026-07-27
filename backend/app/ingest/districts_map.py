"""
Excel'dagi qoraqalpoqcha hudud nomlarini platformaning ID'lariga moslash.

Statistika fayllarida nomlar qoraqalpoq lotinida yozilgan (Ámiwdárya,
Qońırat, Shımbay...), platformada esa ID'lar o'zbekcha translitdan kelib
chiqqan (amudaryo, qongirot, chimboy...). Moslash diakritikalarni olib
tashlagan holda amalga oshiriladi — shunda fayldan faylga uchraydigan
yozuv farqlari (ǵ/ğ, ı/i, ó/o) muammo tug'dirmaydi.
"""

from __future__ import annotations

import re
import unicodedata

#: Respublika yig'indisi — hudud emas, lekin tekshiruv uchun kerak
REPUBLIC = "__republic__"

# Diakritikasiz, kichik harfli kalit -> platforma ID'si
_CANON: dict[str, str] = {
    "amiwdarya": "amudaryo",
    "beruniy": "beruniy",
    "bozataw": "bozatov",
    "qaraozek": "karaozak",
    "kegeyli": "kegeyli",
    "qonirat": "qongirot",
    "qanlikol": "qanlikol",
    "moynaq": "moynoq",
    "nokis": "nukus-tumani",  # DIQQAT: shahar emas, rayon
    "taqiyatas": "taxiatosh",
    "taxtakopir": "taxtakopir",
    "tortkul": "tortkol",
    "xojeli": "xojayli",
    "shimbay": "chimboy",
    "shomanay": "shumanay",
    "ellikqala": "ellikqala",
}

# Nukus shahri alohida: "Nókis qalası", "Nókis q." — bu qatorlar
# "Nókis" rayonidan OLDIN tekshirilishi shart, aks holda ular
# rayon deb qabul qilinadi va ikkalasi ham buziladi.
_CITY_SUFFIX = re.compile(r"\b(qalasi|qala|q)\b")

_REPUBLIC_KEYS = ("qaraqalpaqstan respublikasi", "qaraqalpaqstan respublikasinda")


def normalize(name: str) -> str:
    """Diakritika, tinish belgilari va ortiqcha bo'shliqlardan tozalaydi."""
    s = unicodedata.normalize("NFKD", str(name).strip().lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    # Qoraqalpoq lotinida NFKD ajratmaydigan harflar
    s = s.translate(str.maketrans({"ı": "i", "ǵ": "g", "ğ": "g", "ń": "n", "ó": "o", "ú": "u"}))
    s = re.sub(r"[^a-z\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def resolve(name: str) -> str | None:
    """
    Nomni hudud ID'siga aylantiradi.

    Qaytaradi: platforma ID'si, REPUBLIC, yoki None (sarlavha/izoh qatori).
    """
    key = normalize(name)
    if not key:
        return None

    if any(key.startswith(r) for r in _REPUBLIC_KEYS):
        return REPUBLIC

    # Shahar tekshiruvi rayondan oldin
    if key.startswith("nokis") and _CITY_SUFFIX.search(key):
        return "nukus-shahri"

    if key in _CANON:
        return _CANON[key]

    # "rayonlar:", "*) daslepki maglıwmatlar" kabi qatorlar
    first = key.split(" ")[0]
    return _CANON.get(first)


#: Platformadagi barcha ID'lar — yuklashda to'liqlikni tekshirish uchun
ALL_DISTRICT_IDS = frozenset(_CANON.values()) | {"nukus-shahri"}
