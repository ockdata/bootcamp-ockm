# Architecture Guide

> Guia completo para replicar esta arquitetura ETL em outros projetos.
> Otimizado para uso com Claude Code.

---

## Visão Geral

Monorepo ETL em Python sobre GCP, seguindo o padrão **Medallion Architecture** (Raw → Trusted → Refined). Cada job roda como **Cloud Run Job**, orquestrado por **GCP Workflows** e agendado via **Cloud Scheduler**. A infraestrutura é provisionada com **Terraform** usando auto-discovery de jobs e workflows.

```
┌─────────────────────────────────────────────────────────┐
│                    ORQUESTRAÇÃO                         │
│  Cloud Scheduler → GCP Workflows → Cloud Run Jobs       │
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │ Ingest A │   │ Ingest B │   │ Ingest C │   ← Jobs paralelos
   └────┬─────┘   └────┬─────┘   └────┬─────┘
        │               │               │
        ▼               ▼               ▼
   ┌─────────────────────────────────────────┐
   │           GCS (Raw / Bronze)            │  ← Imutável, audit trail
   └────────────────────┬────────────────────┘
                        │
                        ▼
   ┌─────────────────────────────────────────┐
   │       BigQuery — Trusted (Silver)       │  ← Schema normalizado
   └────────────────────┬────────────────────┘
                        │
                        ▼
   ┌─────────────────────────────────────────┐
   │       BigQuery — Refined (Gold)         │  ← Consolidado + métricas
   └─────────────────────────────────────────┘
```

---

## Estrutura do Projeto

```
projeto/
├── jobs/                          # Jobs ETL (1 pasta por job)
│   ├── ingest_exemplo/
│   │   ├── config.yaml            # Configuração do Cloud Run Job
│   │   └── main.py                # Código do job
│   └── transform_exemplo/
│       ├── config.yaml
│       └── main.py
├── workflows/                     # Orquestração (1 pasta por workflow)
│   ├── daily_pipeline/
│   │   └── workflow.yaml          # Definição do GCP Workflow
│   └── ...
├── shared/                        # Bibliotecas compartilhadas
│   ├── __init__.py
│   ├── gcs.py                     # Operações GCS (save_to_raw)
│   ├── bq.py                      # Operações BigQuery (load, query)
│   └── api_client.py              # Clientes de API externos
├── infra/                         # Terraform IaC
│   ├── main.tf                    # Recursos GCP (APIs, storage, BQ, IAM)
│   ├── jobs.tf                    # Auto-discovery de Cloud Run Jobs
│   ├── workflows.tf               # Auto-discovery de Workflows + Scheduler
│   ├── variables.tf               # Variáveis
│   └── templates/
│       └── workflow.yaml.tftpl    # Template para Workflows
├── scripts/                       # Scripts utilitários
├── docs/                          # Documentação
├── Dockerfile                     # Imagem Docker (multi-job)
├── cloudbuild.yaml                # CI/CD no Cloud Build
├── Makefile                       # Automação local
├── requirements.txt               # Dependências Python
└── README.md
```

### Regra de ouro

Para adicionar um novo job:
1. Crie `jobs/{nome}/config.yaml` + `main.py`
2. Rode `make infra-plan` — o Terraform detecta automaticamente
3. Rode `make infra-apply` — o Cloud Run Job é criado

Para adicionar um novo workflow:
1. Crie `workflows/{nome}/workflow.yaml`
2. Rode `make infra-plan && make infra-apply`

---

## 1. Job — Anatomia e Padrão

### config.yaml

```yaml
job:
  name: ingest-exemplo          # Nome no Cloud Run (kebab-case)
  description: "Ingestão de dados do sistema X"
  schedule: ""                  # Vazio se orquestrado por workflow
  env:
    - name: JOB_NAME
      value: ingest_exemplo     # Deve bater com o nome da pasta
  resources:                    # Opcional — customiza CPU/memória
    cpu: "1"
    memory: "512Mi"
```

### main.py — Padrão de Ingestão

