from pydantic_settings import BaseSettings


class IngestionConfig(BaseSettings):
    # Chunk sizes — tuned for academic/research PDFs
    # Larger chunks preserve more context per retrieval hit
    CHUNK_SIZE: int = 1024
    CHUNK_OVERLAP: int = 150
    CHUNK_SIZE_DOCX: int = 800    # DOCX paragraphs tend to be shorter
    CHUNK_OVERLAP_DOCX: int = 100

    FAISS_INDEX_PATH: str = "./vector_db/faiss_index"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_API_KEY: str = ""
    NVIDIA_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""   # For Gemini models
    GROQ_API_KEY: str = ""     # For Groq free models
    API_KEY: str = ""  # Set to require X-API-Key header (empty = open access)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


config = IngestionConfig()
