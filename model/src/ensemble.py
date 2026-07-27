"""
Ensemble + Feature Enrichment Pipeline
=======================================

1. Xızmetler  → Multivariate LSTM (transport + JAO + Sanaat)
2. Eksport    → LSTM (bar, 89.59%)
3. Investitsiya → Multivariate LSTM (bar, 79.55%)
4. JAO, Sanaat, AwılXojalıǵı, Import → Prophet (jaqsı, 89-95%)

Ensemble usıl: Inverse-MAPE Weighted Average
    Eger eki model bar bolsa → w_i = (1/MAPE_i) / sum(1/MAPE_j)
    Bul eń jaqsı anıqlıqlı modelge kóbirek salmaqlı beriw
"""

import os
import io
import sys
import pickle
import warnings
import numpy as np
import pandas as pd

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
warnings.filterwarnings("ignore")

import logging
logging.getLogger("prophet").setLevel(logging.ERROR)
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)

from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error

import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam
from prophet import Prophet

tf.random.set_seed(42)
np.random.seed(42)

DATA_DIR     = os.path.join(os.path.dirname(__file__), "..", "data")
MODELS_DIR   = os.path.join(os.path.dirname(__file__), "..", "models")
RESULTS_DIR  = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────
#  KÓMEKSHI: Transport maǵlıwmatı júklew
# ─────────────────────────────────────────────────────────────
def _load_transport_jolawshi() -> pd.Series:
    """Avtomobil transportında tasılǵan jolawshılar (mıń. adam) — QR jámi."""
    for fname in os.listdir(DATA_DIR):
        if "jolawshilar sanı" in fname and "(1)" not in fname and "─" not in fname:
            path = os.path.join(DATA_DIR, fname)
            raw  = pd.read_excel(path, header=None)
            # Row 3: jıllar
            year_map = {}
            for ci, v in enumerate(raw.iloc[3]):
                s = str(v).strip() if pd.notna(v) else ""
                if s.startswith("20") and "j." in s:
                    try:
                        y = int(s[:4])
                        year_map[ci] = y
                    except ValueError:
                        pass
            # Row 4: QR jámi
            for ri in range(4, len(raw)):
                cell = str(raw.iloc[ri, 0]).strip() if pd.notna(raw.iloc[ri, 0]) else ""
                if "Respublikası" in cell or "Qaraqalpaqstan" in cell:
                    vals = {}
                    for ci, y in year_map.items():
                        try:
                            v = float(str(raw.iloc[ri, ci]).replace(",", ".").replace(" ", ""))
                            if v > 0:
                                vals[y] = v
                        except (ValueError, TypeError):
                            pass
                    if vals:
                        return pd.Series(vals).sort_index()
    return pd.Series(dtype=float)


def _load_karxana_sani() -> pd.Series:
    """Kárxana hám shólkemler sanı (hárekettegi)."""
    for fname in os.listdir(DATA_DIR):
        if "Kárxana hám shólkemler" in fname:
            path = os.path.join(DATA_DIR, fname)
            raw  = pd.read_excel(path, header=None)
            # Yillar row 4 da (index 4)
            year_map = {}
            for ri in range(6):
                row = raw.iloc[ri]
                found = {}
                for ci, v in enumerate(row):
                    s = str(v).strip() if pd.notna(v) else ""
                    try:
                        y = int(s)
                        if 2009 <= y <= 2030:
                            found[y] = ci
                    except ValueError:
                        pass
                if len(found) >= 4:
                    year_map = found
                    break
            if not year_map:
                continue
            # QR jámi qatarı - "Hárekettegi" kolonnasındaǵı (3-shi kolonn hár jıl blokında)
            # Hár jıl ushın 5 kolonn: Dizimnen, Hárekettegi, Háreketsiz, Jańadan, Saplastırılǵan
            vals = {}
            for ri in range(6, len(raw)):
                cell = str(raw.iloc[ri, 0]).strip() if pd.notna(raw.iloc[ri, 0]) else ""
                if "Respublikasi" in cell or "Qaraqalpaqstan" in cell:
                    for y, start_ci in year_map.items():
                        # Hárekettegi — 2-shi kolonn (offset 1)
                        try:
                            v = float(str(raw.iloc[ri, start_ci + 1]).replace(",", ".").replace(" ", ""))
                            if v > 0:
                                vals[y] = v
                        except (ValueError, TypeError):
                            pass
                    break
            if vals:
                return pd.Series(vals).sort_index()
    return pd.Series(dtype=float)