```python
import logging
import pandas as pd
from datetime import datetime

from shared.bq import load_from_dataframe, query_bigquery
from shared.gcs import save_to_raw

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_data_referencia() -> str:
    """Determina a data de referência (D-2 útil) a partir do calendário de feriados."""
    query = """
        SELECT FORMAT_DATE('%Y-%m-%d', data) as data_ref
        FROM trusted.feriados_anbima
        WHERE data < CURRENT_DATE('America/Sao_Paulo')
          AND eh_dia_util = 1
        ORDER BY data DESC
        LIMIT 1 OFFSET 1
    """
    df = query_bigquery(query)
    return df['data_ref'].iloc[0]


def extract(data_ref: str) -> pd.DataFrame:
    """Extrai dados da fonte (API, S3, banco, etc)."""
    # Implementar extração aqui
    ...


def transform(df: pd.DataFrame, data_ref: str) -> pd.DataFrame:
    """Normaliza schema, converte tipos, adiciona metadados."""
    df['_source'] = 'exemplo'
    df['dt'] = data_ref
    df['_processed_at'] = datetime.now().isoformat()
    return df


def main():
    logger.info("Iniciando job ingest_exemplo")

    # 1. Data de referência determinística
    data_ref = get_data_referencia()
    logger.info(f"Data de referência: {data_ref}")

    # 2. Extração
    df_raw = extract(data_ref)
    logger.info(f"Extraídos {len(df_raw)} registros")

    # 3. Salvar raw (imutável, audit trail)
    save_to_raw(df_raw, dataset_name="exemplo", dt=data_ref)

    # 4. Transformação
    df = transform(df_raw, data_ref)

    # 5. Carga idempotente (WRITE_TRUNCATE na partição)
    load_from_dataframe(
        df,
        dataset_id='trusted',
        table_name='exemplo',
        date_partition=data_ref
    )

    logger.info(f"Job finalizado. {len(df)} registros carregados.")


if __name__ == '__main__':
    main()
```

### main.py — Padrão de Transformação

```python
def main():
    data_ref = get_data_referencia()

    # 1. Carregar todas as tabelas staging
    df = load_staging_tables(data_ref)

    # 2. Lookups de dimensão
    df = lookup_dimensions(df)

    # 3. Cálculo de métricas
    df = calculate_metrics(df, data_ref)

    # 4. Tipagem final
    df = enforce_types(df)

    # 5. Carga no refined
    load_from_dataframe(df, 'refined', 'tabela_final', date_partition=data_ref)
```

### Garantias do padrão

| Propriedade | Como é garantida |
|---|---|
| **Idempotência** | `WRITE_TRUNCATE` por partição — re-executar sobrescreve a mesma partição |
| **Imutabilidade** | Raw salvo em GCS antes de qualquer transformação |
| **Determinismo** | Data de referência vem de query no calendário de feriados |
| **Rastreabilidade** | Campos `_source`, `dt`, `_processed_at` em todo registro |

---

## 2. Shared Libraries

### shared/gcs.py

```python
from google.cloud import storage
import pandas as pd

PROJECT_ID = "seu-projeto-gcp"
BUCKET_NAME = f"{PROJECT_ID}-datalake-raw"

def save_to_raw(df: pd.DataFrame, dataset_name: str, file_format='json', dt=None) -> str:
    """
    Salva DataFrame no GCS como arquivo raw.
    URI: gs://{bucket}/{dataset_name}/dt={YYYY-MM-DD}/{dataset_name}.{format}
    """
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(BUCKET_NAME)
    blob_path = f"{dataset_name}/dt={dt}/{dataset_name}.{file_format}"
    blob = bucket.blob(blob_path)

    if file_format == 'json':
        blob.upload_from_string(df.to_json(orient='records', lines=True))
    elif file_format == 'parquet':
        blob.upload_from_string(df.to_parquet())

    uri = f"gs://{BUCKET_NAME}/{blob_path}"
    logger.info(f"Salvo em {uri}")
    return uri
```

### shared/bq.py

```python
from google.cloud import bigquery
import pandas as pd

PROJECT_ID = "seu-projeto-gcp"
client = bigquery.Client(project=PROJECT_ID)

def query_bigquery(query: str) -> pd.DataFrame:
    """Executa SQL no BigQuery e retorna DataFrame."""
    return client.query(query).to_dataframe()

def load_from_dataframe(df, dataset_id, table_name, date_partition=None):
    """
    Carrega DataFrame no BigQuery.
    Se date_partition fornecido: usa partition decorator + WRITE_TRUNCATE.
    """
    table_ref = f"{PROJECT_ID}.{dataset_id}.{table_name}"

    if date_partition:
        partition_str = date_partition.replace('-', '')
        table_ref = f"{table_ref}${partition_str}"

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )

    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()
    logger.info(f"Carregados {len(df)} registros em {table_ref}")

def load_from_gcs(dataset_name, dataset_id, table_name, date_partition):
    """Carrega JSON do GCS direto para BigQuery via partition decorator."""
    uri = f"gs://{PROJECT_ID}-datalake-raw/{dataset_name}/dt={date_partition}/*.json"
    table_ref = f"{PROJECT_ID}.{dataset_id}.{table_name}${date_partition.replace('-','')}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )

    job = client.load_table_from_uri(uri, table_ref, job_config=job_config)
    job.result()
```

