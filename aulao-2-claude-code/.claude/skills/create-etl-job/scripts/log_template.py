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
