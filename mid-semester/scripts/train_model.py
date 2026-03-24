import os
import json
import joblib
import numpy as np
import pandas as pd
from datetime import date
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    roc_auc_score,
)

DATA_DIR   = os.environ.get("AIRFLOW_DATA_DIR",   "/home/mimou/airflow/mid-semester/data")
MODELS_DIR = os.environ.get("AIRFLOW_MODELS_DIR", "/home/mimou/airflow/mid-semester/models")

FEATURE_COLS = [
    "sentiment_mean",
    "sentiment_min",
    "sentiment_max",
    "article_count",
    "prev_sentiment",
    "price_change_pct",
    "prev_price_change_pct",
    "sentiment_7d_avg",
]
TARGET_COL = "target"


def train_and_save_model(
    training_csv: str = os.path.join(DATA_DIR, "training_data.csv"),
    models_dir: str = MODELS_DIR,
) -> str:
    """
    Loads training data, trains a classifier, evaluates, and saves model.

    Parameters
    ----------
    training_csv : Path to training_data.csv produced by compute_sentiment_and_merge
    models_dir   : Directory to save model artefacts

    Returns
    -------
    str: Path to the saved model file
    """
    os.makedirs(models_dir, exist_ok=True)

    df = pd.read_csv(training_csv)
    print(f"Loaded training data: {df.shape}")

    # Validate columns
    missing = [c for c in FEATURE_COLS + [TARGET_COL] if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in training data: {missing}")

    X = df[FEATURE_COLS].fillna(0).values
    y = df[TARGET_COL].values

    if len(X) < 30:
        raise ValueError(f"Not enough training samples ({len(X)}). Need at least 30.")

    # Train / test split (80/20, time-ordered — no shuffle)
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    # Build pipeline 
    # Try three models, keep the best by CV accuracy
    candidates = {
        "RandomForest": Pipeline([
            ("clf", RandomForestClassifier(
                n_estimators=200,
                max_depth=6,
                min_samples_leaf=5,
                random_state=42,
                class_weight="balanced",
            ))
        ]),
        "GradientBoosting": Pipeline([
            ("clf", GradientBoostingClassifier(
                n_estimators=100,
                max_depth=3,
                learning_rate=0.05,
                random_state=42,
            ))
        ]),
        "LogisticRegression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42))
        ]),
    }

    best_name, best_pipeline, best_cv = None, None, -1
    cv_results = {}
    for name, pipeline in candidates.items():
        cv_scores = cross_val_score(pipeline, X_train, y_train, cv=5, scoring="accuracy")
        cv_mean = cv_scores.mean()
        cv_results[name] = round(float(cv_mean), 4)
        print(f"  {name}: CV accuracy = {cv_mean:.4f} ± {cv_scores.std():.4f}")
        if cv_mean > best_cv:
            best_cv = cv_mean
            best_name = name
            best_pipeline = pipeline

    print(f"\nBest model: {best_name} (CV accuracy: {best_cv:.4f})")

    #Final fit on full training set
    best_pipeline.fit(X_train, y_train)

    # Evaluate on held-out test set 
    y_pred = best_pipeline.predict(X_test)
    y_prob = best_pipeline.predict_proba(X_test)[:, 1] if hasattr(best_pipeline, "predict_proba") else None

    test_accuracy = accuracy_score(y_test, y_pred)
    roc_auc = float(roc_auc_score(y_test, y_prob)) if y_prob is not None else None
    report = classification_report(y_test, y_pred, output_dict=True)
    cm = confusion_matrix(y_test, y_pred).tolist()

    print(f"\nTest accuracy : {test_accuracy:.4f}")
    if roc_auc:
        print(f"ROC-AUC       : {roc_auc:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # Feature importance (if available)
    feature_importance = {}
    estimator = best_pipeline.named_steps.get("clf")
    if hasattr(estimator, "feature_importances_"):
        for feat, imp in zip(FEATURE_COLS, estimator.feature_importances_):
            feature_importance[feat] = round(float(imp), 6)
        print("\nFeature importances:")
        for feat, imp in sorted(feature_importance.items(), key=lambda x: -x[1]):
            print(f"  {feat:30s} {imp:.6f}")

    # Save model 
    today_str = date.today().strftime("%Y%m%d")
    model_filename = f"gold_model_{today_str}.joblib"
    model_path = os.path.join(models_dir, model_filename)
    latest_path = os.path.join(models_dir, "gold_model_latest.joblib")

    joblib.dump(best_pipeline, model_path)
    joblib.dump(best_pipeline, latest_path)
    print(f"\nModel saved → {model_path}")
    print(f"Latest link → {latest_path}")

    #  Save metrics 
    metrics = {
        "run_date": today_str,
        "best_model": best_name,
        "cv_accuracy_by_model": cv_results,
        "test_accuracy": round(test_accuracy, 4),
        "roc_auc": round(roc_auc, 4) if roc_auc else None,
        "classification_report": report,
        "confusion_matrix": cm,
        "feature_importance": feature_importance,
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "features": FEATURE_COLS,
    }
    metrics_path = os.path.join(models_dir, f"model_metrics_{today_str}.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics saved → {metrics_path}")

    return model_path


#  standalone execution 
if __name__ == "__main__":
    training_csv = os.path.join(DATA_DIR, "training_data.csv")
    train_and_save_model(training_csv)
