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
