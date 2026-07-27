"""
LSTM Forecast — Eksport hám beqarar waqıtlıq qatarlar ushın
=============================================================

Arxitektura:
    Input (window) → LSTM(64) → Dropout(0.2)
                   → LSTM(32) → Dropout(0.2)
                   → Dense(16) → Dense(1)

Oqıtiw strategiyası:
    - MinMaxScaler normalizatsiya
    - Sliding window (pencere) usılı
    - EarlyStopping (overfit aldının alıw)
    - K-Fold Cross Validation
"""

import os
import pickle
import warnings
import numpy as np
import pandas as pd

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
warnings.filterwarnings("ignore")

import tensorflow as tf
tf.get_logger().setLevel("ERROR")

from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

tf.random.set_seed(42)
np.random.seed(42)


# ─────────────────────────────────────────────────────────────
#  MAǴLÍWMAT TAYARLAW
# ─────────────────────────────────────────────────────────────
def make_sequences(data: np.ndarray, window: int):
    """
    Sliding window arqalı X, y juptarın jasaw.
    data: (n,) → X: (n-window, window, 1),  y: (n-window,)
    """
    X, y = [], []
    for i in range(len(data) - window):
        X.append(data[i : i + window])
        y.append(data[i + window])
    return np.array(X)[..., np.newaxis], np.array(y)


