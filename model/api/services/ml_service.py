"""
ML Service — XGBoost + Prophet/LSTM modellarini ishga tushirish
"""

import os, sys, pickle, warnings, json
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, ROOT)
MODELS_DIR = os.path.join(ROOT, "models")

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"


# ─────────────────────────────────────────────────────────────
#  MODEL YUKLAW (bir marta startup da)
# ─────────────────────────────────────────────────────────────
_ws_model      = None   # XGBoost
_prophet_models = {}    # Prophet {col: model}
_lstm_models    = {}    # LSTM {col: model}


def _load_models():
    global _ws_model, _prophet_models, _lstm_models

    # XGBoost
    ws_path = os.path.join(MODELS_DIR, "weak_spot_model.pkl")
    if os.path.exists(ws_path):
        with open(ws_path, "rb") as f:
            _ws_model = pickle.load(f)

    # Prophet
    for col in ["JAO","Sanaat","AwılXojalıǵı","Investitsiya",
                "Eksport","Import","Xızmetler","Qurılıs"]:
        path = os.path.join(MODELS_DIR, f"prophet_{col}.pkl")
        if os.path.exists(path):
            with open(path, "rb") as f:
                _prophet_models[col] = pickle.load(f)

    # LSTM
    from tensorflow.keras.models import load_model as keras_load
    for fname, key in [("lstm_Eksport.pkl","Eksport"),
                       ("lstm_mv_Investitsiya.pkl","Investitsiya"),
                       ("lstm_mv_Xizmetler.pkl","Xızmetler")]:
        path = os.path.join(MODELS_DIR, fname)
        if os.path.exists(path):
            with open(path, "rb") as f:
                m = pickle.load(f)
            if isinstance(m.model, str):
                m.model = keras_load(m.model)
            _lstm_models[key] = m

    print(f"[ML] Modeller yuklandi: XGBoost={_ws_model is not None}, "
          f"Prophet={len(_prophet_models)}, LSTM={len(_lstm_models)}")


# ─────────────────────────────────────────────────────────────
#  WEAK SPOT DETECTION
# ─────────────────────────────────────────────────────────────
LABEL_NAMES = {0: "Jaqsı", 1: "Ortasha", 2: "Qauipli"}
FEATURE_COLS = [
    "JumıssızlıqPáti","Jumıssız_YılÓzg","Jumıssız_2YılÓzg",
    "BántlerUles","JumıssızUles","Bántler_YılÓzg",
    "AktivXalıq_YılÓzg","AktivXalıq","JılKód","RayonKód",
]


def detect_weak_spots(df_unemp: pd.DataFrame) -> list:
    """
    Rayon jumıssızlıq maǵlıwmatınan weak spot anıqlaw.
    Qaytaradı: [{rayon, jil, status, prob_qauipli, jumissizliq_pati}]
    """
    if _ws_model is None:
        return []

    from src.weak_spot import build_features
    df_feat, _ = build_features(df_unemp)
    avail = [c for c in FEATURE_COLS if c in df_feat.columns]
    X = df_feat[avail].values

    preds = _ws_model.model.predict(X)
    proba = _ws_model.model.predict_proba(X)

    results = []
    for i, row in df_feat.iterrows():
        results.append({
            "rayon":          row["Rayon"],
            "jil":            int(row["Jıl"]),
            "status":         LABEL_NAMES[preds[i]],
            "prob_jaqsi":     round(float(proba[i][0]), 3),
            "prob_ortasha":   round(float(proba[i][1]), 3),
            "prob_qauipli":   round(float(proba[i][2]), 3),
            "jumissizliq_pati": round(float(row["JumıssızlıqPáti"]), 2),
            "aktiv_xaliq":    round(float(row["AktivXalıq"]), 1),
            "bantler":        round(float(row["Bántler"]), 1),
        })
    return results


def get_critical_regions(year: int = None) -> list:
    """Eń qauipli rayonlar ro'yhati."""
    from src.data_loader import load_rayon_unemployment
    df = load_rayon_unemployment()
    if year:
        df = df[df["Jıl"] == year]
    all_results = detect_weak_spots(df)
    critical = [r for r in all_results if r["status"] in ("Qauipli", "Ortasha")]
    return sorted(critical, key=lambda x: x["prob_qauipli"], reverse=True)


