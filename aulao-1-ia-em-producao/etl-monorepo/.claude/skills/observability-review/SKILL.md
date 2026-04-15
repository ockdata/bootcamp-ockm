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

1. Liste todos os jobs em `etl-monorepo/jobs/`
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
