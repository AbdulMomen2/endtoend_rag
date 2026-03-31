from pathlib import Path
import logging
from dotenv import load_dotenv
from ingestion.parsers import ParserFactory
from ingestion.chunker import DocumentChunker
from ingestion.vector_store import VectorStoreManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

class IngestionPipeline:
    """
    Orchestrates the end-to-end ingestion process:
    1. Read Document
    2. Parse Text & Metadata
    3. Split into Chunks
    4. Generate Embeddings & Store in FAISS
    """

    def __init__(self):
        self.chunker = DocumentChunker()
        self.vector_manager = VectorStoreManager()

    def run(self, file_path_str: str) -> bool:
        file_path = Path(file_path_str)
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path_str}")
            return False

        try:
            logger.info(f"--- Starting Ingestion Pipeline for: {file_path.name} ---")

            parser = ParserFactory.get_parser(file_path)
            raw_documents = parser.parse(file_path)
            chunks = self.chunker.split(raw_documents)
            self.vector_manager.build_and_save(chunks)
            logger.info("--- Ingestion Pipeline Completed Successfully ---")
            return True
            
        except Exception as e:
            logger.error(f"Ingestion Pipeline failed: {str(e)}")
            return False

if __name__ == "__main__":

    pipeline = IngestionPipeline()
    pipeline.run("CIFFND__Cross_Modal_Attention_Fusion_of_Caption_and_Images_for_AI_Generated_Content_Detection.pdf")