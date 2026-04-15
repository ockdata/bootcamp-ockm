---
name: create-etl-job
description: 'Scaffolds a complete ETL job for the monorepo with Pydantic schema, structured logging, retry logic, DLQ, Terraform resource, and tests. Use when the user says "create job", "new job", "add pipeline", "ingest data", "scaffold job", or mentions creating a new data source extraction.'
---

# Create ETL Job

Cria um job ETL completo seguindo os padrões do aulão 1. Vai além do `make init JOB=xxx` — gera código funcional com validação, retry, DLQ e infra.

## Inputs esperados
- `$ARGUMENTS` contém o nome do job (ex: `ingest_sales`)
- Se não informado, pergunte o nome e a fonte de dados

## Step 1: Entender o contexto

Antes de gerar código, pesquise o codebase:
1. Leia `aulao-1-ia-em-producao/etl-monorepo/jobs/job_template/main.py` para entender o template base
2. Leia `aulao-1-ia-em-producao/etl-monorepo/jobs/job_template/config.yaml` para o formato de configuração
3. Leia um job existente (se houver) em `aulao-1-ia-em-producao/etl-monorepo/jobs/` para entender padrões reais
4. Leia `schemas/` para entender os schemas Pydantic existentes
5. Leia `shared/` para entender os módulos compartilhados disponíveis

## Step 2: Gerar os arquivos

Crie TODOS os arquivos abaixo. Não pule nenhum.

### 2.1 Job principal: `aulao-1-ia-em-producao/etl-monorepo/jobs/{nome}/main.py`

Deve seguir este padrão:
- Import dos módulos em `shared/` (bq, gcs, api_client)
- Schema Pydantic para validação dos registros
- Retry com Tenacity (3 tentativas, backoff exponencial)
- Try/except por registro: válidos vão pro BigQuery, inválidos vão pra DLQ
- Structured logging JSON com TODOS os campos obrigatórios:
  - event, job, timestamp, valid_records, dlq_records, duration_seconds, success

Padrão obrigatório de logging — execute o script auxiliar para referência:
```bash
python .claude/skills/create-etl-job/scripts/log_template.py {nome}
```

### 2.2 Config: `aulao-1-ia-em-producao/etl-monorepo/jobs/{nome}/config.yaml`

```yaml
job_name: "{nome}"
source:
  type: "api"  # ou "gcs", "database"
  # preencher conforme a fonte
destination:
  dataset: "trusted"
  table: "{nome}"
dlq:
  dataset: "trusted"
  table: "{nome}_dlq"
retry:
  max_attempts: 3
  wait_multiplier: 2
```

### 2.3 Schema Pydantic: `schemas/{nome}.py`

- Usar Pydantic v2 (BaseModel)
- Type hints explícitos em todos os campos
- Validators para regras de negócio (se aplicável)
- Incluir exemplo de registro válido como docstring

### 2.4 Terraform: `aulao-1-ia-em-producao/etl-monorepo/infra/job_{nome}.tf`

- Usar o módulo em `modules/cloud_run_job/`
- Seguir o padrão dos outros job_*.tf existentes
- Variáveis: JOB_NAME = "{nome}"
- Service account: referência ao existente (não criar novo)

### 2.5 Testes: `tests/test_{nome}.py`

Cobertura mínima obrigatória:
1. **Happy path**: registro válido passa pela validação Pydantic
2. **Edge cases**: campos opcionais ausentes, tipos errados
3. **DLQ**: registro inválido é enviado para DLQ, não quebra o job
4. **Schema**: validação rejeita registros malformados

## Step 3: Verificar consistência

Após gerar todos os arquivos:
1. Verificar que o schema importa corretamente no main.py
2. Verificar que o config.yaml referencia tabelas consistentes com o schema
3. Verificar que o Terraform usa o módulo correto
4. Rodar `pytest tests/test_{nome}.py` se possível

## Output final

Apresente um resumo dos arquivos criados e como rodar:
```
make run-job JOB={nome}          # Teste local
make deploy                       # Build + push Docker
make infra-plan                   # Verificar Terraform
make infra-apply                  # Provisionar
make cloud-run JOB={nome}         # Executar no GCP
```