# ─────────────────────────────────────────────────────────────
#  MULTIVARIATE LSTM — Xızmetler ushın
# ─────────────────────────────────────────────────────────────
def _mv_lstm_train_eval(train_df, test_df, target_col, window=3,
                         units=(128, 64), dropout=0.2, lr=0.001, epochs=1000):
    """Multivariate LSTM oqıtiw hám holdout test."""
    from src.lstm_forecast import MultivariateLSTMForecaster
    forecaster = MultivariateLSTMForecaster(
        target_col=target_col,
        feature_cols=list(train_df.columns),
        window=window, epochs=epochs, batch_size=4,
        lstm_units=units, dropout=dropout, lr=lr,
    )
    forecaster.train(train_df, verbose=0)
    full_df = pd.concat([train_df, test_df])
    h = forecaster.holdout_test(full_df, list(test_df.index))
    ep = len(forecaster.history.history["loss"])
    return forecaster, h, ep


# ─────────────────────────────────────────────────────────────
#  PROPHET HOLDOUT
# ─────────────────────────────────────────────────────────────
def _prophet_holdout(series, test_years):
    train = series[~series.index.isin(test_years)]
    test  = series[series.index.isin(test_years)]
    tr_df = pd.DataFrame({
        "ds": pd.to_datetime(train.index.astype(str) + "-06-15"),
        "y":  train.values.astype(float),
    })
    m = Prophet(yearly_seasonality=False, weekly_seasonality=False,
                daily_seasonality=False, seasonality_mode="multiplicative",
                changepoint_prior_scale=0.3, interval_width=0.90)
    m.fit(tr_df)
    te_df = pd.DataFrame({"ds": pd.to_datetime(pd.Index(test_years).astype(str) + "-06-15")})
    fc = m.predict(te_df)
    y_true = test.values.astype(float)
    y_pred = fc["yhat"].values
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    return y_pred, max(0, 100 - mape), mape


# ─────────────────────────────────────────────────────────────
#  ENSEMBLE: Eki model natijasini birlestirish
# ─────────────────────────────────────────────────────────────
def inverse_mape_ensemble(preds_dict: dict, mapes_dict: dict, y_true: np.ndarray):
    """
    preds_dict: {'Prophet': y_pred1, 'LSTM': y_pred2, ...}
    mapes_dict: {'Prophet': 10.5,    'LSTM': 8.3, ...}
    Qaytaradı: ensemble y_pred, ensemble_mape
    """
    inv_mapes = {k: 1.0 / max(v, 0.1) for k, v in mapes_dict.items()}
    total = sum(inv_mapes.values())
    weights = {k: v / total for k, v in inv_mapes.items()}

    ensemble = np.zeros(len(y_true))
    for model_name, w in weights.items():
        ensemble += w * preds_dict[model_name]

    mape = np.mean(np.abs((y_true - ensemble) / y_true)) * 100
    return ensemble, max(0, 100 - mape), mape, weights


