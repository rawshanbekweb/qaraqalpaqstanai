"""
Qaraqalpaqstan Respublikası - Ekonomikalıq Maǵlıwmatlar Júklewshi
"""

import os
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _find_file(keyword: str) -> str | None:
    """Data papkasida rekursiv qidirish (subfolder lar ham)."""
    for root, dirs, files in os.walk(DATA_DIR):
        # 00_Duplikatlar papkasini o'tkazib yuborish
        dirs[:] = [d for d in dirs if d != "00_Duplikatlar"]
        for fname in files:
            if keyword.lower() in fname.lower() and fname.endswith(".xlsx"):
                return os.path.join(root, fname)
    return None


def _safe_float(v) -> float | None:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    s = str(v).strip().replace(" ", "").replace(",", ".")
    if s in ("nan", "NaN", "x", "х", "X", "Х", "-", ""):
        return None
    try:
        return float(s)
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────
#  1. MAKROEKONOMIKALIQ KÓRSETKISHLER
# ─────────────────────────────────────────────────────────────
def load_macro() -> pd.DataFrame:
    """
    Jıllar × kórsetkishler DataFrame.
    Kórsetkishler: JAO, Sanaat, AwılXojalıǵı, Investitsiya,
                   Qurılıs, Eksport, Import, Xızmetler, SawdaAylanbası
    Tek mlrd./mln. qatarlar (ósim páti % qatarları esepke alınbaydı)
    """
    path = _find_file("Makroekonomikalıq")
    if path is None:
        raise FileNotFoundError("Makroekonomikalıq kórsetkishler fayl tabılmadı")

    raw = pd.read_excel(path, header=None)

    # Row 2-de jıllar bar: "2010 j.", "2011 j.", ...
    years_row = raw.iloc[2]
    year_map = {}   # col_index → year (int)
    for ci, val in enumerate(years_row):
        s = str(val).strip() if pd.notna(val) else ""
        if s.startswith("20"):
            try:
                y = int(s[:4])
                if 2010 <= y <= 2030:
                    year_map[ci] = y
            except ValueError:
                pass

    # Kórsetkish atiw qoidalari
    LABEL_MAP = {
        "Jalpı aymaqlıq ónim":           "JAO",
        "Sanaat ónimi":                   "Sanaat",
        "Awıl, toğay hám balıqshilıq":   "AwılXojalıǵı",
        "Tiykarǵı kapitalǵa investitsiyalar": "Investitsiya",
        "Qurılıs jumısları":             "Qurılıs",
        "Eksport":                        "Eksport",
        "Import":                         "Import",
        "Xızmetler, jámi":               "Xızmetler",
        "Usaqlap satıw sawda tovar":     "SawdaAylanbası",
        "Saldo":                          "Saldo",
    }

    records = {}       # short_name → {year: value}
    current_label = None
    skip_next = False  # ósim páti qatarın ótiriw

    for ri in range(3, len(raw)):
        row = raw.iloc[ri]
        label_cell = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        unit_cell  = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""

        # Jańa kórsetkish baslandı ma?
        for key, short in LABEL_MAP.items():
            if key in label_cell:
                current_label = short
                skip_next = False
                break

        if current_label is None:
            continue

        # Bu qator ósim páti (%) bolsa — ótip ket
        if "o'siw" in unit_cell.lower() or "ósim" in unit_cell.lower() or "%" in unit_cell:
            skip_next = True
            continue

        if skip_next:
            skip_next = False

        # mlrd./mln. maǵlıwmat qatarı
        if "mlrd" in unit_cell.lower() or "mln" in unit_cell.lower():
            if current_label not in records:
                vals = {}
                for ci, y in year_map.items():
                    fv = _safe_float(row.iloc[ci])
                    if fv is not None:
                        vals[y] = fv
                if vals:
                    records[current_label] = vals

    df = pd.DataFrame(records)
    df.index.name = "Jıl"
    df = df.sort_index()
    return df


