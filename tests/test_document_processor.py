"""Tests for DocumentProcessor: PDF extraction and text chunking."""
from unittest.mock import MagicMock, patch

import pytest

from app.core.document_processor import DocumentProcessor


@pytest.fixture
def processor():
    return DocumentProcessor()


class TestCreateChunks:
    def test_basic_chunking(self, processor):
        pages = [
            {"page": 1, "content": "Content sentence. " * 30, "total_pages": 2},
            {"page": 2, "content": "More content here. " * 30, "total_pages": 2},
        ]
        chunks = processor.create_chunks(pages, "lecture.pdf")
        assert len(chunks) > 0
        for c in chunks:
            assert c.metadata["source"] == "lecture.pdf"
            assert "page" in c.metadata

    def test_metadata_attached(self, processor):
        pages = [{"page": 3, "content": "Data " * 50, "total_pages": 5}]
        chunks = processor.create_chunks(pages, "notes.pdf")
        assert all(c.metadata["source"] == "notes.pdf" for c in chunks)
        assert all(c.metadata["page"] == 3 for c in chunks)
        assert all(c.metadata["total_pages"] == 5 for c in chunks)

    def test_empty_content_produces_no_chunks(self, processor):
        pages = [{"page": 1, "content": "", "total_pages": 1}]
        chunks = processor.create_chunks(pages, "empty.pdf")
        assert chunks == []

    def test_long_content_split_into_multiple_chunks(self, processor):
        long_content = "This is a sentence. " * 500
        pages = [{"page": 1, "content": long_content, "total_pages": 1}]
        chunks = processor.create_chunks(pages, "big.pdf")
        assert len(chunks) > 1

    def test_multiple_pages_preserved(self, processor):
        pages = [
            {"page": 1, "content": "Page one text. " * 20, "total_pages": 3},
            {"page": 2, "content": "Page two text. " * 20, "total_pages": 3},
            {"page": 3, "content": "Page three text. " * 20, "total_pages": 3},
        ]
        chunks = processor.create_chunks(pages, "multi.pdf")
        pages_in_chunks = {c.metadata["page"] for c in chunks}
        assert pages_in_chunks == {1, 2, 3}


class TestExtractTextFromPdf:
    def _mock_reader(self, texts):
        pages = []
        for t in texts:
            p = MagicMock()
            p.extract_text.return_value = t
            pages.append(p)
        reader = MagicMock()
        reader.pages = pages
        return reader

    def test_extracts_text_from_pages(self, processor, tmp_path):
        reader = self._mock_reader(["Machine learning concepts.", "Neural networks overview."])
        with patch("app.core.document_processor.pypdf.PdfReader", return_value=reader):
            f = tmp_path / "test.pdf"
            f.write_bytes(b"%PDF fake")
            pages = processor.extract_text_from_pdf(str(f))
        assert len(pages) == 2
        assert pages[0]["page"] == 1
        assert "Machine learning" in pages[0]["content"]

    def test_skips_empty_pages(self, processor, tmp_path):
        reader = self._mock_reader(["", "Real content here."])
        with patch("app.core.document_processor.pypdf.PdfReader", return_value=reader):
            f = tmp_path / "test.pdf"
            f.write_bytes(b"%PDF fake")
            pages = processor.extract_text_from_pdf(str(f))
        assert len(pages) == 1
        assert pages[0]["page"] == 2

    def test_all_empty_returns_empty_list(self, processor, tmp_path):
        reader = self._mock_reader(["   ", "\n\t"])
        with patch("app.core.document_processor.pypdf.PdfReader", return_value=reader):
            f = tmp_path / "test.pdf"
            f.write_bytes(b"%PDF fake")
            pages = processor.extract_text_from_pdf(str(f))
        assert pages == []

    def test_total_pages_recorded(self, processor, tmp_path):
        reader = self._mock_reader(["Content A.", "Content B.", "Content C."])
        with patch("app.core.document_processor.pypdf.PdfReader", return_value=reader):
            f = tmp_path / "test.pdf"
            f.write_bytes(b"%PDF fake")
            pages = processor.extract_text_from_pdf(str(f))
        assert all(p["total_pages"] == 3 for p in pages)


class TestProcessFile:
    def test_end_to_end(self, processor, tmp_path):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Algorithms and data structures content. " * 30
        reader = MagicMock()
        reader.pages = [mock_page]

        f = tmp_path / "lecture.pdf"
        f.write_bytes(b"%PDF fake")

        with patch("app.core.document_processor.pypdf.PdfReader", return_value=reader):
            docs = processor.process_file(str(f), "lecture.pdf")

        assert len(docs) > 0
        assert all(d.metadata["source"] == "lecture.pdf" for d in docs)
