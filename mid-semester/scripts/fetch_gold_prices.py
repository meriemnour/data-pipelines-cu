import os
import pandas as pd
import yfinance as yf
from datetime import date

DATA_DIR = os.environ.get("AIRFLOW_DATA_DIR", "/home/mimou/airflow/mid-semester/data")
OUTPUT_FILE = os.path.join(DATA_DIR, "gold_prices.csv")


def fetch_and_save_gold_prices(
    ticker: str = "GC=F",
    start_date: str = "2024-01-01",
    output_path: str = OUTPUT_FILE,
) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    end_date = str(date.today())
    print(f"Fetching gold prices [{start_date} → {end_date}] ticker={ticker}")

    #THE API CALL
    raw = yf.download(ticker, start=start_date, end=end_date, progress=False)

    if raw.empty:
        raise ValueError(f"No data returned for ticker '{ticker}'. Check the symbol or date range.")

    # Flatten multi-level columns produced by yfinance
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = ["_".join(col).strip() for col in raw.columns]

    # Normalise column names
    raw = raw.reset_index()
    raw.columns = [c.lower().replace(" ", "_") for c in raw.columns]

    # Keep only the columns we need and rename for clarity
    col_map = {}
    for c in raw.columns:
        if "date" in c:
            col_map[c] = "date"
        elif "close" in c:
            col_map[c] = "close"
        elif "open" in c:
            col_map[c] = "open"
        elif "high" in c:
            col_map[c] = "high"
        elif "low" in c:
            col_map[c] = "low"
        elif "volume" in c:
            col_map[c] = "volume"

    raw = raw.rename(columns=col_map)

    keep = [c for c in ["date", "open", "high", "low", "close", "volume"] if c in raw.columns]
    df = raw[keep].copy()

    # Ensure date is a proper date (no time component)
    df["date"] = pd.to_datetime(df["date"]).dt.date

    # Drop any NaN rows
    df = df.dropna(subset=["close"])
    df = df.sort_values("date").reset_index(drop=True)

    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} rows → {output_path}")
    return output_path

if __name__ == "__main__":
    path = fetch_and_save_gold_prices()
    df = pd.read_csv(path)
    print(df.tail())
