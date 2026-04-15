# Aulão 1 — IA em Produção

Pelas apresentações e pelo histórico de commits de `2026-02-19`, este aulão reúne dois blocos principais:

- `etl-monorepo/`: plataforma de dados, infraestrutura e jobs ETL.
- `agente-monitoramento/`: observabilidade, RAG e agente de monitoramento.

## Projeto base

### ETL Monorepo

> Monorepo ETL with Cloud Run Jobs + BigQuery + Terraform

[![GCP](https://img.shields.io/badge/GCP-Cloud_Run-4285F4?logo=google-cloud)](https://cloud.google.com/run)
[![Terraform](https://img.shields.io/badge/IaC-Terraform-7B42BC?logo=terraform)](https://www.terraform.io/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://www.python.org/)

---

## About

This lecture folder demonstrates how to build resilient data pipelines in production using:

- **1 Docker image** for N independent jobs (monorepo pattern)
- **Cloud Run Jobs** — serverless, pay-per-execution
- **Retry logic** with exponential backoff (Tenacity)
- **Schema validation** with Pydantic
- **Dead Letter Queue** for invalid records
- **100% Infrastructure as Code** (Terraform)
- **Observability** with structured logging

---

## Architecture

```
+-------------------+
|  Cloud Scheduler  |  <- Daily triggers
+--------+----------+
         |
         v
+-------------------+
|   Cloud Run Job   |  <- Serverless execution (single image)
+--------+----------+
         |
    +----+----+
    |  Retry  |  <- Tenacity: 3 attempts, exponential backoff
    +----+----+
         |
    +----v------+
    |  Pydantic |  <- Schema validation
    +----+------+
         |
    +----+--------+----------+
    v             v
+---------+  +----------+
| BigQuery|  |   DLQ    |  <- Dead Letter Queue
|  Table  |  |  Table   |
+---------+  +----------+
```

---

## Project Structure

```
bootcamp-ockm/
└── aulao-1-ia-em-producao/
    ├── README.md
    ├── agente-monitoramento/            # observabilidade + RAG + alertas
    └── etl-monorepo/
        ├── infra/                       # Terraform (IaC)
        ├── jobs/                        # ETL job modules
        ├── scripts/                     # Utility and scaffolding scripts
        ├── shared/                      # Shared utility modules
        ├── workflows/                   # GCP Workflows definitions
        ├── docs/
        ├── cloudbuild.yaml              # CI/CD pipeline
        ├── Dockerfile
        ├── Makefile
        └── requirements.txt
```

---

## Prerequisites

- Python 3.11+
- Docker
- GCP account with billing enabled
- Terraform 1.5+
- [gcloud CLI](https://cloud.google.com/sdk/docs/install)

---

## Quick Start

### 1. Local setup

```bash
git clone https://github.com/seu-usuario/bootcamp-ockm.git
cd bootcamp-ockm/aulao-1-ia-em-producao/etl-monorepo

# Create virtual environment and install dependencies
make setup
source .venv/bin/activate

# Configure GCP credentials
gcloud auth login
gcloud auth application-default login
gcloud config set project mestrado-insper
```

### 2. Run a job locally

```bash
# Copy .env.example and fill in credentials
cp .env.example .env

make run-job JOB=job_template
```

### 3. Deploy infrastructure

```bash
make infra-init
make infra-plan
make infra-apply
```

### 4. Build and push Docker image

```bash
# Configure Docker auth (once)
make auth-configure

# Build and push
make deploy
```

### 5. Execute a job on Cloud Run

```bash
make cloud-run JOB=job-template
```

---

## Creating a New Job

A single command scaffolds the job code and the Terraform resource together:

```bash
make init JOB=ingest_sales
```

This creates:

```
jobs/ingest_sales/
    main.py          <- implement extraction logic here
    config.yaml

infra/
    job_ingest_sales.tf   <- Cloud Run Job resource, ready to apply
```

Then implement the job, deploy the image, and provision the infrastructure:

```bash
# 1. Implement
#    Edit jobs/ingest_sales/main.py

# 2. Deploy image
make deploy

# 3. Provision Cloud Run Job
make infra-plan
make infra-apply

# 4. Execute
make cloud-run JOB=ingest-sales
```

---

## Makefile Reference

### Local development

```bash
make setup                        # Create venv and install dependencies
make run-job JOB=<job>            # Run job locally (loads .env)
make test                         # Run unit tests
make clean                        # Remove __pycache__, .pyc, .pytest_cache
```

### Docker

```bash
make auth-configure               # Configure Docker auth for Artifact Registry (once)
make docker-build                 # Build image locally
make docker-run JOB=<job>         # Run via Docker (loads .env)
make deploy                       # Build + tag + push to Artifact Registry
```

### Infrastructure (Terraform)

```bash
make infra-init                   # terraform init
make infra-plan                   # terraform plan
make infra-apply                  # terraform apply
```

### Cloud Run

```bash
make cloud-run JOB=<job>          # Execute job on GCP
```

### Scaffolding

```bash
make init JOB=<job>               # Create new job + Terraform file
make workflow-init WF=<workflow>  # Create new workflow
```

### Workflows

```bash
make workflow-validate            # Validate all workflow.yaml files
make workflow-run WF=<workflow>   # Execute workflow on GCP
make workflow-status WF=<wf>      # Show last 5 executions
make workflow-list                # List local and GCP workflows
```

---

## GCP Configuration

| Setting | Value |
|---------|-------|
| Project ID | `mestrado-insper` |
| Region | `us-central1` |
| Artifact Registry | `data-etl-repo` |
| Image | `etl-monorepo` |
| Service Account | `etl-runner@mestrado-insper.iam.gserviceaccount.com` |

The service account is provisioned with the following roles:

- `roles/storage.objectAdmin` — read/write GCS
- `roles/bigquery.dataEditor` — write to BigQuery tables
- `roles/bigquery.jobUser` — execute BigQuery jobs
- `roles/secretmanager.secretAccessor` — read secrets

---

## Data Layers

| Layer | Location | Description |
|-------|----------|-------------|
| Raw | GCS `raw/` | Original data in Parquet |
| Trusted | BigQuery `trusted` | Cleaned and typed data |
| Refined | BigQuery `refined` | Consolidated and enriched data |

---

## Security

- Secrets stored in Secret Manager, never in code or environment files committed to git
- Service account follows least privilege principle
- Audit logs enabled by default on GCP
- `.env` is gitignored — use `.env.example` as reference

---

## CI/CD

`cloudbuild.yaml` handles build and push to Artifact Registry on every commit.
The substitution variable `_JOB` controls which job image is built (defaults to `job_template`).

```bash
# Manually trigger via gcloud
gcloud builds submit --config cloudbuild.yaml --substitutions _JOB=ingest_sales .
```

---

## Observability

All jobs emit structured JSON logs compatible with Cloud Logging:

```json
{
  "event": "ingest_complete",
  "job": "ingest_sales",
  "timestamp": "2026-02-19T07:00:00Z",
  "valid_records": 9850,
  "dlq_records": 5,
  "duration_seconds": 45.2,
  "success": true
}
```

---

## Resources

- [GCP Cloud Run Jobs documentation](https://cloud.google.com/run/docs/create-jobs)
- [Terraform Google Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Tenacity retry library](https://tenacity.readthedocs.io/)
- [Pydantic data validation](https://docs.pydantic.dev/)
