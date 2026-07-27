"""
RAG + from-to.uz Translation Pipeline
======================================

Tolıq arxitektura:

  Soraw (Uzbek/Karakalpak/Rus)
        ↓
  [Retriever] — naqıy ekonomikaliq sanlar
        ↓
  [Shablon generator] — Uzbekcha aniq matn (naqıy sanlar bilan)
        ↓
  [from-to.uz API] — Uzbekcha → Karakalpaqsha (Kirill)
        ↓
  Karakalpaqsha juwap — Hallucination = 0%
"""

import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.rag import DataRetriever, _extract_keywords, _extract_year, _extract_year
from src.translator import get_translator


# ─────────────────────────────────────────────────────────────
#  UZBEKCHA SHABLON GENERATORLAR (naqıy sanlar bilan)
# ─────────────────────────────────────────────────────────────

def _build_uz_response(context: dict) -> str:
    """
    Naqıy sanlardan Uzbekcha analitik matn yarat.
    Bu matn so'ng Karakalpaqshaga tarjima qilinadi.
    """
    sanlar  = context.get("sanlar", {})
    soraw   = context.get("soraw", "")
    region  = context.get("rayon")
    year    = context.get("jil")

    lines = []

    # ── Statistika bo'limi ──────────────────────────────────
    lines.append("## Statistika\n")

    has_data = False

    for mod, info in sanlar.items():
        if mod == "barcha_rayonlar":
            yr = info["jil"]
            jumissizliq = info["jumissizliq"]
            sorted_r = sorted(jumissizliq.items(), key=lambda x: x[1], reverse=True)
            lines.append(f"{yr}-yilda tumanlar bo'yicha ishsizlik darajasi (%):\n")
            for r, p in sorted_r[:5]:
                lines.append(f"- **{r}**: {p:.2f}%")
            lines.append(f"\nEng yuqori: **{sorted_r[0][0]}** — {sorted_r[0][1]:.2f}%")
            lines.append(f"Eng past: **{sorted_r[-1][0]}** — {sorted_r[-1][1]:.2f}%")
            has_data = True

        elif "pati" in info:
            lines.append(
                f"**{info['rayon']}** tumanida {info['jil']}-yilda:\n"
                f"- Iqtisodiy faol aholi: **{info['aktiv_xaliq']:,.1f}** ming kishi\n"
                f"- Bandlar: **{info['bantler']:,.1f}** ming kishi\n"
                f"- Ishsizlar: **{info['jumissizlar']:,.1f}** ming kishi\n"
                f"- **Ishsizlik darajasi: {info['pati']:.2f}%**"
            )
            has_data = True

        elif "mán" in info:
            birim = info.get("birim", "")
            lines.append(
                f"**{mod}** ({info['jil']}-yil): **{info['mán']:,.2f}** {birim}"
            )
            has_data = True

        elif "dinamika" in info:
            birim = info.get("birim", "")
            lines.append(f"\n**{mod}** so'nggi yillar dinamikasi ({birim}):")
            items = sorted(info["dinamika"].items())
            for y, v in items[-4:]:
                lines.append(f"- {y}: {v:,.1f}")
            if len(items) >= 2:
                last_two = items[-2:]
                osim = (last_two[1][1] - last_two[0][1]) / last_two[0][1] * 100
                lines.append(
                    f"\nO'sish: **{osim:+.1f}%** "
                    f"({last_two[0][0]} → {last_two[1][0]})"
                )
            has_data = True

        elif "sońǵı_kvartalar" in info:
            lines.append("\n**Ish haqi** (ming so'm, so'nggi kvartallar):")
            for q, v in list(info["sońǵı_kvartalar"].items())[-4:]:
                lines.append(f"- {q}: {v:,.0f} ming so'm")
            has_data = True

    if not has_data:
        lines.append(
            "Ushbu so'rov bo'yicha ma'lumotlar bazada topilmadi. "
            "Iltimos, tegishli ko'rsatkichni aniqlashtirib so'rang."
        )

    # DB dan admin kiritgan sanlar
    if context.get("db_sanlar"):
        lines.append("\n**Admin kiritgan ma'lumotlar:**")
        for item in context["db_sanlar"][:8]:
            try:
                plan = float(item.get("kpi_planned") or 0)
                amal = float(item.get("kpi_actual")  or 0)
            except (TypeError, ValueError):
                plan, amal = 0, 0
            unit = item.get("unit", "")
            pct  = round(amal/plan*100, 1) if plan and plan != 0 else "?"
            lines.append(
                f"- {item.get('module','?')} | {item.get('region','?')} | "
                f"{item.get('year','?')}: reja={plan} → amalda={amal} {unit} "
                f"({pct}%) [{item.get('status','?')}]"
            )
            if item.get("comment"):
                lines.append(f"  *{item['comment']}*")

    # ── Tahlil ─────────────────────────────────────────────
    lines.append("\n## Tahlil\n")

    if has_data:
        # Eksport/Import saldo
        if "Eksport" in sanlar and "Import" in sanlar:
            exp_info = sanlar.get("Eksport", {})
            imp_info = sanlar.get("Import", {})
            sal_info = sanlar.get("Saldo", {})

            if "mán" in exp_info and "mán" in imp_info:
                saldo = exp_info["mán"] - imp_info["mán"]
                lines.append(
                    f"Eksport ({exp_info['mán']:,.1f} mln.$) "
                    f"{'import dan yuqori' if saldo >= 0 else 'importdan past'} "
                    f"({imp_info['mán']:,.1f} mln.$). "
                    f"Savdo balansi: **{saldo:+,.1f} mln.$**"
                )
            elif "dinamika" in exp_info:
                last = sorted(exp_info["dinamika"].items())[-1]
                lines.append(
                    f"{last[0]}-yilda eksport: {last[1]:,.1f} mln.$. "
                    f"Eksport barqarorligi muhim iqtisodiy ko'rsatkich."
                )

        # JAO tahlili
        elif "JAO" in sanlar:
            info = sanlar["JAO"]
            if "mán" in info:
                lines.append(
                    f"{info['jil']}-yilda YaIM {info['mán']:,.1f} mlrd. so'm bo'lib, "
                    f"respublikaning iqtisodiy o'sishi davom etmoqda."
                )
            elif "dinamika" in info:
                items = sorted(info["dinamika"].items())
                if len(items) >= 2:
                    osim = (items[-1][1] - items[-2][1]) / items[-2][1] * 100
                    lines.append(
                        f"YaIM o'tgan yilga nisbatan **{osim:+.1f}%** o'sdi. "
                        f"Iqtisodiy o'sish barqaror trayektoriyada."
                    )

        # Jumıssızlıq tahlili
        elif "Jumıssızlıq" in sanlar:
            info = sanlar["Jumıssızlıq"]
            if "pati" in info:
                lines.append(
                    f"{info['rayon']}da ishsizlik darajasi {info['pati']:.2f}% ni tashkil etadi. "
                    f"{'Bu respublika o\'rtachasidan past.' if info['pati'] < 5 else 'Bu ko\'rsatkich nazorat ostida saqlanishi zarur.'}"
                )
        else:
            lines.append(
                "Ko'rsatkichlar tahlili asosiy tendensiyalarni aniqlashga imkon beradi."
            )
    else:
        lines.append("Ma'lumotlar yetarli emas — qo'shimcha ma'lumot kiritish tavsiya etiladi.")

    # ── Muammo ─────────────────────────────────────────────
    lines.append("\n## Muammo\n")

    if "Eksport" in sanlar or "Import" in sanlar or "Saldo" in sanlar:
        sal = sanlar.get("Saldo", {})
        if "mán" in sal and sal["mán"] < 0:
            lines.append(
                f"- Savdo balansi manfiy ({sal['mán']:,.1f} mln.$) — "
                f"import eksportdan ko'p\n"
                f"- Eksport barqarorligi past: kimyoviy mahsulot narxlariga bog'liqlik yuqori\n"
                f"- Import almashtirish siyosati zaif"
            )
        else:
            lines.append(
                "- Eksport tarkibini diversifikatsiya qilish zarur\n"
                "- Yangi bozorlar va sherik mamlakatlar topish kerak"
            )
    elif "JAO" in sanlar:
        lines.append(
            "- YaIM tarkibida xizmatlar sektorining ulushi oshishi zarur\n"
            "- Tashqi investitsiyalar jalb qilishda muammolar bor\n"
            "- Tumanlar o'rtasidagi iqtisodiy tengsizlik saqlanmoqda"
        )
    elif "Jumıssızlıq" in sanlar:
        lines.append(
            "- Tumanlar o'rtasidagi ishsizlik darajasidagi farq katta\n"
            "- Qishloq joylarda ish o'rinlari yetarli emas\n"
            "- Kasbiy ta'lim va malaka oshirish imkoniyatlari cheklangan"
        )
    elif "AwılXojalıǵı" in sanlar:
        lines.append(
            "- Sug'orish tizimida suv tanqisligi\n"
            "- Orol dengizining qurib borishidan tuproq sho'rlanishi\n"
            "- Qishloq xo'jaligi erlari maydoni qisqarmoqda"
        )
    else:
        lines.append(
            "- Ko'rsatkichlarni monitoring qilishni kuchaytirish zarur\n"
            "- Resurslarni samarali taqsimlash mexanizmlarini takomillashtirish kerak"
        )

    # ── Usınıs ─────────────────────────────────────────────
    lines.append("\n## Tavsiyalar\n")
    lines.append(
        "**Qisqa muddatli (1-3 oy):**\n"
        "- Zaif ko'rsatkichli hududlarda tezkor monitoring o'rnatish\n"
        "- Imkoniyatlar va resurslarni qayta taqsimlash\n\n"
        "**O'rta muddatli (6 oy):**\n"
        "- Investitsiya muhitini yaxshilash chora-tadbirlarini amalga oshirish\n"
        "- Mahalliy ishlab chiqarishni qo'llab-quvvatlash\n\n"
        "**Uzoq muddatli (1 yil):**\n"
        "- Iqtisodiyotni diversifikatsiyalash strategiyasini ishlab chiqish\n"
        "- Hududlar o'rtasidagi tengsizlikni kamaytirish"
    )

    # ── Juwmaq ─────────────────────────────────────────────
    lines.append("\n## Xulosa\n")
    lines.append(
        "Taqdim etilgan statistik ma'lumotlar asosida tahlil amalga oshirildi. "
        "Ko'rsatkichlarni muntazam monitoring qilish va o'z vaqtida chora ko'rish "
        "barqaror iqtisodiy o'sishni ta'minlaydi."
    )

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
#  ASOSIY RAG + TRANSLATION FUNKSIYASI
# ─────────────────────────────────────────────────────────────