---

## 3. Infraestrutura (Terraform)

### Auto-discovery de Jobs (`infra/jobs.tf`)

```hcl
locals {
  job_configs = {
    for f in fileset("${path.module}/../jobs", "*/config.yaml") :
    dirname(f) => yamldecode(file("${path.module}/../jobs/${f}"))
  }
}

resource "google_cloud_run_v2_job" "jobs" {
  for_each = local.job_configs

  name     = each.value.job.name
  location = var.region

  template {
    template {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repo_name}/etl-monorepo:latest"

        dynamic "env" {
          for_each = each.value.job.env
          content {
            name  = env.value.name
            value = env.value.value
          }
        }

        resources {
          limits = {
            cpu    = try(each.value.job.resources.cpu, "1")
            memory = try(each.value.job.resources.memory, "512Mi")
          }
        }
      }

      service_account = google_service_account.etl_job_runner.email
      timeout         = "1800s"
      max_retries     = 1
    }
  }
}
```

### Auto-discovery de Workflows (`infra/workflows.tf`)

```hcl
locals {
  workflow_configs = {
    for f in fileset("${path.module}/../workflows", "*/workflow.yaml") :
    dirname(f) => yamldecode(file("${path.module}/../workflows/${f}"))
  }
}

resource "google_workflows_workflow" "workflows" {
  for_each = local.workflow_configs

  name            = each.value.name
  region          = var.region
  service_account = google_service_account.workflow_runner.id
  source_contents = templatefile(
    "${path.module}/templates/workflow.yaml.tftpl",
    { steps = each.value.steps, project_id = var.project_id, region = var.region }
  )
}

resource "google_cloud_scheduler_job" "workflow_triggers" {
  for_each = {
    for k, v in local.workflow_configs : k => v if try(v.schedule, "") != ""
  }

  name      = "${each.value.name}-trigger"
  schedule  = each.value.schedule
  time_zone = each.value.timezone

  http_target {
    uri         = "https://workflowexecutions.googleapis.com/v1/${google_workflows_workflow.workflows[each.key].id}/executions"
    http_method = "POST"
    oauth_token {
      service_account_email = google_service_account.workflow_runner.email
    }
  }
}
```

### Recursos Base (`infra/main.tf`)

```hcl
# APIs necessárias
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "workflows.googleapis.com",
    "cloudscheduler.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "bigquery.googleapis.com",
    "storage.googleapis.com",
    "secretmanager.googleapis.com",
    "logging.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

# Artifact Registry
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = var.repo_name
  format        = "DOCKER"
}

# GCS Bucket (Raw Layer)
resource "google_storage_bucket" "raw" {
  name     = "${var.project_id}-datalake-raw"
  location = var.region
}

# BigQuery Datasets
resource "google_bigquery_dataset" "trusted" {
  dataset_id = "trusted"
  location   = var.region
}

resource "google_bigquery_dataset" "refined" {
  dataset_id = "refined"
  location   = var.region
}

# Service Accounts
resource "google_service_account" "etl_job_runner" {
  account_id   = "etl-job-runner"
  display_name = "ETL Job Runner"
}

resource "google_service_account" "workflow_runner" {
  account_id   = "workflow-runner"
  display_name = "Workflow Runner"
}

# IAM — Job Runner
resource "google_project_iam_member" "job_runner_roles" {
  for_each = toset([
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/storage.objectAdmin",
    "roles/logging.logWriter",
    "roles/secretmanager.secretAccessor",
  ])
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.etl_job_runner.email}"
}

# IAM — Workflow Runner
resource "google_project_iam_member" "workflow_runner_roles" {
  for_each = toset([
    "roles/run.developer",
    "roles/workflows.invoker",
    "roles/logging.logWriter",
  ])
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.workflow_runner.email}"
}
```

---

## 4. Docker & CI/CD

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY jobs/ ./jobs/

ENV PYTHONPATH=/app

# Entry point dinâmico: JOB_NAME define qual job executar
CMD ["sh", "-c", "python -m jobs.${JOB_NAME}.main"]
```

**Conceito**: Uma única imagem Docker contém todos os jobs. A variável `JOB_NAME` (definida no `config.yaml` de cada job) determina qual módulo Python será executado.

### cloudbuild.yaml

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/etl-monorepo:${SHORT_SHA}'
      - '.'
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPO}/etl-monorepo:${SHORT_SHA}'

substitutions:
  _REGION: us-central1
  _REPO: data-etl-repo

options:
  logging: CLOUD_LOGGING_ONLY
```

