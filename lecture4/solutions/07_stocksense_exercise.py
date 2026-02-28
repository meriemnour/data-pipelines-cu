"""
Lecture 4 - Exercise: StockSense Wikipedia Pageviews ETL

Complete ETL pipeline that fetches Wikipedia pageviews for tracked companies
and saves to CSV, then loads results into a SQLite database.

Pipeline: get_data → extract_gz → fetch_pageviews → add_to_db

Data source: https://dumps.wikimedia.org/other/pageviews/
Format: domain_code page_title view_count response_size (space-separated)
"""

from __future__ import annotations

from pathlib import Path

import airflow.utils.dates
from airflow import DAG

try:
    from airflow.operators.bash import BashOperator
    from airflow.operators.python import PythonOperator
except ImportError:
    # For newer provider-based imports
    from airflow.providers.standard.operators.bash import BashOperator
    from airflow.providers.standard.operators.python import PythonOperator

PAGENAMES = {"Google", "Amazon", "Apple", "Microsoft", "Facebook"}

# Where CSVs will be written (inside container/VM)
OUTPUT_DIR = "/data/stocksense/pageview_counts"

# SQLite DB path for "load" step
DB_PATH = "/data/stocksense/stocksense.db"


def _get_data(year, month, day, hour, output_path, **_):
    """Download Wikipedia pageviews for the given hour (templated op_kwargs)."""
    from urllib import request

    url = (
        f"https://dumps.wikimedia.org/other/pageviews/"
        f"{year}/{year}-{int(month):02d}/"
        f"pageviews-{year}{int(month):02d}{int(day):02d}-{int(hour):02d}0000.gz"
    )
    print(f"Downloading {url}")
    request.urlretrieve(url, output_path)
    print(f"Saved gz to {output_path}")


def _fetch_pageviews(pagenames, execution_date, **context):
    """
    Parse pageviews file, extract counts for tracked companies, save to CSV.

    execution_date is injected by Airflow from task context.
    output_path comes from templates_dict (date/ts-partitioned path).
    """
    result = dict.fromkeys(pagenames, 0)

    # extract_gz produces /tmp/wikipageviews (no .gz)
    with open("/tmp/wikipageviews", "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 4:
                continue

            domain_code, page_title, view_count = parts[0], parts[1], parts[2]

            # Only English + our tracked pages
            if domain_code == "en" and page_title in pagenames:
                try:
                    result[page_title] = int(view_count)
                except ValueError:
                    # keep default 0 if malformed
                    pass

    output_path = context["templates_dict"]["output_path"]
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write("pagename,pageviewcount,datetime\n")
        for pagename, count in result.items():
            f.write(f'"{pagename}",{count},{execution_date}\n')

    print(f"Saved pageview counts to {output_path}")
    print(f"Counts: {result}")
    return result


def _add_to_db(**context):
    """
    Load pageview counts from the CSV into a SQLite database.

    - Reads CSV from context["templates_dict"]["output_path"]
    - Creates table if not exists
    - Inserts rows (upsert by PRIMARY KEY)
    """
    import csv
    import sqlite3

    output_path = context["templates_dict"]["output_path"]

    # Ensure parent directory exists
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Unique key prevents duplicates per pagename per execution datetime
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pageviews (
            pagename TEXT NOT NULL,
            pageviewcount INTEGER NOT NULL,
            datetime TEXT NOT NULL,
            PRIMARY KEY (pagename, datetime)
        )
        """
    )

    with open(output_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            pagename = r["pagename"].strip().strip('"')
            pageviewcount = int(r["pageviewcount"])
            dt = r["datetime"]
            rows.append((pagename, pageviewcount, dt))

    cur.executemany(
        """
        INSERT INTO pageviews (pagename, pageviewcount, datetime)
        VALUES (?, ?, ?)
        ON CONFLICT(pagename, datetime) DO UPDATE SET
            pageviewcount = excluded.pageviewcount
        """,
        rows,
    )

    conn.commit()
    conn.close()

    print(f"Inserted {len(rows)} rows into {DB_PATH} from {output_path}")


dag = DAG(
    dag_id="lecture4_stocksense_exercise",
    start_date=airflow.utils.dates.days_ago(1),
    schedule="@hourly",
    catchup=False,
    max_active_runs=1,
    tags=["lecture4", "exercise", "stocksense", "etl"],
)

get_data = PythonOperator(
    task_id="get_data",
    python_callable=_get_data,
    op_kwargs={
        "year": "{{ execution_date.year }}",
        "month": "{{ execution_date.month }}",
        "day": "{{ execution_date.day }}",
        "hour": "{{ execution_date.hour }}",
        "output_path": "/tmp/wikipageviews.gz",
    },
    dag=dag,
)

extract_gz = BashOperator(
    task_id="extract_gz",
    bash_command="gunzip -f /tmp/wikipageviews.gz",
    dag=dag,
)

fetch_pageviews = PythonOperator(
    task_id="fetch_pageviews",
    python_callable=_fetch_pageviews,
    op_kwargs={"pagenames": PAGENAMES},
    # Use ts_nodash so hourly runs don't overwrite the same YYYY-MM-DD file
    templates_dict={"output_path": f"{OUTPUT_DIR}/{{{{ ts_nodash }}}}.csv"},
    dag=dag,
)

add_to_db = PythonOperator(
    task_id="add_to_db",
    python_callable=_add_to_db,
    templates_dict={"output_path": f"{OUTPUT_DIR}/{{{{ ts_nodash }}}}.csv"},
    dag=dag,
)

get_data >> extract_gz >> fetch_pageviews >> add_to_db