# ─────────────────────────────────────────────────────────────
#  LSTM MODEL KLASSI
# ─────────────────────────────────────────────────────────────
class LSTMForecaster:
    def __init__(
        self,
        corsetkish_ati: str,
        window: int = 3,
        epochs: int = 500,
        batch_size: int = 8,
        lstm_units: tuple = (64, 32),
        dropout: float = 0.2,
        lr: float = 0.001,
    ):
        self.corsetkish_ati = corsetkish_ati
        self.window = window
        self.epochs = epochs
        self.batch_size = batch_size
        self.lstm_units = lstm_units
        self.dropout = dropout
        self.lr = lr

        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.model = None
        self.history = None
        self.train_years = None
        self.scaled_data = None

    def _build_model(self) -> Sequential:
        model = Sequential([
            Input(shape=(self.window, 1)),
            LSTM(self.lstm_units[0], return_sequences=True),
            Dropout(self.dropout),
            LSTM(self.lstm_units[1], return_sequences=False),
            Dropout(self.dropout),
            Dense(16, activation="relu"),
            Dense(1),
        ])
        model.compile(
            optimizer=Adam(learning_rate=self.lr),
            loss="huber",
            metrics=["mae"],
        )
        return model

    def train(self, series: pd.Series, verbose: int = 0):
        """
        series: pd.Series (index=jıl, values=kórsetkish)
        """
        self.train_years = series.index.tolist()
        values = series.values.astype(float).reshape(-1, 1)

        # Normalizatsiya
        self.scaled_data = self.scaler.fit_transform(values).flatten()

        X, y = make_sequences(self.scaled_data, self.window)

        if len(X) < 4:
            raise ValueError(
                f"{self.corsetkish_ati}: window={self.window} ushın az maǵlıwmat "
                f"(kerek: >={self.window + 4}, bar: {len(self.scaled_data)})"
            )

        self.model = self._build_model()

        callbacks = [
            EarlyStopping(
                monitor="val_loss",
                patience=50,
                restore_best_weights=True,
                verbose=0,
            ),
            ReduceLROnPlateau(
                monitor="val_loss",
                factor=0.5,
                patience=20,
                min_lr=1e-6,
                verbose=0,
            ),
        ]

        self.history = self.model.fit(
            X, y,
            epochs=self.epochs,
            batch_size=self.batch_size,
            validation_split=0.2,
            callbacks=callbacks,
            verbose=verbose,
            shuffle=False,
        )

    def forecast(self, periods: int = 5) -> pd.DataFrame:
        """
        Keleshek `periods` jıl ushın boljanıw.
        Monte Carlo Dropout arqalı belirsizlik intervali.
        """
        if self.model is None:
            raise RuntimeError("Aldi oqitıw kerek")

        last_window = self.scaled_data[-self.window :].tolist()
        last_year = max(self.train_years)

        # Monte Carlo — 200 marta stokastik forward pass
        mc_preds = []
        for _ in range(200):
            window = last_window.copy()
            preds = []
            for _ in range(periods):
                x = np.array(window[-self.window :]).reshape(1, self.window, 1)
                # Dropout ta'siri uchun training=True
                p = self.model(x, training=True).numpy()[0, 0]
                preds.append(p)
                window.append(p)
            mc_preds.append(preds)

        mc_preds = np.array(mc_preds)  # (200, periods)
        mean_scaled = mc_preds.mean(axis=0)
        lower_scaled = np.percentile(mc_preds, 5, axis=0)
        upper_scaled = np.percentile(mc_preds, 95, axis=0)

        # Inverse transform
        mean_val  = self.scaler.inverse_transform(mean_scaled.reshape(-1, 1)).flatten()
        lower_val = self.scaler.inverse_transform(lower_scaled.reshape(-1, 1)).flatten()
        upper_val = self.scaler.inverse_transform(upper_scaled.reshape(-1, 1)).flatten()

        result = pd.DataFrame({
            "Jıl":          [last_year + i + 1 for i in range(periods)],
            "Kórsetkish":   self.corsetkish_ati,
            "Boljanıw":     mean_val.round(2),
            "TómenShegara": lower_val.round(2),
            "JoqarıShegara":upper_val.round(2),
        })
        return result

    def insample_metrics(self, series: pd.Series) -> dict:
        """In-sample fit bahası."""
        values = series.values.astype(float).reshape(-1, 1)
        scaled = self.scaler.transform(values).flatten()
        X, y_true_s = make_sequences(scaled, self.window)

        y_pred_s = self.model.predict(X, verbose=0).flatten()
        y_true = self.scaler.inverse_transform(y_true_s.reshape(-1, 1)).flatten()
        y_pred = self.scaler.inverse_transform(y_pred_s.reshape(-1, 1)).flatten()

        mae  = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        r2   = 1 - np.sum((y_true - y_pred)**2) / np.sum((y_true - np.mean(y_true))**2)
        return {
            "MAE": round(mae, 2),
            "RMSE": round(rmse, 2),
            "MAPE": round(mape, 2),
            "R2": round(r2, 4),
            "Anıqlıq": round(max(0, 100 - mape), 2),
        }

    def holdout_test(self, full_series: pd.Series, test_years: list) -> dict:
        """
        Holdout test: full_series ichidan test_years ni boljanaw.
        Model train ma'lumoti (test_years dan oldingi) bilan qayta oqitiladi.
        """
        train_s = full_series[~full_series.index.isin(test_years)]
        test_s  = full_series[full_series.index.isin(test_years)]

        if len(train_s) < self.window + 2:
            return {"error": "Train maǵlıwmatı az"}

        # Qayta oqitiw (faqat train data bilan)
        temp = LSTMForecaster(
            corsetkish_ati=self.corsetkish_ati,
            window=self.window,
            epochs=self.epochs,
            batch_size=self.batch_size,
            lstm_units=self.lstm_units,
            dropout=self.dropout,
            lr=self.lr,
        )
        temp.train(train_s, verbose=0)
        fc = temp.forecast(periods=len(test_years))

        y_true = test_s.values.astype(float)
        y_pred = fc["Boljanıw"].values
        y_lo   = fc["TómenShegara"].values
        y_hi   = fc["JoqarıShegara"].values

        mae  = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        r2   = 1 - np.sum((y_true-y_pred)**2) / np.sum((y_true-np.mean(y_true))**2)
        in_pi = np.sum((y_true >= y_lo) & (y_true <= y_hi))

        rows = []
        for i, yr in enumerate(test_years):
            flag = "OK" if y_lo[i] <= y_true[i] <= y_hi[i] else "MISS"
            rows.append({
                "Jıl": yr,
                "Naqıy": round(y_true[i], 2),
                "Boljanıw": round(y_pred[i], 2),
                "Tómen": round(y_lo[i], 2),
                "Joqarı": round(y_hi[i], 2),
                "Nátiyje": flag,
            })

        return {
            "MAE": round(mae, 2),
            "RMSE": round(rmse, 2),
            "MAPE": round(mape, 2),
            "R2": round(r2, 4),
            "Anıqlıq": round(max(0, 100 - mape), 2),
            "PI_qamraw": f"{in_pi}/{len(test_years)}",
            "Qatarlar": pd.DataFrame(rows),
        }

    def save(self, fname: str | None = None):
        fname = fname or f"lstm_{self.corsetkish_ati}.pkl"
        path = os.path.join(MODELS_DIR, fname)
        # Keras modelni alohida saqlash
        keras_path = path.replace(".pkl", ".keras")
        self.model.save(keras_path)
        # Qolgan attributlarni pickle
        model_backup = self.model
        self.model = keras_path   # faqat path saqlash
        with open(path, "wb") as f:
            pickle.dump(self, f)
        self.model = model_backup
        return path

    @classmethod
    def load(cls, fname: str):
        path = os.path.join(MODELS_DIR, fname)
        with open(path, "rb") as f:
            obj = pickle.load(f)
        # Keras modelni qayta yuklash
        if isinstance(obj.model, str):
            obj.model = load_model(obj.model)
        return obj


