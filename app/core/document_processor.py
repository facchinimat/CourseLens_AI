from typing import List, Dict, Any
import pypdf
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


class DocumentProcessor:
    """Extracts text from PDFs and splits content into indexed chunks."""

    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def extract_text_from_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract text page-by-page from a PDF, returning page metadata."""
        pages = []
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            total = len(reader.pages)
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append({
                        "page": page_num,
                        "content": text,
                        "total_pages": total,
                    })
        return pages

    def create_chunks(self, pages: List[Dict[str, Any]], source_name: str) -> List[Document]:
        """Split page text into overlapping chunks and attach source metadata."""
        documents: List[Document] = []
        for page_data in pages:
            chunks = self.text_splitter.create_documents(
                texts=[page_data["content"]],
                metadatas=[
                    {
                        "source": source_name,
                        "page": page_data["page"],
                        "total_pages": page_data["total_pages"],
                    }
                ],
            )
            documents.extend(chunks)
        return documents

    def process_file(self, file_path: str, source_name: str) -> List[Document]:
        """Extract text from a PDF and return LangChain Document chunks."""
        pages = self.extract_text_from_pdf(file_path)
        return self.create_chunks(pages, source_name)
