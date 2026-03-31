class RAGSystemError(Exception):
    """Base exception for all RAG system errors."""
    pass

class UnsupportedFormatError(RAGSystemError):
    """Raised when a document format is not supported (not PDF or DOCX)."""
    pass

class DocumentParsingError(RAGSystemError):
    """Raised when extraction from a document fails."""
    pass