from pydantic_settings import BaseSettings  

class IngestionConfig(BaseSettings):
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    FAISS_INDEX_PATH: str = "./vector_db/faiss_index"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_API_KEY: str = ""
    NVIDIA_API_KEY: str = ""  # Required for NeMo Guardrails NIM microservices

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

config = IngestionConfig() #lets call it later

