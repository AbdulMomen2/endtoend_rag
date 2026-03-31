import fitz
import docx
from abc import ABC, abstractmethod
from typing import List
from pathlib import Path
import logging
from langchain_core.documents import Document
from core.exceptions import UnsupportedFormatError, DocumentParsingError

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """Abstract base class for all document parsers."""
    
    @abstractmethod
    def parse(self, file_path: Path) -> List[Document]:
        """Parses a document and returns a list of LangChain Document objects."""
        pass


# pdf file format {.pdf}
class PDFParser(BaseParser):
    def parse(self, file_path: Path) -> List[Document]:
        
        documents =[]
        try:
            doc = fitz.open(file_path)
            for page_num, page in enumerate(doc):
                text = page.get_text("text").strip()

                if text:
                    metadata = {"source": str(file_path.name), "page": page_num + 1}
                    documents.append(Document(page_content=text, metadata=metadata))                    
            doc.close()

            logger.info(f"Successfully parsed PDF: {file_path.name} ({len(documents)} pages)")
            return documents
        
        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {str(e)}")
            raise DocumentParsingError(f"PDF parsing failed: {str(e)}")
        


# word files format {.docx}
class DOCXParser(BaseParser):
    def parse(self, file_path: Path) -> List[Document]:
        documents =[]
        
        try:
            doc = docx.Document(file_path)
            full_text =[]
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text.strip())
        

            text_content = "\n".join(full_text)
            metadata = {"source": str(file_path.name), "type": "docx"}
            documents.append(Document(page_content=text_content, metadata=metadata))
            
            logger.info(f"Successfully parsed DOCX: {file_path.name}")
            return documents
        
        except Exception as e:
            logger.error(f"Failed to parse DOCX {file_path}: {str(e)}")
            raise DocumentParsingError(f"DOCX parsing failed: {str(e)}")
        

# IF later we need to add .txt or other format 
# then we can wrtie the codes here 


# main Loader
class ParserFactory:
    """Factory to return the appropriate parser based on file extension."""
    
    @staticmethod
    def get_parser(file_path: Path) -> BaseParser:
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            return PDFParser()
        elif ext == ".docx":
            return DOCXParser()
        else:
            raise UnsupportedFormatError(f"Format {ext} is not supported. Use PDF or DOCX.")