"""
Weak Spot ML — XGBoost
Rayonlardıń ekonomikalıq álsiz jaqların anıqlaw ushın.

Nısaw:
    - Hár rayon + hár jıl ushın "qauip dárejesi" belgisi qoyıw
    - Feature importance arqalı qaysı kórsetkish eń kóp tásir etiwi anıqlaw
    - Jańa dáwir ushın boljanıw (prediction)
"""

import os
import pickle
import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
os.makedirs(MODELS_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────
#  BELGI (LABEL) QOYIW QOLLARI
#   0 = "Jaqsı"    (jumıssızlıq < 6%)
#   1 = "Ortasha"  (6% ≤ jumıssızlıq < 9%)
#   2 = "Qauipli"  (jumıssızlıq ≥ 9%)
# ─────────────────────────────────────────────────────────────
LABEL_NAMES = {0: "Jaqsı", 1: "Ortasha", 2: "Qauipli"}
THRESHOLDS = (6.0, 9.0)


def _label(pati: float) -> int:
    if pati < THRESHOLDS[0]:
        return 0
    elif pati < THRESHOLDS[1]:
        return 1
    return 2


# ─────────────────────────────────────────────────────────────
#  FEATURE ENGINEERING
# ─────────────────────────────────────────────────────────────
def build_features(df_unemp: pd.DataFrame) -> pd.DataFrame:
    """
    Jumıssızlıq DataFrame sinden ML ushın feature matritsası jasaw.

    Kiriwshi: load_rayon_unemployment() qaytarǵan DataFrame
    Qaytaradı: features + target bolǵan DataFrame
    """
    df = df_unemp.copy().sort_values(["Rayon", "Jıl"]).reset_index(drop=True)

    # Rayon boyınsha ózgeriwler
    df["Jumıssız_YılÓzg"] = df.groupby("Rayon")["JumıssızlıqPáti"].diff()
    df["Jumıssız_2YılÓzg"] = df.groupby("Rayon")["JumıssızlıqPáti"].diff(2)
    df["Bántler_YılÓzg"] = df.groupby("Rayon")["Bántler"].diff()
    df["AktivXalıq_YılÓzg"] = df.groupby("Rayon")["AktivXalıq"].diff()

    # Jumıssızlardıń úlesi
    df["JumıssızUles"] = df["Jumıssızlar"] / df["AktivXalıq"]

    # Bántlerdiń úlesi
    df["BántlerUles"] = df["Bántler"] / df["AktivXalıq"]

    # Jıl kódı (trend ushın)
    df["JılKód"] = df["Jıl"] - df["Jıl"].min()

    # Rayon kódı (kategoriyalıq)
    le = LabelEncoder()
    df["RayonKód"] = le.fit_transform(df["Rayon"])

    # Maqset belgisi
    df["WeakSpot"] = df["JumıssızlıqPáti"].apply(_label)

    # NaN qatarların taslaw
    df = df.dropna(subset=[
        "Jumıssız_YılÓzg", "BántlerUles", "JumıssızUles"
    ]).reset_index(drop=True)

    return df, le


FEATURE_COLS = [
    "JumıssızlıqPáti",
    "Jumıssız_YılÓzg",
    "Jumıssız_2YılÓzg",
    "BántlerUles",
    "JumıssızUles",
    "Bántler_YılÓzg",
    "AktivXalıq_YılÓzg",
    "AktivXalıq",
    "JılKód",
    "RayonKód",
]


# ─────────────────────────────────────────────────────────────
#  MODEL OQITIW
# ─────────────────────────────────────────────────────────────
class WeakSpotDetector:
    def __init__(self):
        self.model = XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            use_label_encoder=False,
            eval_metric="mlogloss",
            random_state=42,
        )
        self.label_encoder = None
        self.feature_importance_ = None
        self.cv_scores_ = None

    def train(self, df_features: pd.DataFrame):
        """Model oqitıw."""
        avail = [c for c in FEATURE_COLS if c in df_features.columns]
        X = df_features[avail].values
        y = df_features["WeakSpot"].values

        # Cross-validation
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        self.cv_scores_ = cross_val_score(self.model, X, y, cv=cv, scoring="f1_macro")

        # Tolıq model oqitiw
        self.model.fit(X, y)

        # Feature importance
        imp = self.model.feature_importances_
        self.feature_importance_ = pd.Series(imp, index=avail).sort_values(ascending=False)

    def predict(self, df_features: pd.DataFrame) -> np.ndarray:
        avail = [c for c in FEATURE_COLS if c in df_features.columns]
        X = df_features[avail].values
        return self.model.predict(X)

    def predict_proba(self, df_features: pd.DataFrame) -> np.ndarray:
        avail = [c for c in FEATURE_COLS if c in df_features.columns]
        X = df_features[avail].values
        return self.model.predict_proba(X)

    def save(self, fname: str = "weak_spot_model.pkl"):
        path = os.path.join(MODELS_DIR, fname)
        with open(path, "wb") as f:
            pickle.dump(self, f)
        return path

    @classmethod
    def load(cls, fname: str = "weak_spot_model.pkl"):
        path = os.path.join(MODELS_DIR, fname)
        with open(path, "rb") as f:
            return pickle.load(f)