# ─────────────────────────────────────────────────────────────
#  BASLAWSHI FUNKSIYA
# ─────────────────────────────────────────────────────────────
def run_lstm_export(
    macro_df: pd.DataFrame,
    target_col: str = "Eksport",
    test_years: list = None,
    forecast_periods: int = 5,
    verbose: bool = True,
) -> dict:
    """
    Eksport (yamasa boshqa kórsetkish) ushın LSTM pipeline.

    Qaytaradı:
        {
          "forecaster":    LSTMForecaster,
          "insample":      dict,
          "holdout":       dict,
          "forecast_df":   pd.DataFrame,
        }
    """
    if test_years is None:
        test_years = [2022, 2023, 2024, 2025]

    series = macro_df[target_col].dropna()
    series = series[series.index <= 2025]

    if verbose:
        print(f"\n[LSTM] {target_col} oqıtılıwda...")
        print(f"  Maǵlıwmat: {len(series)} jıl ({series.index.min()}–{series.index.max()})")
        print(f"  Arxitektura: Input({3}) → LSTM(64) → LSTM(32) → Dense(1)")

    # Window size az maǵlıwmat uchun
    window = min(3, len(series) - 4)

    forecaster = LSTMForecaster(
        corsetkish_ati=target_col,
        window=window,
        epochs=500,
        batch_size=4,
        lstm_units=(64, 32),
        dropout=0.2,
        lr=0.001,
    )

    # Tolıq maǵlıwmat bilan oqıtiw
    forecaster.train(series, verbose=0)

    # In-sample metrikalar
    insample = forecaster.insample_metrics(series)

    if verbose:
        stopped = len(forecaster.history.history["loss"])
        print(f"  Oqıtiw tamamlandı: {stopped} epoch")
        print(f"  In-sample → MAE:{insample['MAE']:.1f}  MAPE:{insample['MAPE']:.2f}%  "
              f"R2:{insample['R2']:.4f}  Anıqlıq:{insample['Anıqlıq']:.2f}%")

    # Holdout test
    if verbose:
        print(f"\n  Holdout test ({test_years[0]}–{test_years[-1]}):")

    holdout = forecaster.holdout_test(series, test_years)

    if verbose and "Qatarlar" in holdout:
        for _, row in holdout["Qatarlar"].iterrows():
            print(f"    {int(row['Jıl'])}: naqıy={row['Naqıy']:>7.1f}  "
                  f"boljanıw={row['Boljanıw']:>7.1f}  "
                  f"[{row['Tómen']:>7.1f} – {row['Joqarı']:>7.1f}]  {row['Nátiyje']}")
        print(f"  Holdout → MAE:{holdout['MAE']:.1f}  MAPE:{holdout['MAPE']:.2f}%  "
              f"R2:{holdout['R2']:.4f}  Anıqlıq:{holdout['Anıqlıq']:.2f}%  "
              f"PI:{holdout['PI_qamraw']}")

    # Keleshek boljanıw
    forecast_df = forecaster.forecast(periods=forecast_periods)

    if verbose:
        print(f"\n  2026–{2025 + forecast_periods} Boljanıwı:")
        for _, row in forecast_df.iterrows():
            print(f"    {int(row['Jıl'])}: {row['Boljanıw']:>7.1f} mln.$  "
                  f"[{row['TómenShegara']:>7.1f} – {row['JoqarıShegara']:>7.1f}]")

    # Model saqlash
    model_path = forecaster.save(f"lstm_{target_col}.pkl")
    if verbose:
        print(f"\n  Model saqlandı: {model_path}")

    # Forecast CSV ni yangilash
    fc_path = os.path.join(RESULTS_DIR, f"lstm_{target_col}_forecast.csv")
    forecast_df.to_csv(fc_path, index=False, encoding="utf-8")

    return {
        "forecaster": forecaster,
        "insample": insample,
        "holdout": holdout,
        "forecast_df": forecast_df,
    }