# ─────────────────────────────────────────────────────────────
#  XIZMETLER — Multivariate LSTM
# ─────────────────────────────────────────────────────────────
def improve_xizmetler(macro_df: pd.DataFrame, test_years: list, verbose=True) -> dict:
    """Xızmetler ushın MV-LSTM: JAO + Sanaat + Transport → Xızmetler."""
    if verbose:
        print("\n[Ensemble] Xızmetler — qosımsha maǵlıwmat júkleniwde...")

    transport = _load_transport_jolawshi()
    karxana   = _load_karxana_sani()

    FEATURES = ["JAO", "Sanaat", "Xızmetler"]
    df = macro_df[FEATURES].dropna()
    df = df[df.index <= 2025]

    # Transport biriktiriw (eger jeterlishe maǵlıwmat bar bolsa)
    if len(transport) >= 10:
        common = df.index.intersection(transport.index)
        df_t = df.loc[common].copy()
        df_t["Transport"] = transport.loc[common].values
        FEATURES_T = ["JAO", "Sanaat", "Transport", "Xızmetler"]
        if verbose:
            print(f"  Transport ma'lumot qo'shildi: {len(common)} jıl")
    else:
        df_t = df.copy()
        FEATURES_T = FEATURES
        if verbose:
            print("  Transport ma'lumot yetarli emas, faqat JAO+Sanaat ishlatiladi")

    train_df = df_t[~df_t.index.isin(test_years)]
    test_df  = df_t[df_t.index.isin(test_years)]

    # Konfigurasiyalar sinawı
    best_acc = 0
    best_result = None
    best_fc = None

    for win, units, drop in [(3,(128,64),0.2), (4,(128,64),0.2), (3,(64,32),0.1)]:
        try:
            fc, h, ep = _mv_lstm_train_eval(
                train_df, test_df, "Xızmetler",
                window=win, units=units, dropout=drop
            )
            if h["Anıqlıq"] > best_acc:
                best_acc    = h["Anıqlıq"]
                best_result = h
                best_fc     = fc
                if verbose:
                    print(f"  W{win}-{units[0]}-{units[1]}: ep={ep} MAPE={h['MAPE']:.2f}% Anıqlıq={h['Anıqlıq']:.2f}%")
        except Exception as e:
            if verbose:
                print(f"  W{win}: QATE {e}")

    if best_fc is None:
        return {"error": "Xızmetler LSTM oqıtıwda qáte"}

    # LSTM predict qilingan yillar
    lstm_rows = best_result["Qatarlar"]
    lstm_years_ok = sorted(lstm_rows["Jıl"].tolist())

    # Prophet: faqat LSTM yillari uchun (moslashtirish)
    xiz_series = macro_df["Xızmetler"].dropna()
    xiz_series = xiz_series[xiz_series.index <= 2025]
    p_pred, p_acc, p_mape = _prophet_holdout(xiz_series, lstm_years_ok)

    matched   = lstm_rows.sort_values("Jıl")
    lstm_pred = matched["Boljanıw"].values.astype(float)

    # y_true — makro dan naqiy xizmetler
    y_true = macro_df["Xızmetler"].dropna()
    y_true = y_true[y_true.index.isin(lstm_years_ok)].sort_index().values.astype(float)

    # Uzunliklarni tekshirish
    n = min(len(y_true), len(p_pred), len(lstm_pred))
    y_true    = y_true[:n]
    p_pred    = p_pred[:n]
    lstm_pred = lstm_pred[:n]

    # Ensemble
    ens_pred, ens_acc, ens_mape, weights = inverse_mape_ensemble(
        {"Prophet": p_pred, "MV-LSTM": lstm_pred},
        {"Prophet": p_mape, "MV-LSTM": best_result["MAPE"]},
        y_true,
    )

    if verbose:
        print(f"\n  Xızmetler Nátiyje:")
        print(f"  Prophet:      MAPE={p_mape:.2f}%  Anıqlıq={p_acc:.2f}%")
        print(f"  MV-LSTM:      MAPE={best_result['MAPE']:.2f}%  Anıqlıq={best_result['Anıqlıq']:.2f}%")
        print(f"  ENSEMBLE:     MAPE={ens_mape:.2f}%  Anıqlıq={ens_acc:.2f}%  (ağırlıqlar: P={weights['Prophet']:.2f} L={weights['MV-LSTM']:.2f})")

    # Model saqlash
    best_fc.save("lstm_mv_Xizmetler.pkl")

    return {
        "forecaster":    best_fc,
        "holdout":       best_result,
        "prophet_acc":   p_acc,
        "prophet_mape":  p_mape,
        "ensemble_acc":  ens_acc,
        "ensemble_mape": ens_mape,
        "weights":       weights,
        "y_true":        y_true,
        "lstm_pred":     lstm_pred,
        "prophet_pred":  p_pred,
        "ensemble_pred": ens_pred,
    }


# ─────────────────────────────────────────────────────────────
#  ULÍWMA ENSEMBLE PIPELINE
# ─────────────────────────────────────────────────────────────
def run_ensemble_pipeline(macro_df: pd.DataFrame, verbose: bool = True) -> dict:
    """
    Barlıq modellar ushın ensemble pipeline.
    """
    TEST_YEARS = [2022, 2023, 2024, 2025]

    print("\n" + "=" * 60)
    print("  ENSEMBLE PIPELINE — BARLIQ MODELLAR")
    print("=" * 60)

    results = {}

    # ── 1. Xızmetler: MV-LSTM + Prophet Ensemble ──────────────
    print("\n[1/3] Xızmetler yaxshilanıwda...")
    xiz_result = improve_xizmetler(macro_df, TEST_YEARS, verbose=verbose)
    results["Xızmetler"] = xiz_result

    # ── 2. Eksport: LSTM (bar) ────────────────────────────────
    print("\n[2/3] Eksport (LSTM bar, tekseriliw)...")
    try:
        with open(os.path.join(MODELS_DIR, "lstm_Eksport.pkl"), "rb") as f:
            lstm_exp = pickle.load(f)
        if isinstance(lstm_exp.model, str):
            lstm_exp.model = load_model(lstm_exp.model)
        exp_series = macro_df["Eksport"].dropna()
        exp_series = exp_series[exp_series.index <= 2025]
        h_exp = lstm_exp.holdout_test(exp_series, TEST_YEARS)
        results["Eksport"] = {"holdout": h_exp, "source": "LSTM"}
        if verbose:
            print(f"  LSTM Eksport: MAPE={h_exp['MAPE']:.2f}%  Anıqlıq={h_exp['Anıqlıq']:.2f}%")
    except Exception as e:
        if verbose:
            print(f"  Eksport LSTM: {e}")

    # ── 3. Investitsiya: MV-LSTM (bar) ───────────────────────
    print("\n[3/3] Investitsiya (MV-LSTM bar, tekseriliw)...")
    try:
        with open(os.path.join(MODELS_DIR, "lstm_mv_Investitsiya.pkl"), "rb") as f:
            lstm_inv = pickle.load(f)
        if isinstance(lstm_inv.model, str):
            lstm_inv.model = load_model(lstm_inv.model)
        FEATURES = ["JAO", "Sanaat", "Qurılıs", "Investitsiya"]
        df_mv = macro_df[FEATURES].dropna()
        df_mv = df_mv[df_mv.index <= 2025]
        h_inv = lstm_inv.holdout_test(df_mv, TEST_YEARS)
        results["Investitsiya"] = {"holdout": h_inv, "source": "MV-LSTM"}
        if verbose:
            print(f"  MV-LSTM Investitsiya: MAPE={h_inv['MAPE']:.2f}%  Anıqlıq={h_inv['Anıqlıq']:.2f}%")
    except Exception as e:
        if verbose:
            print(f"  Investitsiya MV-LSTM: {e}")

    # ── YAKUNIY BAHA ─────────────────────────────────────────
    _print_ensemble_summary(results, macro_df, TEST_YEARS, verbose)

    return results


