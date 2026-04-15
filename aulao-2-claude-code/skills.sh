#!/bin/bash
# ============================================================
# Setup Skills — bootcamp-ockm
# Execute na raiz do repositório: bash setup-skills.sh
# ============================================================

set -e

echo "Criando estrutura de skills para bootcamp-ockm..."
echo ""

# ============================================================
# 1. CLAUDE.md (raiz do repo)
# ============================================================
echo "1/9  CLAUDE.md"
cat > CLAUDE.md << 'EOF'
# ETL Monorepo — bootcamp-ockm

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
- Provider Google em `infra/main.tf`
- Módulo reutilizável em `infra/modules/cloud_run_job/`
- Projeto: mestrado-insper, região: us-central1
EOF

# ============================================================
# 2. PROJECT-LEVEL: create-etl-job
# ============================================================
echo "2/9  .claude/skills/create-etl-job/SKILL.md"
mkdir -p .claude/skills/create-etl-job/scripts

cat > .claude/skills/create-etl-job/SKILL.md << 'EOF'
---
name: create-etl-job
description: 'Scaffolds a complete ETL job for the monorepo with Pydantic schema, structured logging, retry logic, DLQ, Terraform resource, and tests. Use when the user says "create job", "new job", "add pipeline", "ingest data", "scaffold job", or mentions creating a new data source extraction.'
---

# Create ETL Job

Cria um job ETL completo seguindo os padrões do monorepo. Vai além do `make init JOB=xxx` — gera código funcional com validação, retry, DLQ e infra.

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
EOF

# ============================================================
# 3. PROJECT-LEVEL: create-etl-job/scripts/log_template.py
# ============================================================
echo "3/9  .claude/skills/create-etl-job/scripts/log_template.py"
cat > .claude/skills/create-etl-job/scripts/log_template.py << 'PYEOF'
"""
Gera o boilerplate de structured logging para um novo ETL job.
Executado pela skill create-etl-job — o output entra no contexto,
mas o código-fonte deste script NÃO consome tokens.
"""
import sys
import json

job_name = sys.argv[1] if len(sys.argv) > 1 else "job_name"

template = f'''import json
import time
import datetime


def log_event(event: str, job: str, valid: int, dlq: int, start: float, extra: dict | None = None):
    """Emite log estruturado no padrão do projeto."""
    entry = {{
        "event": event,
        "job": job,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "valid_records": valid,
        "dlq_records": dlq,
        "duration_seconds": round(time.time() - start, 2),
        "success": dlq == 0,
    }}
    if extra:
        entry.update(extra)
    print(json.dumps(entry))


# Uso no job:
# start = time.time()
# ... processar registros ...
# log_event("ingest_complete", "{job_name}", valid_count, dlq_count, start)
'''

print(template)
PYEOF

# ============================================================
# 4. PROJECT-LEVEL: terraform-review
# ============================================================
echo "4/9  .claude/skills/terraform-review/SKILL.md"
mkdir -p .claude/skills/terraform-review

cat > .claude/skills/terraform-review/SKILL.md << 'EOF'
---
name: terraform-review
description: 'Reviews Terraform infrastructure code for security issues, best practices, and compliance with project standards. Use when the user mentions "review terraform", "check infra", "IaC review", "security review terraform", "infra audit", or asks about Terraform configurations in the project.'
allowed-tools: Read, Glob, Grep, Bash
---

# Terraform Review — Security & Best Practices

Revisa a infraestrutura Terraform do monorepo ETL.

## Escopo de análise

Foque nos arquivos em `aulao-1-ia-em-producao/etl-monorepo/infra/`:
- `main.tf` — provider e backend
- `variables.tf` — variáveis e locals
- `iam.tf` — service accounts e IAM bindings
- `job_*.tf` — recursos de cada job
- `modules/cloud_run_job/` — módulo reutilizável

## Checklist de segurança

### IAM & Least Privilege
- Service accounts com roles mínimas necessárias?
- Nenhum `roles/editor` ou `roles/owner`?
- Bindings são por service account, não por projeto inteiro?
- Grep por `allUsers` ou `allAuthenticatedUsers` — devem ser zero

### Secrets
- Grep por `password`, `secret`, `token`, `api_key` em arquivos .tf
- Secrets são referenciados via `google_secret_manager_secret_version`?
- Nenhum secret em `env_vars` dos Cloud Run Jobs?

### Rede
- Nenhum `0.0.0.0/0` em firewall rules ou ingress?
- Cloud Run Jobs configurados como `internal` quando possível?