# ─────────────────────────────────────────────────────────────
#  2. RAYON BOYINSHA JUMISSIZLIQ
# ─────────────────────────────────────────────────────────────
RAYON_KK_MAP = {
    "Qoraqalpog'iston Respublikasi": "QR jámi",
    "Nukus sh.":      "Nukus qalası",
    "Amudaryo":       "Amudarya",
    "Beruniy":        "Beruniy",
    "Bo'zatov":       "Bózataw",
    "Qorao'zak":      "Qaraózek",
    "Kegeyli":        "Kegeyli",
    "Qo'ng'irot":     "Qońırat",
    "Qanliko'l":      "Qanlikól",
    "Mo'ynoq":        "Mójnak",
    "Nukus":          "Nukus tumani",
    "Taxiatosh":      "Taxiatash",
    "Taxtako'pir":    "Taxtakópir",
    "To'rtko'l":      "Tórtk¸l",
    "Xo'jayli":       "Xojayli",
    "Chimboy":        "Shımbay",
    "Shumanay":       "Shumanay",
    "Ellikqal'a":     "Ellikqala",
}


def load_rayon_unemployment() -> pd.DataFrame:
    """
    Rayon × Jıl jumıssızlıq maǵlıwmatları.
    Kolonnalar: Jıl, Rayon, AktivXalıq, Bántler, Jumıssızlar, JumıssızlıqPáti
    """
    path = _find_file("Ekonomikalıq aktiv")
    if path is None:
        raise FileNotFoundError("Jumıssızlıq fayl tabılmadı")

    raw = pd.read_excel(path, header=None)

    # Row 2-de jıllar: "2025 й.", "2024 й.", ...
    # Hár jıl 4 kolonnadan baslanadı (col 1, 5, 9, ...)
    year_start_cols = {}   # col_index → year
    for ci in range(len(raw.iloc[2])):
        v = raw.iloc[2, ci]
        s = str(v).strip() if pd.notna(v) else ""
        if s.startswith("20"):
            try:
                y = int(s[:4])
                if 2015 <= y <= 2030:
                    year_start_cols[ci] = y
            except ValueError:
                pass

    # Hár jıl ushın 4 kolonn: aktiv, bántler, jumıssız, páti
    CHUNK = 4

    records = []
    for ri in range(5, len(raw)):
        row = raw.iloc[ri]
        rayon_raw = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""

        kk_name = None
        for orig, kk in RAYON_KK_MAP.items():
            if orig in rayon_raw:
                kk_name = kk
                break

        if kk_name is None:
            continue

        for start_ci, year in year_start_cols.items():
            cols = [start_ci + i for i in range(CHUNK)]
            if max(cols) >= len(row):
                continue
            vals = [_safe_float(row.iloc[c]) for c in cols]
            if any(v is None for v in vals):
                continue
            aktiv, bant, jumissiz, pati = vals
            records.append({
                "Jıl":             year,
                "Rayon":           kk_name,
                "AktivXalıq":      aktiv,
                "Bántler":         bant,
                "Jumıssızlar":     jumissiz,
                "JumıssızlıqPáti": pati,
            })

    df = pd.DataFrame(records)
    if df.empty:
        return df
    df = df.sort_values(["Rayon", "Jıl"]).reset_index(drop=True)
    return df


# ─────────────────────────────────────────────────────────────
#  3. IS HAQI (Kvartal boyinsha)
# ─────────────────────────────────────────────────────────────
def load_salary() -> pd.DataFrame:
    """
    Kvartal × Tarmaqlaq is haqı DataFrame.
    """
    path = _find_file("Is haq")
    if path is None:
        raise FileNotFoundError("Is haqı fayl tabılmadı")

    raw = pd.read_excel(path, header=None)

    # Kvartal qatarın tabıw
    qtr_row_idx = None
    for ri in range(min(8, len(raw))):
        row_vals = [str(v).strip() for v in raw.iloc[ri] if pd.notna(v)]
        if sum(1 for v in row_vals if "Q" in v and "20" in v) >= 4:
            qtr_row_idx = ri
            break

    if qtr_row_idx is None:
        raise ValueError("Is haqı: kvartal qatarı tabılmadı")

    headers = [str(v).strip() if pd.notna(v) else "" for v in raw.iloc[qtr_row_idx]]
    qtrs = [h for h in headers if "Q" in h and "20" in h]

    data_rows = []
    for ri in range(qtr_row_idx + 1, len(raw)):
        row = raw.iloc[ri]
        label = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        if not label or label in ("nan", "NaN"):
            continue
        nums = []
        for v in row.iloc[1: 1 + len(qtrs)]:
            fv = _safe_float(v)
            nums.append(fv if fv is not None else np.nan)
        data_rows.append([label] + nums)

    df = pd.DataFrame(data_rows, columns=["Tarmaqlaq"] + qtrs)
    df = df.set_index("Tarmaqlaq")
    return df


