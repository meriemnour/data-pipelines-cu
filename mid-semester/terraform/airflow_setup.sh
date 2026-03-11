#!/bin/bash
# =============================================================================
# airflow_setup.sh
# Bootstraps Apache Airflow on Ubuntu 22.04 (EC2 user_data)
# Templated by Terraform — variables injected at provision time
# =============================================================================

set -euo pipefail
exec > >(tee /var/log/airflow_setup.log) 2>&1

echo "===== Starting Airflow setup: $(date) ====="

# ── System packages ───────────────────────────────────────────────────
apt-get update -y
apt-get install -y python3-pip python3-venv git awscli curl unzip

# ── Environment variables ─────────────────────────────────────────────
export AIRFLOW_HOME=/opt/airflow
export AIRFLOW_DATA_DIR=/opt/airflow/data
export AIRFLOW_MODELS_DIR=/opt/airflow/models
export S3_BUCKET="${s3_bucket}"
export AWS_DEFAULT_REGION="${aws_region}"
export PROJECT_NAME="${project_name}"

# Persist env vars for all future sessions
cat >> /etc/environment << EOF
AIRFLOW_HOME=/opt/airflow
AIRFLOW_DATA_DIR=/opt/airflow/data
AIRFLOW_MODELS_DIR=/opt/airflow/models
S3_BUCKET=${s3_bucket}
AWS_DEFAULT_REGION=${aws_region}
PROJECT_NAME=${project_name}
EOF

# ── Create directories ────────────────────────────────────────────────
mkdir -p $AIRFLOW_HOME/dags $AIRFLOW_HOME/scripts $AIRFLOW_DATA_DIR $AIRFLOW_MODELS_DIR
mkdir -p $AIRFLOW_HOME/logs $AIRFLOW_HOME/plugins

# ── Python virtual environment ────────────────────────────────────────
python3 -m venv /opt/airflow-venv
source /opt/airflow-venv/bin/activate

pip install --upgrade pip

# Install Airflow (constraint file ensures compatible versions)
AIRFLOW_VERSION=2.9.2
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d. -f1,2)
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip install "apache-airflow==${AIRFLOW_VERSION}" --constraint "$CONSTRAINT_URL"

# Install ML and data dependencies
pip install \
  yfinance==0.2.40 \
  feedparser==6.0.11 \
  vaderSentiment==3.3.2 \
  scikit-learn==1.4.2 \
  pandas==2.2.2 \
  numpy==1.26.4 \
  joblib==1.4.2 \
  boto3==1.34.100

# ── Initialise Airflow database ───────────────────────────────────────
export AIRFLOW__CORE__DAGS_FOLDER=$AIRFLOW_HOME/dags
export AIRFLOW__CORE__EXECUTOR=SequentialExecutor
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=sqlite:///$AIRFLOW_HOME/airflow.db
export AIRFLOW__WEBSERVER__SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
export AIRFLOW__CORE__LOAD_EXAMPLES=False

airflow db migrate

# Create admin user
airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password "${airflow_admin_password}"

# ── Download DAGs and scripts from S3 ────────────────────────────────
# (Sync happens on first run — files must be uploaded to S3 first)
aws s3 sync s3://${s3_bucket}/dags/    $AIRFLOW_HOME/dags/    || echo "WARN: No DAGs in S3 yet"
aws s3 sync s3://${s3_bucket}/scripts/ $AIRFLOW_HOME/scripts/ || echo "WARN: No scripts in S3 yet"

# ── Create systemd service for Airflow webserver ──────────────────────
cat > /etc/systemd/system/airflow-webserver.service << 'SVCEOF'
[Unit]
Description=Airflow Webserver
After=network.target

[Service]
EnvironmentFile=/etc/environment
Environment=AIRFLOW_HOME=/opt/airflow
Environment=AIRFLOW__CORE__EXECUTOR=SequentialExecutor
Environment=AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=sqlite:////opt/airflow/airflow.db
Environment=AIRFLOW__CORE__LOAD_EXAMPLES=False
User=ubuntu
Group=ubuntu
ExecStart=/opt/airflow-venv/bin/airflow webserver --port 8080
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
SVCEOF

# ── Create systemd service for Airflow scheduler ──────────────────────
cat > /etc/systemd/system/airflow-scheduler.service << 'SVCEOF'
[Unit]
Description=Airflow Scheduler
After=network.target

[Service]
EnvironmentFile=/etc/environment
Environment=AIRFLOW_HOME=/opt/airflow
Environment=AIRFLOW__CORE__EXECUTOR=SequentialExecutor
Environment=AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=sqlite:////opt/airflow/airflow.db
Environment=AIRFLOW__CORE__LOAD_EXAMPLES=False
User=ubuntu
Group=ubuntu
ExecStart=/opt/airflow-venv/bin/airflow scheduler
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
SVCEOF

# ── Fix ownership ─────────────────────────────────────────────────────
chown -R ubuntu:ubuntu /opt/airflow /opt/airflow-venv

# ── Start services ────────────────────────────────────────────────────
systemctl daemon-reload
systemctl enable airflow-webserver airflow-scheduler
systemctl start airflow-webserver airflow-scheduler

echo "===== Airflow setup complete: $(date) ====="
echo "  Web UI: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8080"
echo "  Username: admin"
echo "  S3 bucket: ${s3_bucket}"