---

## 5. Workflows — Orquestração

### workflow.yaml (exemplo)

```yaml
name: daily-pipeline
schedule: "0 7 * * *"           # 7h diariamente
timezone: "America/Sao_Paulo"

steps:
  - name: parallel-ingest
    parallel:
      - job: ingest-exemplo-a
      - job: ingest-exemplo-b
      - job: ingest-exemplo-c

  - name: transform
    job: transform-exemplo
```

O Terraform lê esse arquivo e gera o workflow GCP real usando o template `workflow.yaml.tftpl`. Os steps `parallel` executam jobs em paralelo; steps sequenciais esperam o anterior terminar.

---

## 6. Makefile — Comandos Essenciais

```makefile
PROJECT_ID := seu-projeto-gcp
REGION     := us-central1
REPO       := data-etl-repo
IMAGE      := $(REGION)-docker.pkg.dev/$(PROJECT_ID)/$(REPO)/etl-monorepo

# ─── Desenvolvimento Local ───
setup:
	python -m venv .venv && .venv/bin/pip install -r requirements.txt

run-job:
	PYTHONPATH=. JOB_NAME=$(JOB) python -m jobs.$(JOB).main

# ─── Docker ───
docker-build:
	docker build -t etl-monorepo .

docker-run:
	docker run --rm \
		-e JOB_NAME=$(JOB) \
		-e GOOGLE_APPLICATION_CREDENTIALS=/creds/key.json \
		-v ~/.config/gcloud/application_default_credentials.json:/creds/key.json \
		etl-monorepo

# ─── Infraestrutura ───
infra-init:
	cd infra && terraform init

infra-plan:
	cd infra && terraform plan

infra-apply:
	cd infra && terraform apply

# ─── Cloud Run ───
cloud-run:
	gcloud run jobs execute $(JOB) --region $(REGION) --wait

# ─── Workflows ───
workflow-run:
	gcloud workflows run $(WF) --location $(REGION)

# ─── Scaffolding ───
init:
	@mkdir -p jobs/$(JOB)
	@echo 'job:\n  name: $(JOB)\n  description: ""\n  schedule: ""\n  env:\n    - name: JOB_NAME\n      value: $(JOB)' > jobs/$(JOB)/config.yaml
	@echo 'from shared.bq import load_from_dataframe, query_bigquery\nfrom shared.gcs import save_to_raw\n\ndef main():\n    pass\n\nif __name__ == "__main__":\n    main()' > jobs/$(JOB)/main.py
	@echo "Job $(JOB) criado em jobs/$(JOB)/"

# ─── Testes ───
test:
	pytest tests/ -v
```

---

## 7. Dados — Convenções

### Particionamento

Todas as tabelas são particionadas por `dt` (data de referência, tipo `DATE`).

```
# GCS: partição por diretório Hive-style
gs://bucket/dataset/dt=2025-01-21/arquivo.json

# BigQuery: partition decorator
projeto.trusted.tabela$20250121
```

### Schema Padrão para Tabelas de Ingestão

Cada tabela `trusted.estoque_*` segue um schema normalizado:

| Campo | Tipo | Descrição |
|---|---|---|
| `dt` | `DATE` | Data de referência |
| `_source` | `STRING` | Identificador da fonte |
| `_processed_at` | `TIMESTAMP` | Momento do processamento |
| `CNPJ_FUNDO` | `STRING` | CNPJ do fundo |
| `VALOR_NOMINAL` | `FLOAT64` | Valor nominal do recebível |
| `VALOR_PRESENTE` | `FLOAT64` | Valor presente |
| `DATA_VENCIMENTO` | `DATE` | Data de vencimento |
| ... | ... | Campos específicos da fonte |

### Camadas

| Camada | Storage | Dataset BQ | Propósito |
|---|---|---|---|
| **Raw** | GCS | — | JSON bruto, imutável, audit trail |
| **Trusted** | — | `trusted` | Schema normalizado, particionado, uma tabela por fonte |
| **Refined** | — | `refined` | Visão consolidada, métricas calculadas, pronto para consumo |
| **Business Input** | — | `business_input` | Uploads manuais (Excel) |

---

## 8. Segurança

### Credenciais

Nunca em código. Sempre via **Secret Manager**:

```python
from google.cloud import secretmanager

def get_secret(secret_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")
```

### Service Accounts

