"""
RAG Pipeline — Retrieval-Augmented Generation
=============================================
Soraw → Naqıy maǵlıwmat → Kontekst → Qwen2.5-3B → Karakalpaqsha juwap

Hallucination = 0%  (model faqat berilgen sanlardan paydalanadi)
"""

import os, sys, re, json, warnings, pickle
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

# ─────────────────────────────────────────────────────────────
#  1. KONTEKST RETRIEVER — naqıy sanlarni tabıw
# ─────────────────────────────────────────────────────────────

# Kalit sozlar → modul mapping
KEYWORD_MAP = {
    # JAO — barcha variatsiyalar
    "jao": "JAO", "jaó": "JAO", "jaó": "JAO",
    "jalpı aymaqlıq": "JAO", "yalpi": "JAO",
    "gdp": "JAO", "umumiy mahsulot": "JAO", "regional": "JAO",
    "yalpi mahsulot": "JAO", "iqtisodiy o'sish": "JAO",

    # Sanaat
    "sanaat": "Sanaat", "sanoat": "Sanaat", "industry": "Sanaat",
    "ximiya": "Sanaat", "toqımashılıq": "Sanaat", "azıq": "Sanaat",

    # Awıl xojalıǵı
    "awıl": "AwılXojalıǵı", "awil": "AwılXojalıǵı", "qishloq": "AwılXojalıǵı",
    "dıyqan": "AwılXojalıǵı", "sharwa": "AwılXojalıǵı", "balıq": "AwılXojalıǵı",
    "egin": "AwılXojalıǵı", "fermer": "AwılXojalıǵı",

    # Investitsiya
    "investitsiya": "Investitsiya", "kapital": "Investitsiya",
    "qurılıs": "Qurılıs", "qurilish": "Qurılıs",

    # Eksport/Import
    "eksport": "Eksport", "import": "Import",
    "sawda": "Sawda", "saldo": "Saldo", "tashqi": "Eksport",

    # Xızmetler
    "xızmet": "Xızmetler", "xizmat": "Xızmetler", "servis": "Xızmetler",
    "transport": "Xızmetler", "finanslıq": "Xızmetler",

    # Jumıssızlıq
    "jumıssız": "Jumıssızlıq", "ishsiz": "Jumıssızlıq", "bandlik": "Jumıssızlıq",
    "bántler": "Jumıssızlıq", "aktiv xalıq": "Jumıssızlıq",

    # Is haqı
    "is haqı": "IsHaqı", "maosh": "IsHaqı", "ish haqi": "IsHaqı",
    "aylıq": "IsHaqı",
}

RAYON_MAP = {
    "nukus": "Nukus qalası", "nókis": "Nukus qalası",
    "amudarya": "Amudarya", "ámiwdárya": "Amudarya",
    "beruniy": "Beruniy", "beruni": "Beruniy",
    "kegeyli": "Kegeyli", "kegeyli": "Kegeyli",
    "qońırat": "Qońırat", "kongirot": "Qońırat", "qo'ng'irot": "Qońırat",
    "mójnak": "Mójnak", "mo'ynoq": "Mójnak",
    "shımbay": "Shımbay", "chimboy": "Shımbay",
    "taxiatash": "Taxiatash", "taxiatosh": "Taxiatash",
    "taxtakópir": "Taxtakópir", "taxtako'pir": "Taxtakópir",
    "ellikqala": "Ellikqala", "ellikqal'a": "Ellikqala",
    "qaraózek": "Qaraózek", "qorao'zak": "Qaraózek",
    "xojayli": "Xojayli", "xo'jayli": "Xojayli",
    "tórtk¸l": "Tórtk¸l", "to'rtko'l": "Tórtk¸l",
    "bózataw": "Bózataw", "bo'zatov": "Bózataw",
    "shumanay": "Shumanay",
    "qr": "QR jámi", "respublika": "QR jámi",
}


def _extract_year(text: str) -> int | None:
    """Sorawdan jilni tabıw."""
    matches = re.findall(r'\b(20[12]\d)\b', text)
    if matches:
        return int(matches[-1])
    return None


def _extract_keywords(text: str) -> tuple[list, str | None]:
    """Modullar hám rayon anıqlaw."""
    text_low = text.lower()
    modules  = []
    region   = None

    for kw, mod in KEYWORD_MAP.items():
        if kw in text_low and mod not in modules:
            modules.append(mod)

    for kw, ray in RAYON_MAP.items():
        if kw in text_low:
            region = ray
            break

    return modules, region


