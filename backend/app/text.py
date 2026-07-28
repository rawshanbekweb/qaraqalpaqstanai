"""Qoraqalpoq matnini qidiruv uchun normallashtirish.

Foydalanuvchi "xaliq" deb yozadi, manbada esa "xalıq" turadi. Diakritika
va apostroflar olib tashlansa ikkalasi ham bitta shaklga keladi.

Diqqat: bu `ingest/loader.py` dagi `slugify` EMAS. U yerdagi qoida bazadagi
mavjud kalitlarni belgilab bo'lgan — o'zgartirilsa qayta yuklashda barcha
ko'rsatkichlar takrorlanadi.
"""

from __future__ import annotations

import unicodedata

#: Unicode NFKD ajratmaydigan harflar (ı, kirill) qo'lda moslanadi.
TRANSLIT = str.maketrans(
    {
        "ı": "i", "ǵ": "g", "ğ": "g", "ģ": "g", "ń": "n", "ó": "o", "ú": "u", "á": "a",
        "ә": "a", "ө": "o", "ү": "u", "ұ": "u", "қ": "q", "ғ": "g", "ң": "n", "һ": "h",
        "'": "", "’": "", "ʻ": "", "`": "",
    }
)


def normalize(text: str) -> str:
    """Kichik harf, diakritikasiz, apostrofsiz shakl."""
    s = unicodedata.normalize("NFKD", text.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.translate(TRANSLIT)
