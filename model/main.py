"""
Qaraqalpaqstan Respublikası Ekonomikalıq ML Sistemi
====================================================

Júrgizish:
    python -u main.py
    python -u main.py --only-weakspot
    python -u main.py --only-forecast
    python -u main.py --no-verbose
"""

import argparse
import sys
import os
import io

# Windows UTF-8 encoding qosiw
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "buffer"):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except (AttributeError, io.UnsupportedOperation):
        pass

sys.path.insert(0, os.path.dirname(__file__))

from src.pipeline import run_pipeline
from src.data_loader import load_macro, load_rayon_unemployment, load_salary
from src.weak_spot import run_weak_spot
from src.forecast import run_forecasts, run_salary_forecast


def main():
    parser = argparse.ArgumentParser(description="Qaraqalpaqstan Ekonomika ML Pipeline")
    parser.add_argument("--no-verbose",      action="store_true", help="Habarlar azaytılsın")
    parser.add_argument("--only-weakspot",   action="store_true", help="Tek Weak Spot")
    parser.add_argument("--only-forecast",   action="store_true", help="Tek Forecast")
    args = parser.parse_args()

    verbose = not args.no_verbose

    if args.only_weakspot:
        print("=== WEAK SPOT ML (XGBoost) ===")
        unemp_df = load_rayon_unemployment()
        results = run_weak_spot(unemp_df, verbose=verbose)
        print("\nEń sońǵı jıl nátiyjeleri:")
        print(results["latest"][["Rayon", "JumıssızlıqPáti", "Boljanıw"]].to_string(index=False))

    elif args.only_forecast:
        print("=== FORECAST ML (Prophet) ===")
        macro_df = load_macro()
        results = run_forecasts(macro_df, verbose=verbose)
        if "__combined__" in results:
            print("\nBoljanıw nátiyjeleri:")
            print(results["__combined__"].to_string(index=False))

    else:
        results = run_pipeline(verbose=verbose)

    return results


if __name__ == "__main__":
    main()
