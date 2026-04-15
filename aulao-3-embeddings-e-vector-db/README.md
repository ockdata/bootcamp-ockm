# Aulão 3 — Embeddings e Vector DB

Material do hands-on do aulão em formato de notebooks, na mesma ordem do roteiro ao vivo.

## Ordem de execução

1. `notebooks/01_embeddings.ipynb`
2. `notebooks/02_clusterizacao_fraude.ipynb`
3. `notebooks/03_vector_db_chunking_reranking.ipynb`

Cada notebook é autocontido, mas o fluxo faz mais sentido nessa ordem.

## Setup rápido

```bash
cd aulao-3-embeddings-e-vector-db
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
jupyter lab
```

No VS Code, selecione o kernel / interpretador:

`aulao-3-embeddings-e-vector-db/.venv/bin/python`

## Providers

- Default: embeddings locais com `sentence-transformers`.
- Se existir `.env` com `OPENAI_API_KEY`, os notebooks carregam essa chave automaticamente.
- Sem `EMBEDDING_PROVIDER` definido, os notebooks preferem `openai` quando a chave existe e fazem fallback para `local` quando não existe.
- Notebook 3 usa Chroma local no caminho `.chroma_lab/` e inclui snippets para outros backends.

## Estrutura

- `data/rag_docs/`: corpus pequeno de políticas internas para o demo de RAG.
- `notebooks/`: notebooks gerados para palco.
- `requirements.txt`: dependências do hands-on.

## Observações para o aulão

- O notebook 2 usa um dataset sintético para mostrar clusterização de embeddings aplicada a fraude.
- O notebook 3 foi desenhado para mostrar chunking ruim vs chunking melhor, retrieval vetorial e reranking.
- Se a API externa falhar, os notebooks 1 e 2 seguem com provider local e o notebook 3 continua até retrieval/reranking.
