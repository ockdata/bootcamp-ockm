"""Index RAG documents (runbooks, postmortems, changelogs) into vector store."""

from __future__ import annotations

import asyncio
from pathlib import Path

from config.settings import get_settings
from observability.logger import setup_logging
from pipeline.rag import RAGEngine
from providers.faiss_store import FAISSStore
from providers.local_embeddings import LocalEmbeddings


def collect_documents(rag_dir: str) -> list[dict]:
    """Scan rag_data directory and collect all markdown documents."""
    base = Path(rag_dir)
    docs: list[dict] = []

    for category in ["runbooks", "postmortems", "changelogs"]:
        category_dir = base / category
        if not category_dir.exists():
            continue

        for md_file in sorted(category_dir.glob("*.md")):
            content = md_file.read_text(encoding="utf-8")
            doc_id = f"{category}/{md_file.stem}"
            docs.append({
                "id": doc_id,
                "content": content,
                "metadata": {
                    "type": category,
                    "source": str(md_file),
                    "filename": md_file.name,
                },
            })

    return docs


async def seed_rag(rag_dir: str) -> tuple[RAGEngine, int]:
    """Index all RAG documents and return the engine + count."""
    embedder = LocalEmbeddings()
    store = FAISSStore(dim=64)
    engine = RAGEngine(embedder=embedder, store=store)

    docs = collect_documents(rag_dir)
    count = await engine.index_documents(docs)
    return engine, count


async def main() -> None:
    settings = get_settings()
    setup_logging(level=settings.log_level, fmt="console")

    print(f"📚 Indexando documentos de {settings.rag_data_dir}...")
    _, count = await seed_rag(settings.rag_data_dir)
    print(f"✅ {count} documentos indexados no vector store")


if __name__ == "__main__":
    asyncio.run(main())