# ─────────────────────────────────────────────────────────────
#  FORECAST
# ─────────────────────────────────────────────────────────────
def get_forecast(indicator: str, periods: int = 5) -> list:
    """
    Kórsetkish ushın keleshek boljanıwı.
    Qaytaradı: [{jil, boljanıw, tomen, joqarı}]
    """
    # LSTM (eń jaqsı model)
    if indicator in _lstm_models:
        try:
            m = _lstm_models[indicator]
            # LSTMForecaster — periods argument qabul qiladi
            from src.lstm_forecast import LSTMForecaster
            if isinstance(m, LSTMForecaster):
                fc = m.forecast(periods=periods)
                return fc.to_dict("records")
            # MultivariateLSTMForecaster — Prophet ga fallback
        except Exception:
            pass

    # Prophet (zaxira)
    if indicator in _prophet_models:
        m = _prophet_models[indicator]
        fc = m.forecast(periods=periods)
        return [
            {
                "Jıl":          int(r["Jıl"]),
                "Kórsetkish":   r["Kórsetkish"],
                "Boljanıw":     round(r["Boljanıw"], 2),
                "TómenShegara": round(r["TómenShegara"], 2),
                "JoqarıShegara":round(r["JoqarıShegara"], 2),
            }
            for _, r in fc.iterrows()
        ]
    return []


def get_all_forecasts(periods: int = 5) -> dict:
    """Barlıq kórsetkishler ushın boljanıwlar."""
    result = {}
    for col in ["JAO","Sanaat","AwılXojalıǵı","Investitsiya",
                "Eksport","Import","Xızmetler"]:
        fc = get_forecast(col, periods)
        if fc:
            result[col] = fc
    return result


# ─────────────────────────────────────────────────────────────
#  DB MAǴLÍWMATLARDAN ANALIZ
# ─────────────────────────────────────────────────────────────
def analyze_db_indicators(indicators: list) -> dict:
    """
    Admin kiritgan ko'rsatkichlarni (DB dan keladi) tahlil qiladi.
    indicators: [{module, region, kpi_planned, kpi_actual, year, ...}]
    Qaytaradı: {summary, weak_spots, recommendations}
    """
    if not indicators:
        return {"error": "Maǵlıwmat joq"}

    df = pd.DataFrame(indicators)
    results = {"modules": {}, "regions": {}, "critical": []}

    # Modul boyinsha tahlil
    for module, grp in df.groupby("module"):
        planned = grp["kpi_planned"].dropna()
        actual  = grp["kpi_actual"].dropna()
        if len(planned) > 0 and len(actual) > 0:
            completion = (actual.mean() / planned.mean() * 100) if planned.mean() != 0 else 0
            results["modules"][module] = {
                "ortasha_rejalan": round(float(planned.mean()), 2),
                "ortasha_amalda":  round(float(actual.mean()), 2),
                "orindalish":      round(completion, 1),
                "status":          _completion_status(completion),
            }

    # Rayon boyinsha tahlil
    for region, grp in df.groupby("region"):
        planned = grp["kpi_planned"].dropna()
        actual  = grp["kpi_actual"].dropna()
        if len(planned) > 0 and len(actual) > 0:
            completion = (actual.mean() / planned.mean() * 100) if planned.mean() != 0 else 0
            results["regions"][region] = {
                "orindalish": round(completion, 1),
                "status":     _completion_status(completion),
            }
            if completion < 80:
                results["critical"].append({
                    "region": region,
                    "orindalish": round(completion, 1),
                    "status": _completion_status(completion),
                })

    results["critical"] = sorted(
        results["critical"], key=lambda x: x["orindalish"]
    )
    return results


def _completion_status(pct: float) -> str:
    if pct >= 95:   return "completed"
    if pct >= 80:   return "in_progress"
    if pct >= 60:   return "at_risk"
    return "critical"


# ─────────────────────────────────────────────────────────────
#  STARTUP
# ─────────────────────────────────────────────────────────────
def startup():
    _load_models()
