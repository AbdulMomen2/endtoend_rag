from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from core.config import config
import logging

logger = logging.getLogger(__name__)


class DocumentChunker:
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        # Default to config values; callers can override per doc type
        self.chunk_size = chunk_size or config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or config.CHUNK_OVERLAP
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    @classmethod
    def for_docx(cls) -> "DocumentChunker":
        """Smaller chunks for DOCX files with shorter paragraphs."""
        return cls(chunk_size=config.CHUNK_SIZE_DOCX, chunk_overlap=config.CHUNK_OVERLAP_DOCX)

    def split(self, documents: List[Document]) -> List[Document]:
        chunks = self.splitter.split_documents(documents)
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = i
        logger.info(
            f"Split {len(documents)} pages into {len(chunks)} chunks "
            f"(size={self.chunk_size}, overlap={self.chunk_overlap})"
        )
        return chunks
