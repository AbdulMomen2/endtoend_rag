"""
Vector store manager with multi-document support.
Each document is stored with its doc_id in metadata.
New documents are merged into the existing index rather than replacing it.
"""
import os
import json
import pickle
import re
import time
from pathlib import Path
from typing import List, Dict, Optional
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from rank_bm25 import BM25Okapi
from core.config import config
import logging

logger = logging.getLogger(__name__)

REGISTRY_FILE = "doc_registry.json"


def _tokenize(text: str) -> List[str]:
    return re.sub(r"[^a-z0-9\s]", "", text.lower()).split()


class VectorStoreManager:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model=config.EMBEDDING_MODEL)
        self.index_path = Path(config.FAISS_INDEX_PATH)
        self.registry_path = self.index_path / REGISTRY_FILE

    def _load_registry(self) -> Dict:
        if self.registry_path.exists():
            return json.loads(self.registry_path.read_text())
        return {}

    def _save_registry(self, registry: Dict):
        self.registry_path.write_text(json.dumps(registry, indent=2))

    def list_documents(self) -> List[Dict]:
        """Return all ingested documents with metadata."""
        return list(self._load_registry().values())

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove a document from the registry.
        Note: FAISS doesn't support selective deletion — full rebuild required.
        Returns True if doc existed.
        """
        registry = self._load_registry()
        if doc_id not in registry:
            return False
        del registry[doc_id]
        self._save_registry(registry)
        logger.warning(f"Document {doc_id} removed from registry. Rebuild index to fully remove vectors.")
        return True

    def build_and_save(self, chunks: List[Document], doc_id: str, filename: str) -> None:
        """
        Embed chunks and merge into the existing FAISS + BM25 indexes.
        Tags each chunk with doc_id for future filtering.
        """
        logger.info(f"Ingesting '{filename}' ({len(chunks)} chunks) as doc_id={doc_id}")

        # Tag chunks with doc_id
        for chunk in chunks:
            chunk.metadata["doc_id"] = doc_id
            chunk.metadata["filename"] = filename

        self.index_path.mkdir(parents=True, exist_ok=True)

        # --- Dense FAISS index ---
        faiss_path = str(self.index_path)
        new_store = FAISS.from_documents(chunks, self.embeddings)

        if (self.index_path / "index.faiss").exists():
            existing = FAISS.load_local(
                faiss_path, self.embeddings, allow_dangerous_deserialization=True
            )
            existing.merge_from(new_store)
            existing.save_local(faiss_path)
            logger.info("Merged into existing FAISS index.")
        else:
            new_store.save_local(faiss_path)
            logger.info("Created new FAISS index.")

        # --- Sparse BM25 index (append) ---
        bm25_path = self.index_path / "bm25.pkl"
        existing_docs: List[Document] = []
        if bm25_path.exists():
            with open(bm25_path, "rb") as f:
                data = pickle.load(f)
            existing_docs = data.get("docs", [])

        all_docs = existing_docs + chunks
        tokenized = [_tokenize(doc.page_content) for doc in all_docs]
        bm25 = BM25Okapi(tokenized)
        with open(bm25_path, "wb") as f:
            pickle.dump({"bm25": bm25, "docs": all_docs}, f)
        logger.info(f"BM25 index updated ({len(all_docs)} total chunks).")

        # --- Update registry ---
        registry = self._load_registry()
        registry[doc_id] = {
            "doc_id": doc_id,
            "filename": filename,
            "chunks": len(chunks),
            "ingested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self._save_registry(registry)
        logger.info(f"Registry updated. Total documents: {len(registry)}")