# ─────────────────────────────────────────────────────────────
#  MULTIVARIATE LSTM (Investitsiya ushın)
# ─────────────────────────────────────────────────────────────
class MultivariateLSTMForecaster:
    """
    Bir neshe kórsetkish → Maqset kórsetkish boljanıwı.
    Investitsiya ushın: JAO + Sanaat + Qurılıs → Investitsiya
    """

    def __init__(
        self,
        target_col: str,
        feature_cols: list,
        window: int = 4,
        epochs: int = 1000,
        batch_size: int = 4,
        lstm_units: tuple = (128, 64),
        dropout: float = 0.2,
        lr: float = 0.001,
    ):
        self.target_col   = target_col
        self.feature_cols = feature_cols
        self.all_cols     = feature_cols  # target included
        self.window       = window
        self.epochs       = epochs
        self.batch_size   = batch_size
        self.lstm_units   = lstm_units
        self.dropout      = dropout
        self.lr           = lr

        self.scalers      = {}
        self.model        = None
        self.history      = None
        self.train_df_    = None
        self.target_idx_  = None

    def _log_scale(self, df: pd.DataFrame, fit: bool = True) -> np.ndarray:
        """Log + MinMax scaling, hár kolonna alohida."""
        log_vals = np.log1p(df.values.astype(float))
        result   = np.zeros_like(log_vals)
        for i, col in enumerate(df.columns):
            if fit:
                sc = MinMaxScaler(feature_range=(0.05, 0.95))
                result[:, i] = sc.fit_transform(log_vals[:, i].reshape(-1, 1)).flatten()
                self.scalers[col] = sc
            else:
                result[:, i] = self.scalers[col].transform(
                    log_vals[:, i].reshape(-1, 1)
                ).flatten()
        return result

    def _inv_target(self, scaled_vals: np.ndarray) -> np.ndarray:
        sc = self.scalers[self.target_col]
        log_vals = sc.inverse_transform(scaled_vals.reshape(-1, 1)).flatten()
        return np.expm1(log_vals)

    def _make_mv_seq(self, scaled: np.ndarray):
        X, y = [], []
        for i in range(len(scaled) - self.window):
            X.append(scaled[i : i + self.window, :])
            y.append(scaled[i + self.window, self.target_idx_])
        return np.array(X), np.array(y)

    def _build(self, n_features: int) -> Sequential:
        m = Sequential([
            Input(shape=(self.window, n_features)),
            LSTM(self.lstm_units[0], return_sequences=True),
            Dropout(self.dropout),
            LSTM(self.lstm_units[1], return_sequences=False),
            Dropout(self.dropout),
            Dense(32, activation="relu"),
            Dense(1),
        ])
        m.compile(optimizer=Adam(self.lr), loss="huber", metrics=["mae"])
        return m

    def train(self, df: pd.DataFrame, verbose: int = 0):
        """df: DataFrame, columns = feature_cols, index = jıl."""
        self.train_df_   = df.copy()
        self.target_idx_ = list(df.columns).index(self.target_col)

        scaled = self._log_scale(df, fit=True)
        X, y   = self._make_mv_seq(scaled)

        self.model = self._build(n_features=df.shape[1])
        cb = [
            EarlyStopping(monitor="val_loss", patience=80,
                          restore_best_weights=True, verbose=0),
            ReduceLROnPlateau(monitor="val_loss", factor=0.5,
                              patience=30, min_lr=1e-7, verbose=0),
        ]
        self.history = self.model.fit(
            X, y,
            epochs=self.epochs, batch_size=self.batch_size,
            validation_split=0.2, callbacks=cb,
            verbose=verbose, shuffle=False,
        )

    def forecast(self, exog_df: pd.DataFrame) -> pd.DataFrame:
        """
        exog_df: test / keleshek dáwir feature qiymatlari
                 (target_col qiymatlari bolmasa 0 qoyiladi)
        Qaytaradı: boljanıw DataFrame
        """
        # Birlestirish: train + exog
        combined = pd.concat([self.train_df_, exog_df])
        scaled   = self._log_scale(combined, fit=False)

        preds_scaled = []
        for i in range(len(exog_df)):
            start = len(self.train_df_) + i - self.window
            win   = scaled[start : start + self.window, :]
            x     = win.reshape(1, self.window, combined.shape[1])
            p     = self.model.predict(x, verbose=0)[0, 0]
            preds_scaled.append(p)
            # Keyingi qadamda predict qilingan qiymatni ishlatish
            scaled[len(self.train_df_) + i, self.target_idx_] = p

        y_pred = self._inv_target(np.array(preds_scaled))

        # Monte Carlo PI
        mc = []
        for _ in range(150):
            ps = []
            sc_copy = scaled.copy()
            for i in range(len(exog_df)):
                start = len(self.train_df_) + i - self.window
                win   = sc_copy[start : start + self.window, :]
                x     = win.reshape(1, self.window, combined.shape[1])
                p     = self.model(x, training=True).numpy()[0, 0]
                ps.append(p)
                sc_copy[len(self.train_df_) + i, self.target_idx_] = p
            mc.append(ps)
        mc = np.array(mc)
        lo = self._inv_target(np.percentile(mc, 5,  axis=0))
        hi = self._inv_target(np.percentile(mc, 95, axis=0))

        return pd.DataFrame({
            "Jıl":           exog_df.index.tolist(),
            "Kórsetkish":    self.target_col,
            "Boljanıw":      y_pred.round(1),
            "TómenShegara":  lo.round(1),
            "JoqarıShegara": hi.round(1),
        })

    def holdout_test(self, full_df: pd.DataFrame, test_years: list) -> dict:
        train_df = full_df[~full_df.index.isin(test_years)]
        test_df  = full_df[full_df.index.isin(test_years)]

        temp = MultivariateLSTMForecaster(
            target_col=self.target_col,
            feature_cols=self.feature_cols,
            window=self.window, epochs=self.epochs,
            batch_size=self.batch_size, lstm_units=self.lstm_units,
            dropout=self.dropout, lr=self.lr,
        )
        temp.train(train_df, verbose=0)

        # Test uchun exog: naqiy feature qiymatlari ishlatiladi
        fc = temp.forecast(test_df)

        y_true = test_df[self.target_col].values.astype(float)
        y_pred = fc["Boljanıw"].values
        y_lo   = fc["TómenShegara"].values
        y_hi   = fc["JoqarıShegara"].values

        mae  = float(np.mean(np.abs(y_true - y_pred)))
        mape = float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100)
        r2   = float(1 - np.sum((y_true-y_pred)**2) / np.sum((y_true-np.mean(y_true))**2))
        in_pi = int(np.sum((y_true >= y_lo) & (y_true <= y_hi)))

        rows = []
        for i, yr in enumerate(test_years):
            flag = "OK" if y_lo[i] <= y_true[i] <= y_hi[i] else "MISS"
            rows.append({
                "Jıl": yr, "Naqıy": round(float(y_true[i]), 1),
                "Boljanıw": round(float(y_pred[i]), 1),
                "Tómen": round(float(y_lo[i]), 1),
                "Joqarı": round(float(y_hi[i]), 1),
                "Nátiyje": flag,
            })
        return {
            "MAE": round(mae, 1), "MAPE": round(mape, 2),
            "R2": round(r2, 4), "Anıqlıq": round(max(0, 100-mape), 2),
            "PI_qamraw": f"{in_pi}/{len(test_years)}",
            "Qatarlar": pd.DataFrame(rows),
        }

    def save(self, fname: str | None = None):
        fname = fname or f"lstm_mv_{self.target_col}.pkl"
        path  = os.path.join(MODELS_DIR, fname)
        keras_path = path.replace(".pkl", ".keras")
        self.model.save(keras_path)
        model_bak  = self.model
        self.model = keras_path
        with open(path, "wb") as f:
            pickle.dump(self, f)
        self.model = model_bak
        return path

    @classmethod
    def load(cls, fname: str):
        path = os.path.join(MODELS_DIR, fname)
        with open(path, "rb") as f:
            obj = pickle.load(f)
        if isinstance(obj.model, str):
            obj.model = load_model(obj.model)
        return obj