### Estado
- Backend remoto configurado (GCS)?
- State file não está no repositório? (grep por `.tfstate`)

### Módulo
- Módulo `cloud_run_job` é usado consistentemente?
- Todos os job_*.tf seguem o mesmo padrão?
- Variáveis obrigatórias estão sendo passadas?

## Validação adicional

Se possível, execute:
```bash
cd aulao-1-ia-em-producao/etl-monorepo/infra && terraform fmt -check -recursive && terraform validate
```

## Output

```
# Terraform Review Report

## Score: X/10

## Segurança
- [CRITICAL/WARNING/OK] descrição do achado

## Consistência
- [WARNING/OK] descrição do achado

## Recomendações
1. [lista priorizada por severidade]
```
EOF

# ============================================================
# 5. MONOREPO NESTING: schema-audit
# ============================================================
echo "5/9  aulao-1-ia-em-producao/etl-monorepo/.claude/skills/schema-audit/SKILL.md"
mkdir -p aulao-1-ia-em-producao/etl-monorepo/.claude/skills/schema-audit/references

cat > aulao-1-ia-em-producao/etl-monorepo/.claude/skills/schema-audit/SKILL.md << 'EOF'
---
name: schema-audit
description: 'Audits all Pydantic schemas in the ETL monorepo for consistency, missing validations, type safety issues, and alignment with BigQuery tables. Use when the user mentions "audit schemas", "check schemas", "schema review", "Pydantic review", "data quality", or "validation gaps".'
context: fork
agent: Explore
---

# Schema Audit — Pydantic & BigQuery Alignment

Pesquise e audite todos os schemas Pydantic do repositório.

## Investigação

1. Liste todos os arquivos em `schemas/` com Glob
2. Leia cada schema `.py` encontrado
3. Liste todos os jobs em `aulao-1-ia-em-producao/etl-monorepo/jobs/` e leia cada `main.py`
4. Leia `aulao-1-ia-em-producao/etl-monorepo/jobs/job_template/main.py` como baseline
5. Grep por `BaseModel` em todo o repositório para encontrar schemas inline
6. Consulte `references/bigquery-pydantic-types.md` para mapeamento de tipos

## Checklist de auditoria por schema

Para cada schema encontrado, verifique:

### Tipagem
- Todos os campos têm type hints explícitos?
- Campos opcionais usam `Optional[T]` ou `T | None`?
- Datas usam `datetime` em vez de `str`?
- Valores monetários usam `Decimal` em vez de `float`?

### Validações
- Campos obrigatórios de negócio estão sem default?
- Existe `field_validator` para regras de negócio?
- Strings que deveriam ter `min_length` ou pattern?
- Enums que deveriam ser `Literal` ou `Enum`?

### Consistência
- O schema em `schemas/` é importado corretamente no job?
- Existem schemas definidos inline no `main.py` que deveriam ser extraídos?
- Nomes de campos são consistentes entre schemas?

### Alinhamento com BigQuery
- Os tipos Pydantic são compatíveis com os tipos BigQuery esperados?
- Campos que vão pro BigQuery como `REQUIRED` estão sem `Optional` no Pydantic?

## Output

```
# Schema Audit Report

## Resumo
- Schemas analisados: N
- Issues encontradas: N (X critical, Y warning, Z info)

## Por schema
### schemas/exemplo.py
- [CRITICAL/WARNING/INFO] descrição

## Schemas inline (extrair para schemas/)
- caminho:linha — classe encontrada

## Campos inconsistentes entre schemas
- campo_a (schema_x.py) vs campo_b (schema_y.py)
```
EOF

# ============================================================
# 6. MONOREPO NESTING: schema-audit/references
# ============================================================
echo "6/9  aulao-1-ia-em-producao/etl-monorepo/.claude/skills/schema-audit/references/bigquery-pydantic-types.md"
cat > aulao-1-ia-em-producao/etl-monorepo/.claude/skills/schema-audit/references/bigquery-pydantic-types.md << 'EOF'
# Mapeamento Pydantic → BigQuery Types

Use esta referência para verificar compatibilidade entre schemas Pydantic e tipos BigQuery.