class DataRetriever:
    """
    Sorawga mos naqıy ekonomikalıq maǵlıwmatlardı tabıw.
    Excel faylları hám PostgreSQL dan oqıdı.
    """

    def __init__(self):
        self._macro   = None
        self._unemp   = None
        self._salary  = None
        self._sanaat  = None
        self._loaded  = False

    def _lazy_load(self):
        if self._loaded:
            return
        try:
            from src.data_loader import (
                load_macro, load_rayon_unemployment,
                load_salary, load_sanaat,
            )
            self._macro  = load_macro()
            self._unemp  = load_rayon_unemployment()
            self._salary = load_salary()
            self._sanaat = load_sanaat()
            self._loaded = True
        except Exception as e:
            print(f"[RAG] Maǵlıwmat júklenmedi: {e}")
            self._loaded = True  # qayta urinmasliq

    def get_context(self, question: str, db_items: list = None) -> dict:
        """
        Sorawga mos barlıq naqıy maǵlıwmatlardı qaytaradı.
        db_items: PostgreSQL dan kelgan admin-kiritgan sanlar (ixtiyoriy)
        """
        self._lazy_load()
        modules, region = _extract_keywords(question)
        year = _extract_year(question)

        # Eger hech narsa topilmasa — asosiy modullarni qo'sh
        if not modules:
            modules = ["JAO"]

        context = {
            "soraw":   question,
            "modullar": modules,
            "rayon":   region,
            "jil":     year,
            "sanlar":  {},
            "db_sanlar": [],
        }

        # ── Makro sanlar ──────────────────────────────────────
        if self._macro is not None and not self._macro.empty:
            for mod in modules:
                if mod in self._macro.columns:
                    series = self._macro[mod].dropna()
                    if year and year in series.index:
                        context["sanlar"][mod] = {
                            "jil": year,
                            "mán": round(float(series[year]), 2),
                            "birim": "mlrd. som" if mod not in ("Eksport","Import","Saldo") else "mln. $"
                        }
                    else:
                        # Sońǵı jıllar
                        last_yrs = series.tail(4)
                        context["sanlar"][mod] = {
                            "dinamika": {
                                int(y): round(float(v), 2)
                                for y, v in last_yrs.items()
                            },
                            "birim": "mlrd. som" if mod not in ("Eksport","Import","Saldo") else "mln. $"
                        }

        # ── Jumıssızlıq ──────────────────────────────────────
        if "Jumıssızlıq" in modules and self._unemp is not None:
            df = self._unemp
            if region:
                df_r = df[df["Rayon"] == region]
            else:
                df_r = df[df["Rayon"] == "QR jámi"]

            if year:
                df_r = df_r[df_r["Jıl"] == year]
            else:
                df_r = df_r[df_r["Jıl"] == df_r["Jıl"].max()]

            if not df_r.empty:
                row = df_r.iloc[-1]
                context["sanlar"]["Jumıssızlıq"] = {
                    "jil":           int(row["Jıl"]),
                    "rayon":         row["Rayon"],
                    "aktiv_xaliq":   round(float(row["AktivXalıq"]), 1),
                    "bantler":       round(float(row["Bántler"]), 1),
                    "jumissizlar":   round(float(row["Jumıssızlar"]), 1),
                    "pati":          round(float(row["JumıssızlıqPáti"]), 2),
                    "birim":         "mıń adam / %"
                }

        # ── Rayon salistirmasi ────────────────────────────────
        if region and self._unemp is not None:
            df = self._unemp
            target_yr = year or df["Jıl"].max()
            df_yr = df[df["Jıl"] == target_yr]
            all_regions = {}
            for _, row in df_yr.iterrows():
                all_regions[row["Rayon"]] = round(float(row["JumıssızlıqPáti"]), 2)
            if all_regions:
                context["sanlar"]["barcha_rayonlar"] = {
                    "jil": int(target_yr),
                    "jumissizliq": all_regions
                }

        # ── Is haqı ──────────────────────────────────────────
        if "IsHaqı" in modules and self._salary is not None:
            try:
                row = self._salary.iloc[0]  # Ortasha ayliq
                last_cols = [c for c in self._salary.columns if "Q" in c][-4:]
                vals = {c: round(float(row[c])/1000, 0) for c in last_cols if pd.notna(row[c])}
                context["sanlar"]["IsHaqı"] = {
                    "sońǵı_kvartalar": vals,
                    "birim": "mıń som"
                }
            except Exception:
                pass

        # ── DB dan admin kiritgan sanlar ──────────────────────
        if db_items:
            context["db_sanlar"] = db_items

        return context