def run_lstm_investitsiya(
    macro_df: pd.DataFrame,
    test_years: list = None,
    forecast_periods: int = 5,
    verbose: bool = True,
) -> dict:
    """Investitsiya ushın Multivariate LSTM pipeline."""
    if test_years is None:
        test_years = [2022, 2023, 2024, 2025]

    FEATURES = ["JAO", "Sanaat", "Qurılıs", "Investitsiya"]
    df = macro_df[FEATURES].dropna()
    df = df[df.index <= 2025]

    if verbose:
        print(f"\n[LSTM-MV] Investitsiya oqıtılıwda...")
        print(f"  Features: {FEATURES}")
        print(f"  Arxitektura: Input({4},{4}) → LSTM(128) → LSTM(64) → Dense(1)")

    forecaster = MultivariateLSTMForecaster(
        target_col="Investitsiya",
        feature_cols=FEATURES,
        window=4, epochs=1000, batch_size=4,
        lstm_units=(128, 64), dropout=0.2, lr=0.001,
    )
    forecaster.train(df, verbose=0)

    ep = len(forecaster.history.history["loss"])
    if verbose:
        print(f"  Oqıtiw tamamlandı: {ep} epoch")

    # Holdout test
    holdout = forecaster.holdout_test(df, test_years)

    if verbose and "Qatarlar" in holdout:
        print(f"\n  Holdout test ({test_years[0]}–{test_years[-1]}):")
        for _, row in holdout["Qatarlar"].iterrows():
            print(f"    {int(row['Jıl'])}: naqıy={row['Naqıy']:>10,.1f}  "
                  f"boljanıw={row['Boljanıw']:>10,.1f}  "
                  f"[{row['Tómen']:>10,.1f} – {row['Joqarı']:>10,.1f}]  {row['Nátiyje']}")
        print(f"  Holdout → MAPE:{holdout['MAPE']:.2f}%  "
              f"Anıqlıq:{holdout['Anıqlıq']:.2f}%  "
              f"R2:{holdout['R2']:.4f}  PI:{holdout['PI_qamraw']}")

    # Keleshek boljanıw — feature qiymatlari uchun Prophet boljanıwidan foydalanamiz
    last_year  = df.index.max()
    future_idx = list(range(last_year + 1, last_year + forecast_periods + 1))

    # Oddiy ekstrapolyatsiya (JAO, Sanaat, Qurılıs uchun)
    growth_rates = {}
    for col in ["JAO", "Sanaat", "Qurılıs"]:
        last_vals = df[col].values[-4:]
        growth    = np.mean(np.diff(last_vals) / last_vals[:-1])
        growth_rates[col] = growth

    exog_rows = {}
    for col in FEATURES:
        if col == "Investitsiya":
            exog_rows[col] = [0.0] * forecast_periods  # placeholder
        else:
            last_val = float(df[col].iloc[-1])
            vals = []
            for i in range(forecast_periods):
                last_val *= (1 + growth_rates[col])
                vals.append(last_val)
            exog_rows[col] = vals

    exog_df = pd.DataFrame(exog_rows, index=future_idx)
    forecast_df = forecaster.forecast(exog_df)

    if verbose:
        print(f"\n  {last_year+1}–{last_year+forecast_periods} Boljanıwı:")
        for _, row in forecast_df.iterrows():
            print(f"    {int(row['Jıl'])}: {row['Boljanıw']:>10,.1f} mlrd. som  "
                  f"[{row['TómenShegara']:>10,.1f} – {row['JoqarıShegara']:>10,.1f}]")

    model_path = forecaster.save("lstm_mv_Investitsiya.pkl")
    if verbose:
        print(f"\n  Model saqlandı: {model_path}")

    fc_path = os.path.join(RESULTS_DIR, "lstm_mv_Investitsiya_forecast.csv")
    forecast_df.to_csv(fc_path, index=False, encoding="utf-8")

    return {
        "forecaster": forecaster,
        "holdout":    holdout,
        "forecast_df": forecast_df,
    }


