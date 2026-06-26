# Camada semântica do funil — DuckDB + grafo simples

Este pacote foi criado em cima do arquivo `funnel_eventos.csv`.

## Estrutura encontrada no CSV

- `user_id`: identificador do usuário
- `plano`: `free` ou `pro`
- `device`: `web`, `ios`, `android` ou nulo
- `etapa`: `cadastro`, `onboarding_inicio`, `onboarding_completo`, `ativacao`, `exportacao`
- `timestamp`: data/hora do evento, com formatos misturados

## Ideia da demo

A demo mostra que o agente pode consultar o warehouse, mas ainda precisa de contexto semântico.

- Bronze/Silver/Gold organizam o dado.
- Semantic explicita significado:
  - qual evento é numerador
  - qual evento é denominador
  - qual é o grão
  - quais dimensões devem ser usadas antes de concluir
  - qual a ordem esperada das etapas

## Como rodar

Coloque `semantic_layer_funil_duckdb.sql` na mesma pasta do `funnel_eventos.csv` e rode:

```bash
duckdb aulao_funil.duckdb < semantic_layer_funil_duckdb.sql
```

Depois, dentro do DuckDB:

```sql
SELECT * FROM mart_funnel_segmentado ORDER BY plano, device;
SELECT * FROM semantic_edges WHERE relation = 'SHOULD_SEGMENT_BY';
```

## Arquivos

- `semantic_layer_funil_duckdb.sql`: script completo para criar Bronze, Silver, Gold e Semantic.
- `visualizacao_funil_semantico.html`: visualizacao local com funil agregado, grafo semantico e diagnostico segmentado.
- `semantic_nodes.csv`: nós do grafo semântico.
- `semantic_edges.csv`: relações do grafo semântico.
- `semantic_metrics.csv`: definição de métricas.
- `semantic_rules.csv`: regras de negócio e qualidade.
- `funnel_graph.mmd`: diagrama Mermaid para usar no slide.

## Frase para o aulão

MCP dá acesso ao dado.  
A camada semântica dá contexto para interpretar o dado.
