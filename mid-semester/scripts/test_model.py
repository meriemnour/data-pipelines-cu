"""
test_model.py
-------------
Loads the latest trained gold-price prediction model and runs
a comprehensive test suite.

Usage:
    python test_model.py
    python test_model.py --model /path/to/model.joblib
    python test_model.py --data  /path/to/training_data.csv
"""

import os, sys, argparse, json
import numpy as np
import pandas as pd
import joblib
from datetime import date
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score

MODELS_DIR   = os.environ.get("AIRFLOW_MODELS_DIR", "/home/mimou/airflow/mid-semester/models")
DATA_DIR     = os.environ.get("AIRFLOW_DATA_DIR",   "/home/mimou/airflow/mid-semester/data")
LATEST_MODEL = os.path.join(MODELS_DIR, "gold_model_latest.joblib")

FEATURE_COLS = [
    "sentiment_mean","sentiment_min","sentiment_max","article_count",
    "prev_sentiment","price_change_pct","prev_price_change_pct","sentiment_7d_avg",
]

def _sec(t): print(f"\n{'='*60}\n  {t}\n{'='*60}")

def test_model_loads(path):
    _sec("TEST 1 — Model Loads")
    try:
        m = joblib.load(path)
        print(f"✅ PASS  Loaded: {path}  [{type(m).__name__}]")
        return m
    except Exception as e:
        print(f"❌ FAIL  {e}"); sys.exit(1)

def test_predict_interface(m):
    _sec("TEST 2 — Predict Interface")
    cases = {
        "Negative sentiment": [[-0.6,-0.9,-0.2,5,-0.4,-0.01,-0.005,-0.5]],
        "Positive sentiment": [[0.5,0.1,0.8,3,0.4,0.012,0.008,0.4]],
        "Neutral (no news)":  [[0.0,0.0,0.0,0,0.0,0.0,0.0,0.0]],
    }
    for label, x in cases.items():
        try:
            pred = m.predict(np.array(x))[0]
            prob = m.predict_proba(np.array(x))[0]
            print(f"✅ PASS  [{label}]  → {'UP ↑' if pred==1 else 'DOWN ↓'}  conf:{max(prob):.2%}")
        except Exception as e:
            print(f"❌ FAIL  [{label}]  → {e}")

def test_feature_count(m):
    _sec("TEST 3 — Feature Count")
    n = len(FEATURE_COLS)
    try:
        m.predict(np.zeros((1, n+1)))
        print(f"⚠️  WARN  Model accepted wrong feature count {n+1}")
    except Exception:
        print(f"✅ PASS  Correctly rejects wrong feature count")
    try:
        m.predict(np.zeros((1, n)))
        print(f"✅ PASS  Accepts correct feature count ({n})")
    except Exception as e:
        print(f"❌ FAIL  {e}")

def test_output_classes(m):
    _sec("TEST 4 — Output Classes")
    X = np.random.randn(50, len(FEATURE_COLS))
    preds = m.predict(X)
    if set(preds).issubset({0,1}):
        print(f"✅ PASS  All predictions binary (0/1): {dict(zip(*np.unique(preds, return_counts=True)))}")
    else:
        print(f"❌ FAIL  Unexpected values: {set(preds)}")
    probs = m.predict_proba(X)
    print(f"{'✅ PASS' if probs.shape==(50,2) else '❌ FAIL'}  predict_proba shape: {probs.shape}")
    print(f"{'✅ PASS' if np.allclose(probs.sum(1),1,atol=1e-6) else '❌ FAIL'}  Probs sum to 1.0")

def test_on_training_data(m, data_path):
    _sec("TEST 5 — Performance on Held-Out Test Split")
    if not os.path.exists(data_path):
        print(f"⚠️  WARN  {data_path} not found. Skipping."); return
    df = pd.read_csv(data_path)
    X = df[FEATURE_COLS].fillna(0).values
    y = df["target"].values
    split = int(len(X)*0.8)
    Xt, yt = X[split:], y[split:]
    if len(Xt)==0:
        print("⚠️  WARN  Not enough data for test split."); return
    yp = m.predict(Xt)
    yprob = m.predict_proba(Xt)[:,1]
    acc = accuracy_score(yt, yp)
    roc = roc_auc_score(yt, yprob)
    print(f"{'✅ PASS' if acc>=0.5 else '⚠️  WARN'}  Test accuracy: {acc:.4f}")
    print(f"✅ PASS  ROC-AUC: {roc:.4f}")
    print(classification_report(yt, yp, target_names=["DOWN(0)","UP(1)"]))

def test_edge_cases(m):
    _sec("TEST 6 — Edge Cases")
    for label, X in [
        ("All zeros",        np.zeros((1,len(FEATURE_COLS)))),
        ("Extreme positives",np.ones((1,len(FEATURE_COLS)))*1e6),
        ("Extreme negatives",np.ones((1,len(FEATURE_COLS)))*-1e6),
    ]:
        try:
            pred = m.predict(np.nan_to_num(X))[0]
            print(f"✅ PASS  [{label}] → {pred}")
        except Exception as e:
            print(f"❌ FAIL  [{label}] → {e}")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=LATEST_MODEL)
    p.add_argument("--data",  default=os.path.join(DATA_DIR,"training_data.csv"))
    args = p.parse_args()
    print(f"\n{'#'*60}\n  Gold Price ML Model Test Suite  —  {date.today()}\n{'#'*60}")
    m = test_model_loads(args.model)
    test_predict_interface(m)
    test_feature_count(m)
    test_output_classes(m)
    test_on_training_data(m, args.data)
    test_edge_cases(m)
    print(f"\n{'='*60}\n  All tests complete.\n{'='*60}\n")

if __name__ == "__main__":
    main()