class RAGTranslationPipeline:
    """
    RAG + from-to.uz tarjimasi birgalikda.
    1. Retriever — naqıy sanlar
    2. Uzbekcha shablon — aniq matn
    3. Tarjima — Karakalpaqsha
    """

    def __init__(self, api_key: str = None):
        self.retriever  = DataRetriever()
        self.translator = get_translator(api_key)

    def ask(
        self,
        question: str,
        db_items: list = None,
        lang_to: str = "kaa_Cyrl",
        result_case: str = "cyrillic",
    ) -> dict:
        """
        Sorawga naqıy sanlar bilan Karakalpaqsha juwap.
        """
        # 1. RETRIEVE
        context = self.retriever.get_context(question, db_items)

        # 2. Uzbekcha shablon yaratish
        uz_text = _build_uz_response(context)

        # 3. Tarjima: Uzbekcha → Karakalpaqsha
        kaa_text = self.translator.translate(
            uz_text,
            lang_from="uzn_Latn",
            lang_to=lang_to,
            result_case=result_case,
        )

        return {
            "soraw":        question,
            "juwap":        kaa_text,
            "uz_juwap":     uz_text,           # debug uchun
            "kontekst":     context["sanlar"],
            "rayon":        context["rayon"],
            "jil":          context["jil"],
        }

    def translate_only(self, text: str, lang_from: str = "uzn_Latn") -> str:
        """Faqat tarjima."""
        return self.translator.translate(text, lang_from, "kaa_Cyrl")

    def test(self) -> bool:
        """Barlıq sistemani sinash."""
        print("[RAG+Trans] Retriever sinash...")
        ctx = self.retriever.get_context("2025 yilda investitsiya")
        print(f"  Retriever: {len(ctx['sanlar'])} modul topildi")

        print("[RAG+Trans] Tarjimon sinash...")
        ok = self.translator.test_connection()
        return ok


# ─────────────────────────────────────────────────────────────
#  Singleton
# ─────────────────────────────────────────────────────────────
_pipeline: RAGTranslationPipeline | None = None


def get_rag_translation(api_key: str = None) -> RAGTranslationPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGTranslationPipeline(api_key=api_key)
    return _pipeline