# ─────────────────────────────────────────────────────────────
#  NÁTIYJE JADWALI
# ─────────────────────────────────────────────────────────────
def build_result_table(
    df_features: pd.DataFrame,
    detector: WeakSpotDetector,
) -> pd.DataFrame:
    """
    Hár rayon hám jıl ushın boljanıw nátiyjesini qaytaradı.
    """
    preds = detector.predict(df_features)
    proba = detector.predict_proba(df_features)

    result = df_features[["Jıl", "Rayon", "JumıssızlıqPáti", "AktivXalıq", "Bántler"]].copy()
    result["Boljanıw"] = [LABEL_NAMES[p] for p in preds]
    result["Naqıylıq"] = df_features["WeakSpot"].map(LABEL_NAMES)
    result["Tuwrı"] = (preds == df_features["WeakSpot"].values)
    result["P_Jaqsı"] = proba[:, 0].round(3)
    result["P_Ortasha"] = proba[:, 1].round(3)
    result["P_Qauipli"] = proba[:, 2].round(3)

    return result.sort_values(["Jıl", "Rayon"]).reset_index(drop=True)


def latest_weak_spots(result_df: pd.DataFrame) -> pd.DataFrame:
    """Eń sońǵı jıl boyınsha álsiz rayonlar."""
    max_year = result_df["Jıl"].max()
    latest = result_df[result_df["Jıl"] == max_year].copy()
    return latest.sort_values("JumıssızlıqPáti", ascending=False).reset_index(drop=True)


# ─────────────────────────────────────────────────────────────
#  BASLAWSHI FUNKSIYA
# ─────────────────────────────────────────────────────────────
def run_weak_spot(df_unemp: pd.DataFrame, verbose: bool = True) -> dict:
    """
    Weak Spot ML pipeline tolıq júrgiziw.

    Qaytaradı:
        {
          "detector":   WeakSpotDetector,
          "result_df":  pd.DataFrame,
          "latest":     pd.DataFrame,
          "feature_importance": pd.Series,
          "cv_scores":  np.ndarray,
          "report":     str (classification report),
        }
    """
    df_feat, le = build_features(df_unemp)

    detector = WeakSpotDetector()
    detector.label_encoder = le

    if verbose:
        print("[WeakSpot] Oqıtıw baslandı...")

    detector.train(df_feat)

    preds = detector.predict(df_feat)
    y_true = df_feat["WeakSpot"].values

    report = classification_report(
        y_true, preds,
        target_names=list(LABEL_NAMES.values()),
        zero_division=0,
    )

    result_df = build_result_table(df_feat, detector)
    latest = latest_weak_spots(result_df)

    model_path = detector.save()

    if verbose:
        print(f"[WeakSpot] Oqıtiw tamamlandı. Model saqlandı: {model_path}")
        print(f"[WeakSpot] CV F1-macro: {detector.cv_scores_.mean():.3f} ± {detector.cv_scores_.std():.3f}")
        print(f"\n[WeakSpot] Feature Importance:")
        print(detector.feature_importance_.to_string())
        print(f"\n[WeakSpot] Classification Report:")
        print(report)

    return {
        "detector": detector,
        "result_df": result_df,
        "latest": latest,
        "feature_importance": detector.feature_importance_,
        "cv_scores": detector.cv_scores_,
        "report": report,
    }
