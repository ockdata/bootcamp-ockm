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
3. Liste todos os jobs em `etl-monorepo/jobs/` e leia cada `main.py`
4. Leia `etl-monorepo/jobs/job_template/main.py` como baseline
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