| Pydantic Type       | BigQuery Type   | Notas                                      |
|---------------------|-----------------|---------------------------------------------|
| `str`               | `STRING`        |                                             |
| `int`               | `INTEGER`       |                                             |
| `float`             | `FLOAT`         | Evitar para valores monetários              |
| `Decimal`           | `NUMERIC`       | Preferir para valores monetários            |
| `bool`              | `BOOLEAN`       |                                             |
| `datetime`          | `TIMESTAMP`     | Sempre usar timezone-aware                  |
| `date`              | `DATE`          |                                             |
| `time`              | `TIME`          |                                             |
| `bytes`             | `BYTES`         |                                             |
| `list[T]`           | `REPEATED`      | BigQuery não suporta nested arrays          |
| `dict`              | `RECORD`        | Precisa de schema explícito no BigQuery     |
| `Optional[T]`       | `NULLABLE`      | Campo pode ser NULL no BigQuery             |
| `T` (sem Optional)  | `REQUIRED`      | Campo NÃO pode ser NULL no BigQuery         |

## Regras de ouro
- `float` para monetário = CRITICAL (usar `Decimal`)
- `str` para data = WARNING (usar `datetime` ou `date`)
- `Optional` no Pydantic mas `REQUIRED` no BigQuery = CRITICAL
- `dict` sem tipagem interna = WARNING (dificulta schema evolution)
EOF

# ============================================================
# 7. MONOREPO NESTING: observability-review
# ============================================================
echo "7/9  aulao-1-ia-em-producao/etl-monorepo/.claude/skills/observability-review/SKILL.md"
mkdir -p aulao-1-ia-em-producao/etl-monorepo/.claude/skills/observability-review/references

cat > aulao-1-ia-em-producao/etl-monorepo/.claude/skills/observability-review/SKILL.md << 'EOF'
---
name: observability-review
description: 'Reviews all ETL jobs for structured logging compliance and observability best practices. Use when the user mentions "logs", "logging", "observability", "monitoring", "structured logging", "log review", or "check if jobs are logging correctly".'
context: fork
agent: Explore
---

# Observability Review — Structured Logging Compliance

Analise todos os jobs ETL para garantir conformidade com o padrão de logging.

## Padrão obrigatório

Consulte a referência completa em `references/logging-spec.md`.

Todo job DEVE emitir um log JSON no final da execução com os campos:
event, job, timestamp, valid_records, dlq_records, duration_seconds, success.

## Investigação

1. Liste todos os jobs em `aulao-1-ia-em-producao/etl-monorepo/jobs/`
2. Leia cada `main.py`
3. Grep por `print(json.dumps` e `logging` em todos os jobs
4. Leia `observability/` para configurações adicionais

## Checklist por job

### Campos obrigatórios
- `event` — presente e descritivo?
- `job` — presente e match com o nome do diretório?
- `timestamp` — formato ISO 8601 com Z?
- `valid_records` — contagem de registros válidos?
- `dlq_records` — contagem de registros na DLQ?
- `duration_seconds` — tempo de execução?
- `success` — booleano derivado do resultado?

### Boas práticas
- Usa `json.dumps()` em vez de f-string para logs?
- Loga no início E no final da execução?
- Trata exceções com log antes de re-raise?
- Evita `print()` para mensagens que não são logs estruturados?
- Evita logging de dados sensíveis (PII, tokens, secrets)?

## Output

```
# Observability Review

## Compliance Score: X/Y jobs conformes

## Por job
### jobs/{nome}
- Status: COMPLIANT / NON-COMPLIANT
- Campos faltando: [lista]
- Issues: [lista com severidade]

## Recomendações globais
- [melhorias que se aplicam a todos os jobs]
```
EOF

# ============================================================
# 8. MONOREPO NESTING: observability-review/references
# ============================================================
echo "8/9  aulao-1-ia-em-producao/etl-monorepo/.claude/skills/observability-review/references/logging-spec.md"
cat > aulao-1-ia-em-producao/etl-monorepo/.claude/skills/observability-review/references/logging-spec.md << 'EOF'
# Logging Specification — ETL Monorepo

## Formato

Todos os logs DEVEM ser JSON válido emitidos via `print(json.dumps(...))`.

NÃO usar:
- `logging.info()` com mensagens de texto livre
- f-strings com `print()`
- `logger.warning()` sem structured data

## Campos obrigatórios (log final de execução)

```json
{
  "event": "ingest_complete",
  "job": "job_name",
  "timestamp": "2026-02-19T07:00:00Z",
  "valid_records": 9850,
  "dlq_records": 5,
  "duration_seconds": 45.2,
  "success": true
}
```

| Campo             | Tipo    | Regra                                           |
|-------------------|---------|-------------------------------------------------|
| `event`           | string  | Descritivo: `ingest_complete`, `ingest_failed`  |
| `job`             | string  | Deve coincidir com o nome do diretório do job   |
| `timestamp`       | string  | ISO 8601 com sufixo Z (UTC)                     |
| `valid_records`   | int     | >= 0                                            |
| `dlq_records`     | int     | >= 0                                            |
| `duration_seconds`| float   | Tempo total de execução                         |
| `success`         | boolean | `true` se dlq_records == 0                      |

