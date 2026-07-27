"""
Birlesken Pipeline
==================

    Weak Spot ML      Forecast ML
    (XGBoost)         (Prophet)
          │              │
          └──────┬───────┘
                 ▼
         Juwmaq Analiz Nátiyjesi

Barlıq maǵlıwmat júklew → oqitiw → boljanıw → nátiyje jadwalları
"""

import os
import io
import sys
import json
import warnings
from datetime import datetime

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

if sys.platform == "win32" and not isinstance(sys.stdout, io.TextIOWrapper):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except AttributeError:
        pass

from .data_loader import (
    load_macro,
    load_rayon_unemployment,
    load_salary,
    load_jao_growth,
    load_services,
    load_sanaat,
)
from .weak_spot import run_weak_spot, LABEL_NAMES
from .forecast import run_forecasts, run_salary_forecast
from .lstm_forecast import run_lstm_export, compare_prophet_vs_lstm

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────
#  BASLAWSHI PIPELINE
# ─────────────────────────────────────────────────────────────
def run_pipeline(verbose: bool = True) -> dict:
    """
    Tolıq ML pipeline júrgiziw.

    Qaytaradı:
        {
          "macro":          pd.DataFrame,
          "unemp":          pd.DataFrame,
          "weak_spot":      dict  (WeakSpot nátiyjeleri),
          "forecasts":      dict  (Prophet nátiyjeleri),
          "salary_fc":      dict  (Is haqı boljanıwı),
          "combined_report": dict (juwmaq),
        }
    """
    sep = "=" * 60

    print(sep)
    print("  QARAQALPAQSTAN EKONOMIKA ML PIPELINE")
    print(f"  Baslanǵan waqıt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(sep)

    # ── 1. MAǴLÍWMAT JÚKLEW ──────────────────────────────────
    print("\n[1/5] Maǵlıwmatlar júkleniwde...")

    try:
        macro_df = load_macro()
        print(f"  ✓ Makroekonomika: {macro_df.shape[0]} jıl, {macro_df.shape[1]} kórsetkish")
    except Exception as e:
        print(f"  ✗ Makroekonomika: {e}")
        macro_df = pd.DataFrame()

    try:
        unemp_df = load_rayon_unemployment()
        print(f"  ✓ Jumıssızlıq: {unemp_df.shape[0]} qator ({unemp_df['Rayon'].nunique()} rayon)")
    except Exception as e:
        print(f"  ✗ Jumıssızlıq: {e}")
        unemp_df = pd.DataFrame()

    try:
        salary_df = load_salary()
        print(f"  ✓ Is haqı: {salary_df.shape[0]} tármaqlaq, {salary_df.shape[1]} kvartal")
    except Exception as e:
        print(f"  ✗ Is haqı: {e}")
        salary_df = pd.DataFrame()

    try:
        sanaat_df = load_sanaat()
        print(f"  ✓ Sanaat: {sanaat_df.shape[0]} tármaqlaq")
    except Exception as e:
        print(f"  ✗ Sanaat: {e}")
        sanaat_df = pd.DataFrame()

    # ── 2. WEAK SPOT (XGBoost) ───────────────────────────────
    print(f"\n[2/5] Weak Spot ML (XGBoost) oqitılıwda...")
    ws_results = {}
    if not unemp_df.empty:
        ws_results = run_weak_spot(unemp_df, verbose=verbose)
    else:
        print("  ✗ Jumıssızlıq maǵlıwmatı joq — Weak Spot ótip ketildi")

    # ── 3. FORECAST (Prophet) ─────────────────────────────────
    print(f"\n[3/5] Forecast ML (Prophet) oqitılıwda...")
    fc_results = {}
    if not macro_df.empty:
        fc_results = run_forecasts(macro_df, verbose=verbose)
    else:
        print("  ✗ Makro maǵlıwmat joq — Forecast ótip ketildi")

    # ── 4. LSTM — EKSPORT BOLJANIWI ──────────────────────────
    print(f"\n[4/6] LSTM — Eksport modeli oqitılıwda...")
    lstm_result = {}
    if not macro_df.empty and "Eksport" in macro_df.columns:
        import os as _os
        _os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
        lstm_result = run_lstm_export(
            macro_df=macro_df,
            target_col="Eksport",
            test_years=[2022, 2023, 2024, 2025],
            forecast_periods=5,
            verbose=verbose,
        )
        if fc_results and "__combined__" in fc_results and lstm_result:
            cmp_df, summary = compare_prophet_vs_lstm(
                macro_df=macro_df,
                lstm_result=lstm_result,
                target_col="Eksport",
            )
            if verbose:
                print("\n  Prophet vs LSTM:")
                print(summary.to_string(index=False))
    else:
        print("  ✗ Eksport maǵlıwmatı joq")

    # ── 5. IS HAQI BOLJANIWI ─────────────────────────────────
    print(f"\n[5/6] Is haqı kvartal boljanıwı...")
    salary_fc = {}
    if not salary_df.empty:
        salary_fc = run_salary_forecast(salary_df, verbose=verbose)
    else:
        print("  ✗ Is haqı maǵlıwmatı joq")

    # ── 6. BIRLESKEN NÁTIYJE ─────────────────────────────────
    print(f"\n[6/6] Nátiyje jadwalları tayarlanıwda...")
    combined = _build_combined_report(
        macro_df, unemp_df, ws_results, fc_results, salary_fc, lstm_result
    )
    _save_results(combined, ws_results, fc_results, lstm_result)

    print(f"\n{sep}")
    print("  PIPELINE TAMAMLANDÍ")
    print(sep)

    _print_summary(combined, ws_results, fc_results)

    return {
        "macro": macro_df,
        "unemp": unemp_df,
        "salary": salary_df,
        "weak_spot": ws_results,
        "forecasts": fc_results,
        "salary_fc": salary_fc,
        "lstm": lstm_result,
        "combined_report": combined,
    }


# ─────────────────────────────────────────────────────────────
#  BIRLESKEN NÁTIYJE QURIW
# ─────────────────────────────────────────────────────────────
def _build_combined_report(macro_df, unemp_df, ws_results, fc_results, salary_fc, lstm_result=None) -> dict:
    report = {}

    # ── A. Makro suwreti ──────────────────────────────────────
    if not macro_df.empty:
        last_year = macro_df.index.max()
        last = macro_df.loc[last_year]
        report["macro_songi_jil"] = {
            "Jıl": int(last_year),
            "kórsetkishler": {
                col: float(round(last[col], 2))
                for col in macro_df.columns
                if pd.notna(last.get(col))
            }
        }

    # ── B. Eń qauipli rayonlar ───────────────────────────────
    if ws_results and "latest" in ws_results:
        latest = ws_results["latest"]
        qauipli = latest[latest["Boljanıw"] == "Qauipli"][
            ["Rayon", "JumıssızlıqPáti", "Boljanıw", "P_Qauipli"]
        ].to_dict("records")
        ortasha = latest[latest["Boljanıw"] == "Ortasha"][
            ["Rayon", "JumıssızlıqPáti", "Boljanıw", "P_Ortasha"]
        ].to_dict("records")
        report["weak_spot_rayonlar"] = {
            "Qauipli": qauipli,
            "Ortasha": ortasha,
        }

    # ── C. Boljanıw nátiyjeleri ──────────────────────────────
    if "__combined__" in fc_results:
        combined_fc = fc_results["__combined__"]
        forecast_dict = {}
        for _, row in combined_fc.iterrows():
            kor = row["Kórsetkish"]
            jil = int(row["Jıl"])
            if kor not in forecast_dict:
                forecast_dict[kor] = {}
            forecast_dict[kor][jil] = {
                "boljanıw": round(float(row["Boljanıw"]), 2),
                "min": round(float(row["TómenShegara"]), 2),
                "max": round(float(row["JoqarıShegara"]), 2),
            }
        report["boljanıw"] = forecast_dict

    # ── D. Feature importance ────────────────────────────────
    if ws_results and "feature_importance" in ws_results:
        fi = ws_results["feature_importance"]
        report["feature_importance"] = fi.to_dict()

    # ── E. CV kórsetkishi ────────────────────────────────────
    if ws_results and "cv_scores" in ws_results:
        cv = ws_results["cv_scores"]
        report["model_dárejesi"] = {
            "CV_F1_macro_ortasha": round(float(cv.mean()), 4),
            "CV_F1_macro_std": round(float(cv.std()), 4),
        }

    # ── F. LSTM Eksport ───────────────────────────────────────
    if lstm_result and "holdout" in lstm_result and "forecast_df" in lstm_result:
        h = lstm_result["holdout"]
        report["lstm_eksport"] = {
            "holdout_MAPE":    h.get("MAPE"),
            "holdout_R2":      h.get("R2"),
            "holdout_Anıqlıq": h.get("Anıqlıq"),
            "holdout_PI":      h.get("PI_qamraw"),
            "boljanıw": {
                int(row["Jıl"]): {
                    "boljanıw": float(row["Boljanıw"]),
                    "min": float(row["TómenShegara"]),
                    "max": float(row["JoqarıShegara"]),
                }
                for _, row in lstm_result["forecast_df"].iterrows()
            },
        }

    return report


# ─────────────────────────────────────────────────────────────
#  NÁTIYJE SAQLAWSHÍ
# ─────────────────────────────────────────────────────────────
def _save_results(combined, ws_results, fc_results, lstm_result=None):
    # 1. Juwmaq JSON
    try:
        json_path = os.path.join(RESULTS_DIR, "combined_report.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Juwmaq JSON: {json_path}")
    except Exception as e:
        print(f"  ✗ JSON saqlawda qáte: {e}")

    # 2. Weak Spot nátiyjeleri CSV
    if ws_results and "result_df" in ws_results:
        try:
            csv_path = os.path.join(RESULTS_DIR, "weak_spot_results.csv")
            ws_results["result_df"].to_csv(csv_path, index=False, encoding="utf-8")
            print(f"  ✓ Weak Spot CSV: {csv_path}")
        except Exception as e:
            print(f"  ✗ Weak Spot CSV: {e}")

    # 3. LSTM Eksport boljanıwı CSV
    if lstm_result and "forecast_df" in lstm_result:
        try:
            csv_path = os.path.join(RESULTS_DIR, "lstm_Eksport_forecast.csv")
            lstm_result["forecast_df"].to_csv(csv_path, index=False, encoding="utf-8")
            print(f"  ✓ LSTM Eksport CSV: {csv_path}")
        except Exception as e:
            print(f"  ✗ LSTM CSV: {e}")

    # 4. Boljanıw nátiyjeleri CSV
    if "__combined__" in fc_results:
        try:
            csv_path = os.path.join(RESULTS_DIR, "forecast_combined.csv")
            fc_results["__combined__"].to_csv(csv_path, index=False, encoding="utf-8")
            print(f"  ✓ Boljanıw CSV: {csv_path}")
        except Exception as e:
            print(f"  ✗ Boljanıw CSV: {e}")


# ─────────────────────────────────────────────────────────────
#  TERMINAL NÁTIYJE SHIǴARIWSHÍ
# ─────────────────────────────────────────────────────────────
def _print_summary(combined: dict, ws_results: dict, fc_results: dict):
    print("\n" + "─" * 60)
    print("  JUWMAQ NÁTIYJE")
    print("─" * 60)

    # Model dárejesi
    if "model_dárejesi" in combined:
        md = combined["model_dárejesi"]
        print(f"\n  [XGBoost] CV F1-macro: {md['CV_F1_macro_ortasha']:.3f} ± {md['CV_F1_macro_std']:.3f}")

    # Qauipli rayonlar
    if "weak_spot_rayonlar" in combined:
        qr = combined["weak_spot_rayonlar"]
        if qr["Qauipli"]:
            print(f"\n  [QAUIPLI RAYONLAR] ({len(qr['Qauipli'])} rayon):")
            for r in qr["Qauipli"]:
                print(f"    • {r['Rayon']}: jumıssızlıq {r['JumıssızlıqPáti']:.1f}%")
        if qr["Ortasha"]:
            print(f"\n  [ORTASHA RAYONLAR] ({len(qr['Ortasha'])} rayon):")
            for r in qr["Ortasha"]:
                print(f"    • {r['Rayon']}: jumıssızlıq {r['JumıssızlıqPáti']:.1f}%")

    # Boljanıw — JAO
    if "boljanıw" in combined and "JAO" in combined["boljanıw"]:
        jao_fc = combined["boljanıw"]["JAO"]
        print(f"\n  [PROPHET] JAÓ Boljanıwı:")
        for jil in sorted(jao_fc.keys()):
            v = jao_fc[jil]
            print(f"    {jil}: {v['boljanıw']:,.1f} mlrd. som"
                  f"  [{v['min']:,.1f} — {v['max']:,.1f}]")

    # LSTM Eksport
    if "lstm_eksport" in combined:
        le = combined["lstm_eksport"]
        print(f"\n  [LSTM] Eksport Holdout Anıqlıǵı: {le['holdout_Anıqlıq']}%"
              f"  (MAPE:{le['holdout_MAPE']}%  PI:{le['holdout_PI']})")
        print(f"  [LSTM] Eksport Boljanıwı:")
        for jil, v in le["boljanıw"].items():
            print(f"    {jil}: {v['boljanıw']:,.1f} mln.$  [{v['min']:,.1f} — {v['max']:,.1f}]")

    # Feature importance — top 3
    if "feature_importance" in combined:
        fi = combined["feature_importance"]
        sorted_fi = sorted(fi.items(), key=lambda x: x[1], reverse=True)
        print(f"\n  [XGBoost] Eń tásirli faktorlar:")
        for i, (feat, imp) in enumerate(sorted_fi[:5], 1):
            print(f"    {i}. {feat}: {imp:.4f}")

    print("\n" + "─" * 60)
    print("  Barlıq nátiyje 'results/' papkasında saqlandı")
    print("─" * 60)