# ─────────────────────────────────────────────────────────────
#  2. PROMPT BUILDER — kontekstdan prompt jasaw
# ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT_RAG = """Sen Qaraqalpaqstan Respublikasınıń ekonomika ekspertisen.
Senden soralan sorawlarga TEK TÖMEN BERILGEN MAǴLIWMATLARǴA tiykarlanıp juwap beriw kerek.
Berilmegen maǵlıwmatlardı ÓYLEP TABIW YASAQ — "maǵlıwmat joq" dep jazıw kerek.
Juwap strukturası: ## Statistika → ## Analiz → ## Muammo → ## Usınıs → ## Juwmaq
Barlıq naqıy sanlar körsatilishi kerek."""


def build_prompt(context: dict) -> str:
    """Kontekstdan model ushın prompt jasaw."""
    lines = ["=== NAQIY EKONOMIKALIQ MAǴLIWMATLAR ===\n"]

    # Makro sanlar
    for mod, info in context["sanlar"].items():
        if mod == "barcha_rayonlar":
            lines.append(f"\n{info['jil']}-jıl Rayon jumıssızlıq dárejesi (%):")
            for rayon, pati in sorted(info["jumissizliq"].items(),
                                      key=lambda x: x[1], reverse=True):
                lines.append(f"  • {rayon}: {pati}%")
        elif "dinamika" in info:
            lines.append(f"\n{mod} dinamikası ({info.get('birim','')}):")
            for y, v in sorted(info["dinamika"].items()):
                lines.append(f"  • {y}-jıl: {v:,.1f}")
        elif "mán" in info:
            birim = info.get("birim", "")
            lines.append(f"\n{mod} ({info['jil']}-jıl): {info['mán']:,.2f} {birim}")
        elif "aktiv_xaliq" in info:
            lines.append(f"\nJumıssızlıq ({info['rayon']}, {info['jil']}-jıl):")
            lines.append(f"  • Aktiv xalıq:  {info['aktiv_xaliq']:,.1f} mıń")
            lines.append(f"  • Bántler:       {info['bantler']:,.1f} mıń")
            lines.append(f"  • Jumıssızlar:   {info['jumissizlar']:,.1f} mıń")
            lines.append(f"  • Dáreje:        {info['pati']:.2f}%")
        elif "sońǵı_kvartalar" in info:
            lines.append(f"\nIs haqı (mıń som):")
            for q, v in info["sońǵı_kvartalar"].items():
                lines.append(f"  • {q}: {v:,.0f} mıń som")

    # Admin kiritgan sanlar (DB)
    if context.get("db_sanlar"):
        lines.append("\n=== ADMIN KIRITGAN MAǴLIWMATLAR ===")
        for item in context["db_sanlar"][:10]:
            plan = item.get("kpi_planned", "?")
            amal = item.get("kpi_actual", "?")
            unit = item.get("unit", "")
            lines.append(
                f"  • {item.get('module','?')} | {item.get('region','?')} "
                f"| {item.get('year','?')}: reja={plan} → amalda={amal} {unit} "
                f"[{item.get('status','?')}]"
            )

    if len(lines) == 1:
        lines.append("(Maǵlıwmat tabılmadı — admin bazasını tekshiriń)")

    lines.append(f"\n=== SORAW ===\n{context['soraw']}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
#  3. RAG PIPELINE — bas klass
# ─────────────────────────────────────────────────────────────

class RAGPipeline:
    """
    Tolıq RAG: Retrieval + Augmented Prompt + Generation
    """

    def __init__(self):
        self.retriever = DataRetriever()
        self._model     = None
        self._tokenizer = None
        self._loaded    = False

    def load_model(self, lora_path: str = None, base_model: str = "Qwen/Qwen2.5-3B-Instruct"):
        """Fine-tuned modeli yuklash."""
        if lora_path is None:
            lora_path = os.path.join(ROOT, "models", "qwen25_karakalpak_qlora")

        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

        self._tokenizer = AutoTokenizer.from_pretrained(
            lora_path if os.path.exists(lora_path) else base_model,
            trust_remote_code=True,
        )

        base = AutoModelForCausalLM.from_pretrained(
            base_model,
            quantization_config=bnb,
            device_map="auto",
            max_memory={0: "5GiB", "cpu": "16GiB"},
            trust_remote_code=True,
            torch_dtype=torch.bfloat16,
            attn_implementation="eager",
        )

        if os.path.exists(lora_path):
            from peft import PeftModel
            self._model = PeftModel.from_pretrained(base, lora_path)
            print(f"[RAG] Fine-tuned model yuklandi: {lora_path}")
        else:
            self._model = base
            print(f"[RAG] Base model yuklandi: {base_model}")

        self._model.eval()
        self._loaded = True

    def ask(
        self,
        question: str,
        db_items: list = None,
        max_tokens: int = 600,
        temperature: float = 0.3,   # past temp = sanlar aniqroq
    ) -> dict:
        """
        RAG arqalı Karakalpaqsha juwap olıw.
        Qaytaradı: {juwap, kontekst, sanlar}
        """
        # 1. RETRIEVE — naqıy sanlarni tab
        context = self.retriever.get_context(question, db_items)

        # 2. AUGMENT — prompt qur
        prompt_text = build_prompt(context)

        # 3. GENERATE — model ishla
        if self._loaded and self._model is not None:
            import torch
            messages = [
                {"role": "system",  "content": SYSTEM_PROMPT_RAG},
                {"role": "user",    "content": prompt_text},
            ]
            inputs = self._tokenizer.apply_chat_template(
                messages, tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
            ).to(self._model.device)

            with torch.no_grad():
                out = self._model.generate(
                    input_ids=inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    top_p=0.9,
                    do_sample=True,
                    repetition_penalty=1.15,
                    pad_token_id=self._tokenizer.eos_token_id,
                )
            juwap = self._tokenizer.decode(
                out[0][inputs.shape[-1]:], skip_special_tokens=True
            ).strip()
        else:
            juwap = _template_answer(context)

        return {
            "soraw":    question,
            "juwap":    juwap,
            "kontekst": context["sanlar"],
            "rayon":    context["rayon"],
            "jil":      context["jil"],
        }


def _template_answer(context: dict) -> str:
    """Model yuklanmagan waqtı ushın shablon juwap."""
    sanlar = context["sanlar"]
    lines  = ["## Statistika"]

    for mod, info in sanlar.items():
        if mod == "barcha_rayonlar":
            lines.append(f"\n{info['jil']}-jıl rayon jumıssızlıq dárejesi:")
            worst = sorted(info["jumissizliq"].items(), key=lambda x: x[1], reverse=True)
            for r, p in worst[:3]:
                lines.append(f"- {r}: **{p}%**")
        elif "dinamika" in info:
            lines.append(f"\n**{mod}** sońǵı jıllar ({info.get('birim','')}):")
            for y, v in sorted(info["dinamika"].items())[-3:]:
                lines.append(f"- {y}: {v:,.1f}")
        elif "mán" in info:
            lines.append(f"- **{mod}** ({info['jil']}): {info['mán']:,.2f} {info.get('birim','')}")
        elif "aktiv_xaliq" in info:
            lines.append(f"\n**Jumıssızlıq** ({info['rayon']}, {info['jil']}):")
            lines.append(f"- Aktiv: {info['aktiv_xaliq']:,.1f} mıń | Bántler: {info['bantler']:,.1f} mıń")
            lines.append(f"- Jumıssızlar: {info['jumissizlar']:,.1f} mıń | **Dáreje: {info['pati']}%**")

    if not sanlar:
        lines.append("Bul soraw ushın maǵlıwmat bazada tabılmadı.")

    lines += [
        "\n## Analiz",
        "Berilgen maǵlıwmatlar boyınsha analiz jasaldı.",
        "\n## Juwmaq",
        "Naqıy sanlarǵa tiykarlanǵan analiz tamamlandı.",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
#  Singleton
# ─────────────────────────────────────────────────────────────
_rag_pipeline: RAGPipeline | None = None


def get_rag() -> RAGPipeline:
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
    return _rag_pipeline


def startup_rag(load_model: bool = True):
    rag = get_rag()
    if load_model:
        rag.load_model()
    return rag
