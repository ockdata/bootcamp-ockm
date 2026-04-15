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
