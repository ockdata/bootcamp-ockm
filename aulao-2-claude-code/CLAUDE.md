# Aulão 2 — Claude Code

## Contexto
- Este material foi criado para aplicar Claude Code sobre o código em `aulao-1-ia-em-producao/etl-monorepo/`.
- As skills e hooks desta pasta assumem o repositório reorganizado por aulão.

## Stack do projeto-alvo

## Stack
- Python 3.11+ com type hints obrigatórios
- GCP: Cloud Run Jobs, BigQuery, Cloud Storage, Secret Manager
- IaC: Terraform 1.5+
- CI/CD: Cloud Build (cloudbuild.yaml)
- Validação: Pydantic v2
- Retry: Tenacity com exponential backoff
- Docker: imagem única para N jobs (monorepo pattern)

## Arquitetura de dados
- Raw: GCS `raw/` em Parquet
- Trusted: BigQuery dataset `trusted` (dados limpos e tipados)
- Refined: BigQuery dataset `refined` (dados consolidados)

## Convenções de código
- Structured logging em JSON (campos obrigatórios: event, job, timestamp, valid_records, dlq_records, duration_seconds, success)
- Dead Letter Queue (DLQ) para registros inválidos — nunca descartar silenciosamente
- Schemas Pydantic em `schemas/` — um arquivo por entidade
- Secrets via Secret Manager, NUNCA em .env commitado ou hardcoded
- Testes com pytest em `tests/` — mínimo: happy path + edge cases + DLQ

## Estrutura de jobs
- Cada job em `aulao-1-ia-em-producao/etl-monorepo/jobs/{job_name}/` com `main.py` + `config.yaml`
- Template base em `jobs/job_template/`
- Scaffold via `make init JOB={nome}` (roda `scripts/init_job.py`)
- Um Terraform file por job: `infra/job_{nome}.tf`

## Módulos compartilhados
- `shared/gcs.py` — helpers GCS
- `shared/bq.py` — helpers BigQuery
- `shared/api_client.py` — HTTP client genérico

## Segurança
- Service account com least privilege (roles específicas, nunca Editor/Owner)
- Security groups: nunca 0.0.0.0/0
- .env é gitignored — usar .env-exemplo como referência

## Terraform
- Provider Google em `aulao-1-ia-em-producao/etl-monorepo/infra/main.tf`
- Módulo reutilizável em `aulao-1-ia-em-producao/etl-monorepo/infra/modules/cloud_run_job/`
- Projeto: mestrado-insper, região: us-central1
