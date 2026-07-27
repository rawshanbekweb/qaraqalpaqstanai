"""
from-to.uz Translation API Client
===================================
Uzbekcha matn → Karakalpaqsha awdarıw
Endpoint: POST https://api.from-to.uz/api/v1/external/translate
"""

import os
import requests
import json
import time

API_BASE    = "https://api.from-to.uz/api/v1/external"
TRANSLATE_URL   = f"{API_BASE}/translate"
TRANSLITERATE_URL = f"{API_BASE}/transliterate"

# API key environment variable dan yoki to'g'ridan
API_KEY = os.getenv("FROM_TO_API_KEY", "")


class FromToTranslator:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or API_KEY
        if not self.api_key:
            raise ValueError(
                "FROM_TO_API_KEY kerak!\n"
                "set FROM_TO_API_KEY=ft_sizning_keyingiz\n"
                "yoki: translator = FromToTranslator(api_key='ft_...')"
            )
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self._cache = {}  # takroriy so'rovlarni tejash

    def translate(
        self,
        text: str,
        lang_from: str = "uzn_Latn",
        lang_to:   str = "kaa_Cyrl",
        result_case: str = "cyrillic",  # "latin" yoki "cyrillic"
        use_cache:  bool = True,
    ) -> str:
        """
        Matnni tarjima qiladi.

        lang_from kódları:
          uzn_Latn  — Uzbek Latin
          rus_Cyrl  — Russian
          kaa_Latn  — Karakalpak Latin
          kaa_Cyrl  — Karakalpak Cyrillic
          kaz_Cyrl  — Kazakh Cyrillic

        lang_to kódları (bir xil):
          kaa_Cyrl  — Karakalpak Cyrillic (tavsiya)
          kaa_Latn  — Karakalpak Latin
        """
        if not text or not text.strip():
            return text

        # Kesish — API uchun 5000 belgi limit
        text = text[:4900]

        cache_key = f"{lang_from}|{lang_to}|{text[:50]}"
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        payload = {
            "body": {
                "lang_from":   lang_from,
                "lang_to":     lang_to,
                "resultCase":  result_case,
                "text":        text,
            }
        }

        try:
            resp = requests.post(
                TRANSLATE_URL,
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            result = data.get("result", text)

            if use_cache:
                self._cache[cache_key] = result
            return result

        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                print("[Translator] Rate limit — 2 sekund kutish...")
                time.sleep(2)
                return self.translate(text, lang_from, lang_to, result_case, False)
            elif resp.status_code == 401:
                raise ValueError("API key noto'g'ri yoki muddati o'tgan")
            else:
                print(f"[Translator] HTTP xato {resp.status_code}: {e}")
                return text
        except requests.exceptions.ConnectionError:
            print("[Translator] Tarmoq ulanmadi — original matn qaytarildi")
            return text
        except Exception as e:
            print(f"[Translator] Xato: {e}")
            return text

    def transliterate(
        self,
        text: str,
        lang_from: str = "kaa_latin",
        lang_to:   str = "kaa_cyrillic",
    ) -> str:
        """Latin ↔ Kirill o'zgartirish."""
        payload = {
            "body": {
                "lang_from": lang_from,
                "lang_to":   lang_to,
                "text":      text,
            }
        }
        try:
            resp = requests.post(
                TRANSLITERATE_URL,
                headers=self.headers,
                json=payload,
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("result", text)
        except Exception as e:
            print(f"[Transliterate] Xato: {e}")
            return text

    def uz_to_kaa(self, text: str) -> str:
        """Uzbekcha → Karakalpaqsha (Kirill)."""
        return self.translate(text, "uzn_Latn", "kaa_Cyrl", "cyrillic")

    def ru_to_kaa(self, text: str) -> str:
        """Ruscha → Karakalpaqsha (Kirill)."""
        return self.translate(text, "rus_Cyrl", "kaa_Cyrl", "cyrillic")

    def kaa_to_uz(self, text: str) -> str:
        """Karakalpaqsha → Uzbekcha."""
        return self.translate(text, "kaa_Cyrl", "uzn_Latn", "latin")

    def test_connection(self) -> bool:
        """API ulanishini sinash."""
        try:
            result = self.translate("Salom, bu test.", "uzn_Latn", "kaa_Cyrl")
            ok = bool(result and result != "Salom, bu test.")
            print(f"[Translator] Test: {'OK ✓' if ok else 'FAIL'} → '{result}'")
            return ok
        except Exception as e:
            print(f"[Translator] Test xato: {e}")
            return False


# ─────────────────────────────────────────────────────────────
#  Singleton
# ─────────────────────────────────────────────────────────────
_translator: FromToTranslator | None = None


def get_translator(api_key: str = None) -> FromToTranslator:
    global _translator
    if _translator is None:
        _translator = FromToTranslator(api_key=api_key or API_KEY)
    return _translator
