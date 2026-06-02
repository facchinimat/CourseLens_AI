from typing import List, Optional
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings


class VectorStore:
    """ChromaDB-backed vector store with OpenAI embeddings."""

    def __init__(self):
        self._store: Optional[Chroma] = None

    def _get_embeddings(self) -> OpenAIEmbeddings:
        return OpenAIEmbeddings(
            model=settings.embedding_model,
            openai_api_key=settings.openai_api_key,
        )

    def _get_store(self) -> Chroma:
        if self._store is None:
            Path(settings.chroma_db_path).mkdir(parents=True, exist_ok=True)
            self._store = Chroma(
                persist_directory=settings.chroma_db_path,
                embedding_function=self._get_embeddings(),
            )
        return self._store

    def add_documents(self, documents: List[Document]) -> List[str]:
        """Embed and store a list of documents; return their ChromaDB IDs."""
        return self._get_store().add_documents(documents)

    def similarity_search(
        self,
        query: str,
        k: Optional[int] = None,
        filter_dict: Optional[dict] = None,
    ) -> List[Document]:
        """Return the k most relevant documents for *query*."""
        k = k or settings.max_retrieval_docs
        store = self._get_store()
        if filter_dict:
            return store.similarity_search(query, k=k, filter=filter_dict)
        return store.similarity_search(query, k=k)

    def delete_document(self, source_name: str) -> None:
        """Remove all chunks that belong to *source_name* from the store."""
        store = self._get_store()
        results = store.get(where={"source": source_name})
        if results and results.get("ids"):
            store.delete(ids=results["ids"])

    def list_sources(self) -> List[str]:
        """Return sorted list of unique document source names."""
        store = self._get_store()
        try:
            results = store.get()
            if results and results.get("metadatas"):
                sources = {
                    m.get("source", "")
                    for m in results["metadatas"]
                    if m.get("source")
                }
                return sorted(sources)
        except Exception:
            pass
        return []

    def reset(self) -> None:
        """Drop the cached store reference (useful in tests)."""
        self._store = None


vector_store = VectorStore()