# ─────────────────────────────────────────────────────────────
#  4. SANAAT KÓLEM (tarmaqlar boyinsha)
# ─────────────────────────────────────────────────────────────
def load_sanaat() -> pd.DataFrame:
    """
    Sanaat ónimleri kólemi tarmaqlar boyinsha (mlrd. som).
    """
    path = _find_file("sanaat ónimlerin islep")
    if path is None:
        raise FileNotFoundError("Sanaat fayl tabılmadı")

    raw = pd.read_excel(path, header=None)

    year_map = {}
    for ri in range(min(5, len(raw))):
        found = {}
        for ci, v in enumerate(raw.iloc[ri]):
            s = str(v).strip() if pd.notna(v) else ""
            if s.startswith("20"):
                try:
                    y = int(s[:4])
                    if 2010 <= y <= 2030:
                        found[ci] = y
                except ValueError:
                    pass
        if len(found) >= 8:
            year_map = found
            break

    records = {}
    for ri in range(len(raw)):
        row = raw.iloc[ri]
        label = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        if not label or label in ("nan",) or label.startswith("¹") or label.startswith("*"):
            continue
        vals = {}
        for ci, y in year_map.items():
            fv = _safe_float(row.iloc[ci])
            if fv is not None and fv > 0:
                vals[y] = fv
        if len(vals) >= 8:
            records[label[:70]] = vals

    df = pd.DataFrame(records).T
    df.index.name = "Tarmaqlaq"
    df.columns.name = "Jıl"
    return df


# ─────────────────────────────────────────────────────────────
#  5. JAO ÓSIM PÁTLERI
# ─────────────────────────────────────────────────────────────
def load_jao_growth() -> pd.DataFrame:
    """JAÓ ósim pátleri (%) tarmaqlar kesiminde."""
    path = _find_file("Jalpı aymaqlıq óniminiń ósim")
    if path is None:
        raise FileNotFoundError("JAÓ ósim páti fayl tabılmadı")

    raw = pd.read_excel(path, header=None)

    year_map = {}
    for ri in range(min(6, len(raw))):
        found = {}
        for ci, v in enumerate(raw.iloc[ri]):
            s = str(v).strip() if pd.notna(v) else ""
            if s.startswith("20") and "j." in s:
                try:
                    y = int(s[:4])
                    found[ci] = y
                except ValueError:
                    pass
        if len(found) >= 5:
            year_map = found
            break

    records = {}
    for ri in range(len(raw)):
        row = raw.iloc[ri]
        label = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        if not label or label in ("nan",) or label.startswith("*") or label.startswith("2018"):
            continue
        vals = {}
        for ci, y in year_map.items():
            fv = _safe_float(row.iloc[ci])
            if fv is not None and 80 < fv < 200:
                vals[y] = fv
        if len(vals) >= 5:
            records[label[:70]] = vals

    return pd.DataFrame(records).T


# ─────────────────────────────────────────────────────────────
#  6. XIZMETLER kólemi
# ─────────────────────────────────────────────────────────────
def load_services() -> pd.DataFrame:
    path = _find_file("Ekonomikalıq háreket túrleri boyınsha kórsetilgen xızmetler kólemi")
    if path is None:
        raise FileNotFoundError("Xızmetler fayl tabılmadı")

    raw = pd.read_excel(path, header=None)

    year_map = {}
    for ri in range(min(6, len(raw))):
        found = {}
        for ci, v in enumerate(raw.iloc[ri]):
            s = str(v).strip() if pd.notna(v) else ""
            if s.startswith("20") and "j." in s:
                try:
                    y = int(s[:4])
                    found[ci] = y
                except ValueError:
                    pass
        if len(found) >= 5:
            year_map = found
            break

    records = {}
    for ri in range(len(raw)):
        row = raw.iloc[ri]
        label = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        if not label or label in ("nan",) or label.startswith("*") or label.startswith("1)"):
            continue
        vals = {}
        for ci, y in year_map.items():
            raw_val = row.iloc[ci]
            s = str(raw_val).strip().replace(",", ".").replace(" ", "")
            try:
                fv = float(s)
                if fv > 0:
                    vals[y] = fv
            except (ValueError, TypeError):
                pass
        if len(vals) >= 5:
            records[label[:60]] = vals

    return pd.DataFrame(records).T