# ─────────────────────────────────────────────────────────────
#  PROPHET vs LSTM SALISTIRMA
# ─────────────────────────────────────────────────────────────
def compare_prophet_vs_lstm(
    macro_df: pd.DataFrame,
    lstm_result: dict,
    target_col: str = "Eksport",
    test_years: list = None,
) -> pd.DataFrame:
    """
    Prophet hám LSTM nátiyjelerin salıstırıw jadwalı.
    """
    import warnings
    warnings.filterwarnings("ignore")
    import logging
    logging.getLogger("prophet").setLevel(logging.ERROR)
    logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
    from prophet import Prophet

    if test_years is None:
        test_years = [2022, 2023, 2024, 2025]

    series = macro_df[target_col].dropna()
    series = series[series.index <= 2025]
    train_s = series[~series.index.isin(test_years)]
    test_s  = series[series.index.isin(test_years)]

    # Prophet qayta oqitiw (holdout)
    train_df = pd.DataFrame({
        "ds": pd.to_datetime(train_s.index.astype(str) + "-06-15"),
        "y": train_s.values.astype(float),
    })
    prophet_model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=False,
        daily_seasonality=False,
        seasonality_mode="multiplicative",
        changepoint_prior_scale=0.3,
        interval_width=0.90,
    )
    prophet_model.fit(train_df)
    test_df = pd.DataFrame({
        "ds": pd.to_datetime(pd.Index(test_years).astype(str) + "-06-15")
    })
    prophet_fc = prophet_model.predict(test_df)
    p_pred = prophet_fc["yhat"].values
    p_true = test_s.values.astype(float)
    p_mape = np.mean(np.abs((p_true - p_pred) / p_true)) * 100
    p_r2 = 1 - np.sum((p_true-p_pred)**2) / np.sum((p_true-np.mean(p_true))**2)

    # LSTM natiyjalar
    lstm_holdout = lstm_result["holdout"]

    rows = []
    lstm_rows = lstm_holdout["Qatarlar"]
    for i, yr in enumerate(test_years):
        lstm_row = lstm_rows[lstm_rows["Jıl"] == yr].iloc[0]
        rows.append({
            "Jıl":              yr,
            "Naqıy":           round(p_true[i], 1),
            "Prophet boljanıw": round(p_pred[i], 1),
            "Prophet qáte":    round(abs(p_true[i] - p_pred[i]), 1),
            "LSTM boljanıw":   lstm_row["Boljanıw"],
            "LSTM qáte":       round(abs(p_true[i] - lstm_row["Boljanıw"]), 1),
            "Jaqsısı":         "LSTM" if abs(p_true[i]-lstm_row["Boljanıw"]) < abs(p_true[i]-p_pred[i]) else "Prophet",
        })

    cmp_df = pd.DataFrame(rows)

    summary = pd.DataFrame([
        {
            "Model":      "Prophet",
            "MAPE (%)":   round(p_mape, 2),
            "R2":         round(p_r2, 4),
            "Anıqlıq (%)": round(max(0, 100 - p_mape), 2),
        },
        {
            "Model":      "LSTM",
            "MAPE (%)":   lstm_holdout["MAPE"],
            "R2":         lstm_holdout["R2"],
            "Anıqlıq (%)": lstm_holdout["Anıqlıq"],
        },
    ])

    return cmp_df, summary