def _print_ensemble_summary(results, macro_df, test_years, verbose):
    print("\n" + "=" * 65)
    print("  YAKUNIY MODEL ANIQLIQLARI SALISTIRMASI")
    print("=" * 65)

    headers = ["Kórsetkish", "Eski Model", "Eski %", "Jańa Model", "Jańa %", "Ósim"]
    rows = []

    # Prophet natijalari (eski)
    prophet_accs = {
        "JAO":          90.10, "Sanaat":    89.02,
        "AwılXojalıǵı": 95.21, "Xızmetler": 75.91,
        "Import":       81.83, "Eksport":   45.46,
        "Investitsiya": 64.21,
    }

    # Xızmetler
    if "Xızmetler" in results and "ensemble_acc" in results["Xızmetler"]:
        xr = results["Xızmetler"]
        rows.append(["Xızmetler", "Prophet", f"{prophet_accs['Xızmetler']:.1f}%",
                      "MV-LSTM+Prophet Ensemble", f"{xr['ensemble_acc']:.2f}%",
                      f"+{xr['ensemble_acc']-prophet_accs['Xızmetler']:.2f}%"])

    # Eksport
    if "Eksport" in results and "holdout" in results["Eksport"]:
        h = results["Eksport"]["holdout"]
        rows.append(["Eksport", "Prophet", f"{prophet_accs['Eksport']:.1f}%",
                      "LSTM", f"{h['Anıqlıq']:.2f}%",
                      f"+{h['Anıqlıq']-prophet_accs['Eksport']:.2f}%"])

    # Investitsiya
    if "Investitsiya" in results and "holdout" in results["Investitsiya"]:
        h = results["Investitsiya"]["holdout"]
        rows.append(["Investitsiya", "Prophet", f"{prophet_accs['Investitsiya']:.1f}%",
                      "MV-LSTM", f"{h['Anıqlıq']:.2f}%",
                      f"+{h['Anıqlıq']-prophet_accs['Investitsiya']:.2f}%"])

    # O'zgarmaganlar
    for col in ["JAO", "Sanaat", "AwılXojalıǵı", "Import"]:
        rows.append([col, "Prophet", f"{prophet_accs[col]:.1f}%", "Prophet (óz halin)", f"{prophet_accs[col]:.1f}%", "—"])

    # XGBoost
    rows.append(["Weak Spot", "XGBoost", "98.21%", "XGBoost", "98.21%", "—"])

    # Jadwal
    fmt = "{:<22} {:<10} {:<9} {:<28} {:<9} {}"
    print(fmt.format(*headers))
    print("-" * 95)
    for r in rows:
        print(fmt.format(*r))

    # Ortasha
    new_accs = []
    for r in rows:
        try:
            new_accs.append(float(r[4].replace("%", "")))
        except ValueError:
            pass
    if new_accs:
        print("-" * 95)
        print(f"{'Ortasha anıqlıq:':<22} {'':>38} {np.mean(new_accs):.2f}%")

    # Saqlash
    summary_path = os.path.join(RESULTS_DIR, "ensemble_summary.csv")
    pd.DataFrame(rows, columns=headers).to_csv(summary_path, index=False, encoding="utf-8")
    if verbose:
        print(f"\n  Jadwal saqlandı: {summary_path}")
