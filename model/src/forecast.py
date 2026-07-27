"""
Forecast ML — Prophet
Tiykarǵı ekonomikalıq kórsetkishlerdi boljalaw ushın.

Boljanıw nısaw: 2026–2031 jıllar
Kórsetkishler: JAO, Sanaat, AwılXojalıǵı, Investitsiya,
               Qurılıs, Eksport, Import, Xızmetler
"""

import os
import pickle
import warnings
from typing import Optional

import numpy as np
import pandas as pd
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics

warnings.filterwarnings("ignore")
import logging
logging.getLogger("prophet").setLevel(logging.ERROR)
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# Boljanıw jılları sanı
FORECAST_YEARS = 5
FORECAST_PERIODS = FORECAST_YEARS  # jıllıq maǵlıwmat ushın


# ─────────────────────────────────────────────────────────────
#  PROPHET ushın maǵlıwmat tayarlawshı
# ─────────────────────────────────────────────────────────────
def _to_prophet_df(series: pd.Series) -> pd.DataFrame:
    """
    pd.Series (index=jıl) → Prophet {ds, y} DataFrame.
    """
    df = pd.DataFrame({
        "ds": pd.to_datetime(series.index.astype(str) + "-06-15"),
        "y": series.values.astype(float),
    })
    df = df.dropna(subset=["y"])
    df = df[np.isfinite(df["y"])]
    return df.reset_index(drop=True)


# ─────────────────────────────────────────────────────────────
#  HÁRTARAFLAMA Prophet OQITIW
# ─────────────────────────────────────────────────────────────
class EconomicForecaster:
    def __init__(self, corsetkish_ati: str, yearly_seasonality: bool = False):
        self.corsetkish_ati = corsetkish_ati
        self.model = Prophet(
            yearly_seasonality=yearly_seasonality,
            weekly_seasonality=False,
            daily_seasonality=False,
            seasonality_mode="multiplicative",
            changepoint_prior_scale=0.3,
            interval_width=0.90,
        )
        self.prophet_df = None
        self.forecast_df = None
        self.is_trained = False

    def train(self, series: pd.Series):
        """
        series: pd.Series, index=jıl (int), values=kórsetkish mánisi
        """
        self.prophet_df = _to_prophet_df(series)
        if len(self.prophet_df) < 3:
            raise ValueError(f"{self.corsetkish_ati}: az maǵlıwmat ({len(self.prophet_df)} qator)")
        self.model.fit(self.prophet_df)
        self.is_trained = True

    def forecast(self, periods: int = FORECAST_PERIODS) -> pd.DataFrame:
        """Keleshek períodlar ushın boljanıw."""
        if not self.is_trained:
            raise RuntimeError("Model aldi oqitilsin")

        last_year = self.prophet_df["ds"].dt.year.max()
        future_dates = pd.date_range(
            start=f"{last_year + 1}-06-15",
            periods=periods,
            freq="YS",
        )
        future_df = pd.DataFrame({"ds": future_dates})

        # Tarixiy + keleshek
        all_future = pd.concat([self.prophet_df[["ds"]], future_df], ignore_index=True)
        raw_fc = self.model.predict(all_future)

        # Tek keleshek qatarlar
        fc = raw_fc[raw_fc["ds"].dt.year > last_year].copy()
        fc["Jıl"] = fc["ds"].dt.year
        fc["Kórsetkish"] = self.corsetkish_ati

        cols = ["Jıl", "Kórsetkish", "yhat", "yhat_lower", "yhat_upper"]
        fc_clean = fc[cols].rename(columns={
            "yhat": "Boljanıw",
            "yhat_lower": "TómenShegara",
            "yhat_upper": "JoqarıShegara",
        })

        self.forecast_df = fc_clean.reset_index(drop=True)
        return self.forecast_df

    def get_trend(self) -> pd.DataFrame:
        """Tiykarǵı trend (tarixiy + boljanıw)."""
        if not self.is_trained:
            raise RuntimeError("Model aldi oqitilsin")
        all_df = pd.concat([self.prophet_df[["ds"]], pd.DataFrame({
            "ds": pd.date_range(
                start=str(self.prophet_df["ds"].dt.year.max() + 1) + "-06-15",
                periods=FORECAST_PERIODS, freq="YS"
            )
        })], ignore_index=True)
        raw = self.model.predict(all_df)
        raw["Jıl"] = raw["ds"].dt.year
        return raw[["Jıl", "trend", "yhat"]].rename(
            columns={"trend": "Trend", "yhat": "Boljanıw"}
        )

    def save(self, fname: Optional[str] = None):
        fname = fname or f"prophet_{self.corsetkish_ati.replace(' ', '_')}.pkl"
        path = os.path.join(MODELS_DIR, fname)
        with open(path, "wb") as f:
            pickle.dump(self, f)
        return path

    @classmethod
    def load(cls, fname: str):
        path = os.path.join(MODELS_DIR, fname)
        with open(path, "rb") as f:
            return pickle.load(f)


