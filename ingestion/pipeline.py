from pathlib import Path
from typing import Optional
import uuid
import logging
from dotenv import load_dotenv
from ingestion.parsers import ParserFactory
from ingestion.chunker import DocumentChunker
from ingestion.vector_store import VectorStoreManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()


class IngestionPipeline:
    def __init__(self):
        self.chunker = DocumentChunker()
        self.vector_manager = VectorStoreManager()

    def run(self, file_path_str: str, doc_id: Optional[str] = None) -> bool:
        file_path = Path(file_path_str)
        if not file_path.exists():
            logger.error(f"File not found: {file_path_str}")
            return False

        doc_id = doc_id or str(uuid.uuid4())

        try:
            logger.info(f"--- Starting Ingestion: {file_path.name} (doc_id={doc_id}) ---")
            parser = ParserFactory.get_parser(file_path)
            raw_documents = parser.parse(file_path)
            # Use smaller chunks for DOCX, larger for PDF
            chunker = DocumentChunker.for_docx() if file_path.suffix.lower() == ".docx" else DocumentChunker()
            chunks = chunker.split(raw_documents)
            self.vector_manager.build_and_save(chunks, doc_id=doc_id, filename=file_path.name)
            logger.info("--- Ingestion Completed Successfully ---")
            return True
        except Exception as e:
            logger.error(f"Ingestion failed: {str(e)}")
            return False

    def list_documents(self):
        return self.vector_manager.list_documents()


if __name__ == "__main__":
    pipeline = IngestionPipeline()
    pipeline.run("CIFFND__Cross_Modal_Attention_Fusion_of_Caption_and_Images_for_AI_Generated_Content_Detection.pdf")
    print("Documents:", pipeline.list_documents())
