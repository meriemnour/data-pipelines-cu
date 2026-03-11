# =============================================================================
# Terraform — Gold Price & War News ML Pipeline Infrastructure
# =============================================================================
# Provisions: EC2 (Airflow), S3 (data/models/dags), IAM, Security Group, CloudWatch

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" { region = var.aws_region }

# ── Variables ─────────────────────────────────────────────────────────────────
variable "aws_region"             { default = "us-east-1" }
variable "project_name"           { default = "gold-ml-pipeline" }
variable "environment"            { default = "dev" }
variable "instance_type"          { default = "t3.medium" }
variable "key_pair_name"          { default = "" }
variable "airflow_admin_password" { default = "ChangeMe123!"; sensitive = true }

locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ── Random suffix for unique S3 bucket name ───────────────────────────────────
resource "random_id" "suffix" { byte_length = 4 }

# ── S3 Bucket ─────────────────────────────────────────────────────────────────
resource "aws_s3_bucket" "pipeline" {
  bucket        = "${var.project_name}-${var.environment}-${random_id.suffix.hex}"
  force_destroy = true
  tags          = local.common_tags
}

resource "aws_s3_bucket_versioning" "pipeline" {
  bucket = aws_s3_bucket.pipeline.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "pipeline" {
  bucket = aws_s3_bucket.pipeline.id
  rule { apply_server_side_encryption_by_default { sse_algorithm = "AES256" } }
}

# ── IAM Role ──────────────────────────────────────────────────────────────────
resource "aws_iam_role" "airflow_ec2" {
  name = "${var.project_name}-ec2-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy" "s3_access" {
  name = "${var.project_name}-s3"
  role = aws_iam_role.airflow_ec2.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:*"], Resource = [aws_s3_bucket.pipeline.arn, "${aws_s3_bucket.pipeline.arn}/*"] },
      { Effect = "Allow", Action = ["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"], Resource = "*" }
    ]
  })
}

resource "aws_iam_instance_profile" "airflow" {
  name = "${var.project_name}-profile"
  role = aws_iam_role.airflow_ec2.name
}

# ── Security Group ────────────────────────────────────────────────────────────
resource "aws_security_group" "airflow" {
  name        = "${var.project_name}-sg"
  description = "Airflow EC2 security group"
  ingress { from_port = 8080, to_port = 8080, protocol = "tcp", cidr_blocks = ["0.0.0.0/0"], description = "Airflow UI" }
  ingress { from_port = 22,   to_port = 22,   protocol = "tcp", cidr_blocks = ["0.0.0.0/0"], description = "SSH" }
  egress  { from_port = 0,    to_port = 0,    protocol = "-1",  cidr_blocks = ["0.0.0.0/0"] }
  tags = local.common_tags
}

# ── CloudWatch Log Group ──────────────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "airflow" {
  name              = "/aws/ec2/${var.project_name}/airflow"
  retention_in_days = 30
  tags              = local.common_tags
}

# ── AMI — Ubuntu 22.04 ────────────────────────────────────────────────────────
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter { name = "name",                values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"] }
  filter { name = "virtualization-type", values = ["hvm"] }
}

# ── EC2 Instance ──────────────────────────────────────────────────────────────
resource "aws_instance" "airflow" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  iam_instance_profile   = aws_iam_instance_profile.airflow.name
  vpc_security_group_ids = [aws_security_group.airflow.id]
  key_name               = var.key_pair_name != "" ? var.key_pair_name : null

  root_block_device { volume_size = 30, volume_type = "gp3", encrypted = true }

  user_data = base64encode(templatefile("${path.module}/airflow_setup.sh", {
    s3_bucket              = aws_s3_bucket.pipeline.id
    aws_region             = var.aws_region
    airflow_admin_password = var.airflow_admin_password
    project_name           = var.project_name
  }))

  tags = merge(local.common_tags, { Name = "${var.project_name}-airflow" })
}

resource "aws_eip" "airflow" {
  instance = aws_instance.airflow.id
  domain   = "vpc"
  tags     = local.common_tags
}

# ── Outputs ───────────────────────────────────────────────────────────────────
output "airflow_url"      { value = "http://${aws_eip.airflow.public_ip}:8080" }
output "airflow_ip"       { value = aws_eip.airflow.public_ip }
output "s3_bucket_name"   { value = aws_s3_bucket.pipeline.id }
output "ssh_command"      { value = var.key_pair_name != "" ? "ssh -i ${var.key_pair_name}.pem ubuntu@${aws_eip.airflow.public_ip}" : "No key pair configured" }