# ─────────────────────────────────────────────────────────────
#  BARLIQ KÓRSETKISHLER USHIN PIPELINE
# ─────────────────────────────────────────────────────────────
def run_forecasts(macro_df: pd.DataFrame, verbose: bool = True) -> dict:
    """
    Barlıq makroekonomikalıq kórsetkishler ushın Prophet modellerin oqitıw.

    Kiriwshi: load_macro() qaytarǵan DataFrame (index=Jıl)
    Qaytaradı: {kórsetkish_atı: {"forecaster": ..., "forecast": pd.DataFrame}}
    """
    results = {}
    all_forecasts = []

    kórsetkishler = [c for c in macro_df.columns]

    for col in kórsetkishler:
        series = macro_df[col].dropna()
        # 2026 yanvar-iyun dáslepki maǵlıwmatı — tolıq jılǵa aylantırıw
        # (joqarı baylıqsız qaldırıw ushın eń sońǵı ekinin ótkerip jiberiw)
        if len(series) > 1:
            # Eǵer sońǵı eki jıl qosımsha (2025 dáslepki) bolsa
            series = series[series.index <= 2025]

        if len(series) < 4:
            if verbose:
                print(f"[Prophet] {col}: az maǵlıwmat ({len(series)}), ótip ketemin")
            continue

        try:
            forecaster = EconomicForecaster(corsetkish_ati=col)
            forecaster.train(series)
            fc = forecaster.forecast(periods=FORECAST_PERIODS)
            model_path = forecaster.save()

            results[col] = {
                "forecaster": forecaster,
                "forecast": fc,
                "model_path": model_path,
            }
            all_forecasts.append(fc)

            if verbose:
                print(f"[Prophet] {col}: oqıtıldı → {FORECAST_YEARS} jıl boljanıw tayar")

        except Exception as e:
            if verbose:
                print(f"[Prophet] {col}: QÁTE — {e}")
            continue

    # Barlıq boljanıwlardı birleshtiriw
    if all_forecasts:
        combined = pd.concat(all_forecasts, ignore_index=True)
        combined_path = os.path.join(RESULTS_DIR, "forecast_combined.csv")
        combined.to_csv(combined_path, index=False, encoding="utf-8")
        if verbose:
            print(f"\n[Prophet] Birlesken boljanıw saqlandı: {combined_path}")
        results["__combined__"] = combined

    return results


# ─────────────────────────────────────────────────────────────
#  IS HAQI KVARTAL BOLJANIWI
# ─────────────────────────────────────────────────────────────
def run_salary_forecast(salary_df: pd.DataFrame, verbose: bool = True) -> dict:
    """
    Is haqı kvartal maǵlıwmatınan Prophet arqalı boljanıw.
    Tármaqlaq: 'Ortasha esaplanǵan aylıq is haqı'
    """
    results = {}

    target_rows = [r for r in salary_df.index if "Ortasha" in str(r) and "aylıq" in str(r).lower()]
    if not target_rows:
        target_rows = salary_df.index[:1].tolist()

    for row_label in target_rows:
        series_raw = salary_df.loc[row_label]
        # Kvartal atları '2018Q1', '2018Q2', ...
        records = []
        for col_label, val in series_raw.items():
            s = str(col_label).strip()
            if "Q" in s and len(s) >= 6:
                try:
                    y = int(s[:4])
                    q = int(s[5])
                    month = q * 3 - 1  # kvartal ortası
                    ds = pd.Timestamp(f"{y}-{month:02d}-15")
                    fval = float(str(val).replace(",", ".").replace(" ", ""))
                    if np.isfinite(fval) and fval > 0:
                        records.append({"ds": ds, "y": fval})
                except (ValueError, TypeError):
                    continue

        if len(records) < 6:
            continue

        prophet_df = pd.DataFrame(records).sort_values("ds").reset_index(drop=True)

        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            seasonality_mode="additive",
            changepoint_prior_scale=0.5,
            interval_width=0.90,
        )
        model.fit(prophet_df)

        last_date = prophet_df["ds"].max()
        future = model.make_future_dataframe(periods=12, freq="QS")
        fc_raw = model.predict(future)

        fc = fc_raw[fc_raw["ds"] > last_date].copy()
        fc["Kórsetkish"] = row_label[:50]
        fc = fc[["ds", "Kórsetkish", "yhat", "yhat_lower", "yhat_upper"]].rename(
            columns={"yhat": "Boljanıw", "yhat_lower": "TómenShegara", "yhat_upper": "JoqarıShegara"}
        )

        results[row_label] = {
            "model": model,
            "prophet_df": prophet_df,
            "forecast": fc,
        }

        if verbose:
            print(f"[Prophet/IsHaqı] {row_label[:40]}: oqıtıldı → 12 kvartal boljanıw tayar")

    return results
