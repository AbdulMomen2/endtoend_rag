import os
import pickle
import re
from typing import List
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from rank_bm25 import BM25Okapi
from core.config import config
import logging

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> List[str]:
    return re.sub(r"[^a-z0-9\s]", "", text.lower()).split()


class VectorStoreManager:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model=config.EMBEDDING_MODEL)
        self.index_path = config.FAISS_INDEX_PATH

    def build_and_save(self, chunks: List[Document]) -> None:
        """Builds FAISS (dense) + BM25 (sparse) indexes and saves both to disk."""
        logger.info("Starting embedding generation and vector DB indexing...")

        # Dense FAISS index
        vector_store = FAISS.from_documents(chunks, self.embeddings)
        os.makedirs(self.index_path, exist_ok=True)
        vector_store.save_local(self.index_path)
        logger.info(f"FAISS index saved to {self.index_path}")

        # Sparse BM25 index
        tokenized = [_tokenize(doc.page_content) for doc in chunks]
        bm25 = BM25Okapi(tokenized)
        bm25_path = os.path.join(self.index_path, "bm25.pkl")
        with open(bm25_path, "wb") as f:
            pickle.dump({"bm25": bm25, "docs": chunks}, f)
        logger.info(f"BM25 index saved to {bm25_path} ({len(chunks)} chunks)")
