"""
compute_sentiment_and_merge.py
-------------------------------
1. Runs VADER sentiment analysis on each news headline + summary.
2. Aggregates daily sentiment scores.
3. Merges with gold price data.
4. Creates binary target: 1 = gold price went UP the next day, 0 = went DOWN.
5. Saves final training dataset to /home/mimou/airflow/mid-semester/data/training_data.csv
"""

import os
import pandas as pd
import numpy as np
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

DATA_DIR = os.environ.get("AIRFLOW_DATA_DIR", "/home/mimou/airflow/mid-semester/data")

OUTPUT_FILE = os.path.join(DATA_DIR, "training_data.csv")

analyzer = SentimentIntensityAnalyzer()


def _sentiment_score(text: str) -> float:
    """Return VADER compound score for a piece of text (-1 to +1)."""
    if not text or not isinstance(text, str):
        return 0.0
    return analyzer.polarity_scores(text)["compound"]


def _aggregate_daily_sentiment(news_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate multiple news articles per day into a single row.
    Computes mean, min, max compound sentiment and article count.
    """
    news_df = news_df.copy()
    news_df["date"] = pd.to_datetime(news_df["date"]).dt.date

    # Score each article on combined title + summary
    news_df["text"] = (
        news_df["title"].fillna("") + " " + news_df["summary"].fillna("")
    )
    news_df["sentiment_compound"] = news_df["text"].apply(_sentiment_score)

    daily = (
        news_df.groupby("date")
        .agg(
            sentiment_mean=("sentiment_compound", "mean"),
            sentiment_min=("sentiment_compound", "min"),
            sentiment_max=("sentiment_compound", "max"),
            article_count=("sentiment_compound", "count"),
        )
        .reset_index()
    )
    daily["date"] = pd.to_datetime(daily["date"])
    return daily


def compute_and_merge(
    gold_csv: str,
    news_csv: str,
    output_path: str = OUTPUT_FILE,
) -> str:
    """
    Loads gold prices and war news, computes sentiment, merges, and creates target.

    Parameters
    ----------
    gold_csv   : Path to gold_prices.csv
    news_csv   : Path to war_news.csv
    output_path: Where to save training_data.csv

    Returns
    -------
    str: Path to the saved training CSV
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # ── Load data ────────────────────────────────────────────────────
    gold_df = pd.read_csv(gold_csv)
    news_df = pd.read_csv(news_csv)

    gold_df["date"] = pd.to_datetime(gold_df["date"])
    gold_df = gold_df.sort_values("date").reset_index(drop=True)

    # ── Compute daily sentiment ───────────────────────────────────────
    daily_sentiment = _aggregate_daily_sentiment(news_df)

    # ── Merge on date ────────────────────────────────────────────────
    merged = pd.merge(gold_df, daily_sentiment, on="date", how="left")

    # Fill missing sentiment with 0 (neutral — no war news that day)
    sentiment_cols = ["sentiment_mean", "sentiment_min", "sentiment_max", "article_count"]
    for col in sentiment_cols:
        merged[col] = merged[col].fillna(0)

    # ── Create binary target label ────────────────────────────────────
    # target = 1 if next-day close > today's close, else 0
    merged = merged.sort_values("date").reset_index(drop=True)
    merged["next_close"] = merged["close"].shift(-1)
    merged["target"] = (merged["next_close"] > merged["close"]).astype(int)

    # Drop the last row (no next-day price available)
    merged = merged.dropna(subset=["next_close"]).drop(columns=["next_close"])

    # ── Add extra features ────────────────────────────────────────────
    # Lag features: previous day's sentiment and price change
    merged["prev_sentiment"] = merged["sentiment_mean"].shift(1).fillna(0)
    merged["price_change_pct"] = merged["close"].pct_change().fillna(0)
    merged["prev_price_change_pct"] = merged["price_change_pct"].shift(1).fillna(0)

    # Rolling 7-day sentiment average
    merged["sentiment_7d_avg"] = (
        merged["sentiment_mean"].rolling(7, min_periods=1).mean()
    )

    merged = merged.reset_index(drop=True)
    merged.to_csv(output_path, index=False)
    print(f"Training dataset: {len(merged)} rows, {merged.columns.tolist()}")
    print(f"Target distribution:\n{merged['target'].value_counts()}")
    print(f"Saved → {output_path}")
    return output_path


# ── standalone execution ───────────────────────────────────────────────
if __name__ == "__main__":
    gold_csv = os.path.join(DATA_DIR, "gold_prices.csv")
    news_csv = os.path.join(DATA_DIR, "war_news.csv")
    path = compute_and_merge(gold_csv, news_csv)
    df = pd.read_csv(path)
    print(df.tail())