| Account | Usado por | Permissões |
|---|---|---|
| `etl-job-runner` | Cloud Run Jobs | BQ dataEditor, jobUser, Storage objectAdmin, SecretManager accessor |
| `workflow-runner` | GCP Workflows | Cloud Run developer, Workflows invoker |

---

## 9. Como Replicar para Novo Projeto

### Passo a passo

```bash
# 1. Criar estrutura
mkdir -p {jobs,workflows,shared,infra/templates,scripts,docs}

# 2. Copiar arquivos base
# - Dockerfile
# - cloudbuild.yaml
# - Makefile (ajustar PROJECT_ID, REGION)
# - requirements.txt
# - infra/*.tf (ajustar variáveis)
# - shared/*.py (ajustar PROJECT_ID)

# 3. Configurar GCP
gcloud config set project SEU_PROJETO
gcloud auth application-default login

# 4. Inicializar infra
make infra-init
make infra-apply

# 5. Criar primeiro job
make init JOB=meu_primeiro_job
# Editar jobs/meu_primeiro_job/main.py

# 6. Testar local
make run-job JOB=meu_primeiro_job

# 7. Deploy
git push  # Cloud Build cria imagem
make infra-apply  # Terraform cria Cloud Run Job

# 8. Executar na nuvem
make cloud-run JOB=meu-primeiro-job
```

### Checklist de Adaptação

- [ ] Atualizar `PROJECT_ID` no Makefile e shared libs
- [ ] Atualizar `REGION` se diferente de `us-central1`
- [ ] Criar bucket GCS para Terraform state (`gs://{PROJECT}-tfstate/`)
- [ ] Criar secrets necessários no Secret Manager
- [ ] Configurar Cloud Build trigger no repositório
- [ ] Ajustar calendário de feriados (`trusted.feriados_anbima`) ou remover se não aplicável
- [ ] Definir schema das tabelas de dimensão
- [ ] Configurar alertas no Cloud Monitoring (recomendado)

---

## 10. Referência Rápida para Claude Code

### Criar novo job de ingestão

```
Crie um novo job de ingestão chamado ingest_novo_fonte em jobs/ingest_novo_fonte/.
Siga o padrão dos jobs existentes (ex: ingest_estoque_vx):
- config.yaml com nome, env e recursos
- main.py com get_data_referencia(), extract(), transform(), save_to_raw(), load_from_dataframe()
- Use shared/bq.py e shared/gcs.py
```

### Criar novo workflow

```
Crie um workflow em workflows/daily_novo/ com:
- Execução paralela dos jobs A, B, C
- Seguido de job de transformação D
- Schedule: 8h (America/Sao_Paulo)
```

### Adicionar nova shared lib

```
Crie um novo client de API em shared/novo_api.py seguindo o padrão de shared/vortx_api.py:
- Autenticação via Secret Manager
- Paginação automática
- Retorno como pd.DataFrame
```

### Adicionar nova tabela de dimensão

```
Adicione uma nova tabela de dimensão ao BigQuery:
1. Criar script de migração em scripts/
2. Carregar no dataset trusted
3. Usar como lookup no job de transformação
```

### Debug de job

```bash
# Rodar local com logs
PYTHONPATH=. python -m jobs.NOME_DO_JOB.main

# Rodar no Docker
make docker-build && make docker-run JOB=NOME_DO_JOB

# Ver logs no Cloud Run
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=NOME_DO_JOB" --limit=50
```

---

## Dependências

```
google-cloud-bigquery>=3.13.0
google-cloud-storage>=2.10.0
google-cloud-logging>=3.8.0
google-cloud-secret-manager>=2.16.0
pandas>=2.1.0
pyarrow>=14.0.0
pyyaml>=6.0
requests>=2.31.0
fsspec>=2023.10.0
gcsfs>=2023.10.0
boto3>=1.28.0          # Apenas se usar S3
pyodbc>=4.0.39         # Apenas se usar SQL Server
sqlalchemy>=2.0.0      # Apenas se usar SQL Server
db-dtypes>=1.2.0
```

---

## Princípios Arquiteturais

1. **Idempotência**: Todo job pode ser re-executado sem efeitos colaterais
2. **Imutabilidade**: Raw layer nunca é modificado
3. **Auto-discovery**: Terraform detecta novos jobs/workflows automaticamente
4. **Imagem única**: Um Docker serve todos os jobs via `JOB_NAME`
5. **Separação de responsabilidades**: Ingestão separada de transformação
6. **Segurança**: Credenciais no Secret Manager, service accounts isoladas
7. **Observabilidade**: Logging estruturado no Cloud Logging
8. **Convenção sobre configuração**: Estrutura de pastas define a infraestrutura
