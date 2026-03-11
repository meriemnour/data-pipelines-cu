from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="gold_war_news_ml_pipeline",
    default_args=default_args,
    description="Fetches gold prices + war news, trains ML model weekly",
    schedule="0 0 * * 0",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["gold", "ml", "etl"],
) as dag:

    def fetch_gold_prices_fn(**context):
        import sys
        sys.path.insert(0, "/home/mimou/airflow/mid-semester/scripts")
        from fetch_gold_prices import fetch_and_save_gold_prices
        path = fetch_and_save_gold_prices()
        context["ti"].xcom_push(key="gold_csv", value=path)

    def fetch_war_news_fn(**context):
        import sys
        sys.path.insert(0, "/home/mimou/airflow/mid-semester/scripts")
        from fetch_war_news import fetch_and_save_war_news
        path = fetch_and_save_war_news()
        context["ti"].xcom_push(key="news_csv", value=path)

    def compute_sentiment_fn(**context):
        import sys
        sys.path.insert(0, "/home/mimou/airflow/mid-semester/scripts")
        from compute_sentiment_and_merge import compute_and_merge
        gold_csv = context["ti"].xcom_pull(key="gold_csv", task_ids="fetch_gold_prices")
        news_csv = context["ti"].xcom_pull(key="news_csv", task_ids="fetch_war_news")
        path = compute_and_merge(gold_csv, news_csv)
        context["ti"].xcom_push(key="training_csv", value=path)

    def train_model_fn(**context):
        import sys
        sys.path.insert(0, "/home/mimou/airflow/mid-semester/scripts")
        from train_model import train_and_save_model
        training_csv = context["ti"].xcom_pull(key="training_csv", task_ids="compute_sentiment_and_merge")
        train_and_save_model(training_csv)

    fetch_gold_prices = PythonOperator(
        task_id="fetch_gold_prices",
        python_callable=fetch_gold_prices_fn
    )

    fetch_war_news = PythonOperator(
        task_id="fetch_war_news",
        python_callable=fetch_war_news_fn
    )

    compute_sentiment = PythonOperator(
        task_id="compute_sentiment_and_merge",
        python_callable=compute_sentiment_fn
    )

    train_model = PythonOperator(
        task_id="train_model",
        python_callable=train_model_fn
    )

    [fetch_gold_prices, fetch_war_news] >> compute_sentiment >> train_model