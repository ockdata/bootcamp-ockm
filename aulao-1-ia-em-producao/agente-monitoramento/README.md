# Agente de Monitoramento

Projeto do aulão 1 criado no bloco de observabilidade e troubleshooting.

Pipeline Python de classificação, anomalia, RAG, root cause e alerting.

## Estrutura principal

- `pipeline/`: orquestração e etapas do fluxo.
- `observability/`: logging, tracing e métricas.
- `providers/`: integrações de LLM, embeddings, vector store, alert sinks e BigQuery.
- `protocols/`: interfaces do domínio.
- `schemas/`: modelos Pydantic.
- `rag_data/`: base local para runbooks, postmortems e changelogs.
- `scripts/`: demos, seed e utilitários.
- `tests/`: cobertura do fluxo principal.

## Navegação rápida

```bash
cd aulao-1-ia-em-producao/agente-monitoramento
make setup
make demo-dry
```
