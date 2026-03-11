# Gold Price & War News ML Pipeline
### Lecture 6 – Mid-Semester Assignment

## Overview
An ETL + ML pipeline built with Apache Airflow that:
1. **Fetches gold prices** (2024-01-01 → today) via `yfinance` (`GC=F`)
2. **Fetches war-related news** from NYT RSS feeds, filtered by conflict keywords
3. **Computes sentiment** (VADER) on news headlines, merges with gold data, engineers features
4. **Trains a Random Forest classifier** to predict if gold price will go **UP (1)** or **DOWN (0)** the next day
5. **Runs weekly** (`@weekly` / `0 0 * * 0`) to retrain on fresh data

---

## Pipeline Architecture

```
fetch_gold_prices ──┐
                    ├──► compute_sentiment_and_merge ──► train_model
fetch_war_news  ────┘
```

---

## Project Structure

```
gold_pipeline/
├── dags/
│   └── gold_war_pipeline.py      ← Main Airflow DAG
├── scripts/
│   ├── test_model.py             ← Load & test the trained model
│   └── generate_sample_data.py  ← Generate demo CSVs
├── terraform/
│   ├── main.tf                  ← AWS infrastructure (EC2 + S3 + IAM)
│   ├── variables.tf
│   ├── outputs.tf
│   └── userdata.sh              ← EC2 bootstrap script
├── data/                        ← gold_prices.csv, war_news.csv, training_data.csv
├── models/                      ← gold_model_<date>.pkl + metrics JSON
├── requirements.txt
├── docker-compose.yml
└── README.md
```

---

## Quick Start

### Option A – Docker (recommended for local dev)
```bash
docker-compose up airflow-init
docker-compose up
# open http://localhost:8080  (admin / admin)
# trigger DAG: gold_war_news_ml_pipeline
```

### Option B – Local Python
```bash
pip install -r requirements.txt
# generate sample data
python scripts/generate_sample_data.py
# test the model
python scripts/test_model.py
```

### Option C – AWS (Terraform)
```bash
cd terraform
terraform init
terraform apply -var="key_pair_name=MY_KEY"
# SSH to EC2, DAG auto-deployed via userdata.sh
```

---

## Data Sources

| Source     | API / URL                                      | Date Range         |
|------------|------------------------------------------------|--------------------|
| Gold price | `yfinance` – ticker `GC=F` (COMEX Gold)        | 2024-01-01 → today |
| War news   | NYT RSS – World, MiddleEast, Europe feeds      | 2024-01-01 → today |

---

## ML Model

| Property      | Value                              |
|---------------|------------------------------------|
| Algorithm     | Random Forest Classifier           |
| Features      | Sentiment scores, article count, rolling sentiment 3d/7d, OHLCV |
| Target        | 1 = next-day close > today's close |
| Preprocessing | StandardScaler                     |
| Schedule      | Weekly retraining (`@weekly`)      |
| Output        | `gold_model_YYYYMMDD.pkl` + metrics JSON |

---

## Testing
```bash
# Full evaluation on hold-out set
python scripts/test_model.py

# Single prediction demo
python scripts/test_model.py --single

# Custom model file
python scripts/test_model.py --model gold_model_20250101.pkl
```

---

## Deliverables Checklist

- [x] `dags/gold_war_pipeline.py` – ETL + ML DAG
- [x] `models/gold_model_latest.pkl` – Trained model (generated on first run)
- [x] `data/gold_prices.csv` – Sample gold price data
- [x] `data/war_news.csv` – Sample war news data
- [x] `data/training_data.csv` – Merged training data
- [x] `scripts/test_model.py` – Model loading + testing script
- [x] `terraform/` – Infrastructure as Code (AWS)