## Campos opcionais

| Campo             | Tipo    | Quando usar                                     |
|-------------------|---------|-------------------------------------------------|
| `error`           | string  | Mensagem de erro quando success=false           |
| `source`          | string  | Identificação da fonte de dados                 |
| `batch_id`        | string  | ID do batch quando aplicável                    |

## Log de início (recomendado)

```json
{
  "event": "ingest_started",
  "job": "job_name",
  "timestamp": "2026-02-19T07:00:00Z"
}
```
EOF

# ============================================================
# 9. USER-LEVEL: codebase-explorer (instruções de instalação)
# ============================================================
echo "9/9  Gerando codebase-explorer (user-level)"
USER_SKILL_DIR="$HOME/.claude/skills/codebase-explorer"
mkdir -p "$USER_SKILL_DIR"

cat > "$USER_SKILL_DIR/SKILL.md" << 'EOF'
---
name: codebase-explorer
description: 'Deep research on any codebase. Maps dependencies, data flows, module relationships, and architecture patterns. Use when the user asks "how does this work", "explain the architecture", "map dependencies", "what uses this module", or needs to understand a codebase before making changes.'
context: fork
agent: Explore
---

# Codebase Explorer

Pesquise o codebase e produza um mapa completo do que foi solicitado em `$ARGUMENTS`.

## Estratégia de pesquisa

### 1. Reconhecimento inicial
- Leia o README.md na raiz (se existir)
- Leia o CLAUDE.md (se existir) para entender convenções
- Liste a estrutura de diretórios (2 níveis de profundidade)
- Identifique linguagens, frameworks, e ferramentas (package.json, pyproject.toml, go.mod, etc.)

### 2. Mapeamento de módulos
- Identifique os módulos/pacotes principais
- Para cada módulo, identifique: responsabilidade, exports, dependências internas

### 3. Grafo de dependências
- Grep por imports entre módulos internos
- Identifique dependências circulares
- Identifique módulos "hub" (importados por muitos outros)

### 4. Fluxo de dados (se aplicável)
- Identifique entry points (main, handlers, routes)
- Trace o fluxo: input → processamento → output
- Identifique onde dados persistem (banco, filesystem, cache)

### 5. Infraestrutura (se presente)
- Mapeie arquivos de IaC (Terraform, CloudFormation, k8s manifests)
- Mapeie CI/CD (GitHub Actions, Cloud Build, etc.)
- Identifique ambientes (dev, staging, prod)

## Output

Retorne um resumo conciso e estruturado:

```
# Codebase Map: [tópico pesquisado]

## Visão geral
[2-3 frases]

## Descobertas relevantes
[o que é mais relevante para $ARGUMENTS]

## Arquivos-chave
[caminhos que o agente principal deveria ler]

## Riscos ou gaps identificados
[inconsistências ou problemas, se houver]
```

Seja conciso. O agente principal recebe apenas este resumo.
Não inclua código-fonte completo, apenas referências aos arquivos.
EOF

# ============================================================
# RESUMO
# ============================================================
echo ""
echo "============================================================"
echo " Setup completo!"
echo "============================================================"
echo ""
echo " Estrutura criada:"
echo ""
echo " PROJECT-LEVEL (git-tracked, todo o time):"
echo "   .claude/skills/create-etl-job/SKILL.md"
echo "   .claude/skills/create-etl-job/scripts/log_template.py"
echo "   .claude/skills/terraform-review/SKILL.md"
echo ""
echo " MONOREPO NESTING (ativa só dentro de aulao-1-ia-em-producao/etl-monorepo/):"
echo "   aulao-1-ia-em-producao/etl-monorepo/.claude/skills/schema-audit/SKILL.md"
echo "   aulao-1-ia-em-producao/etl-monorepo/.claude/skills/schema-audit/references/bigquery-pydantic-types.md"
echo "   aulao-1-ia-em-producao/etl-monorepo/.claude/skills/observability-review/SKILL.md"
echo "   aulao-1-ia-em-producao/etl-monorepo/.claude/skills/observability-review/references/logging-spec.md"
echo ""
echo " USER-LEVEL (cross-project, pessoal):"
echo "   ~/.claude/skills/codebase-explorer/SKILL.md"
echo ""
echo " Teste com: claude e depois /create-etl-job ingest_inventory"
echo "============================================================"