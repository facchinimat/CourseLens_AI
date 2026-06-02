"""Tests for RAGEngine: Q&A, quiz generation/scoring, weak-area analysis."""
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from app.core.rag_engine import RAGEngine


@pytest.fixture
def engine():
    return RAGEngine()


def make_doc(content: str, source: str = "test.pdf", page: int = 1) -> Document:
    return Document(
        page_content=content,
        metadata={"source": source, "page": page, "total_pages": 5},
    )


# ── _format_context ────────────────────────────────────────────
class TestFormatContext:
    def test_includes_sources_and_pages(self, engine):
        docs = [make_doc("ML content.", "lec1.pdf", 1), make_doc("NN content.", "lec2.pdf", 3)]
        ctx = engine._format_context(docs)
        assert "lec1.pdf" in ctx and "Page 1" in ctx
        assert "lec2.pdf" in ctx and "Page 3" in ctx
        assert "ML content." in ctx and "NN content." in ctx

    def test_sources_separated(self, engine):
        docs = [make_doc("A"), make_doc("B")]
        ctx = engine._format_context(docs)
        assert "---" in ctx


# ── _extract_sources ───────────────────────────────────────────
class TestExtractSources:
    def test_deduplicates_same_source_page(self, engine):
        docs = [make_doc("A", "d.pdf", 1), make_doc("B", "d.pdf", 1), make_doc("C", "d.pdf", 2)]
        sources = engine._extract_sources(docs)
        assert len(sources) == 2

    def test_excerpt_truncated(self, engine):
        docs = [make_doc("x" * 300, "big.pdf", 1)]
        sources = engine._extract_sources(docs)
        assert len(sources[0]["excerpt"]) <= 203  # 200 + '…'

    def test_short_excerpt_not_truncated(self, engine):
        docs = [make_doc("Short text.", "s.pdf", 1)]
        sources = engine._extract_sources(docs)
        assert sources[0]["excerpt"] == "Short text."


# ── _parse_json_from_response ──────────────────────────────────
class TestParseJson:
    def test_valid_json(self, engine):
        content = 'Here is the result: {"key": "value"}'
        assert engine._parse_json_from_response(content) == {"key": "value"}

    def test_invalid_json_returns_none(self, engine):
        assert engine._parse_json_from_response("no json here") is None

    def test_nested_json(self, engine):
        content = '{"questions": [{"id": 1}]}'
        result = engine._parse_json_from_response(content)
        assert result["questions"][0]["id"] == 1


# ── answer_question ────────────────────────────────────────────
class TestAnswerQuestion:
    def test_no_docs_returns_fallback(self, engine):
        with patch("app.core.rag_engine.vector_store") as vs:
            vs.similarity_search.return_value = []
            result = engine.answer_question("What is gravity?")
        assert "couldn't find" in result["answer"].lower() or "no" in result["answer"].lower()
        assert result["sources"] == []

    def test_returns_answer_and_sources(self, engine):
        docs = [make_doc("Gravity is a force.", "physics.pdf", 2)]
        mock_response = MagicMock()
        mock_response.content = "Gravity is the force of attraction."

        with patch("app.core.rag_engine.vector_store") as vs, \
             patch.object(engine, "_get_llm", return_value=MagicMock()), \
             patch("app.core.rag_engine.QA_PROMPT") as mock_prompt:
            vs.similarity_search.return_value = docs
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = mock_response
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            result = engine.answer_question("What is gravity?")

        assert "answer" in result
        assert "sources" in result
        assert result["sources"][0]["document"] == "physics.pdf"


# ── generate_quiz ──────────────────────────────────────────────
class TestGenerateQuiz:
    def test_no_docs_returns_error(self, engine):
        with patch("app.core.rag_engine.vector_store") as vs:
            vs.similarity_search.return_value = []
            result = engine.generate_quiz(topic="Physics")
        assert result["questions"] == []
        assert "error" in result

    def test_llm_bad_json_returns_error(self, engine):
        docs = [make_doc("Some content.", "doc.pdf", 1)]
        mock_response = MagicMock()
        mock_response.content = "I cannot generate questions right now."

        with patch("app.core.rag_engine.vector_store") as vs, \
             patch.object(engine, "_get_llm", return_value=MagicMock()), \
             patch("app.core.rag_engine.QUIZ_PROMPT") as mp:
            vs.similarity_search.return_value = docs
            chain = MagicMock()
            chain.invoke.return_value = mock_response
            mp.__or__ = MagicMock(return_value=chain)
            result = engine.generate_quiz()

        assert result["questions"] == []
        assert "error" in result


# ── score_quiz ─────────────────────────────────────────────────
class TestScoreQuiz:
    def _qs(self):
        return [
            {"id": 1, "question": "Q1?", "options": ["A) a", "B) b"], "correct_answer": "A", "topic": "Math", "explanation": ""},
            {"id": 2, "question": "Q2?", "options": ["A) a", "B) b"], "correct_answer": "B", "topic": "Math", "explanation": ""},
            {"id": 3, "question": "Q3?", "options": ["A) a", "B) b"], "correct_answer": "A", "topic": "Science", "explanation": ""},
        ]

    def test_all_correct(self, engine):
        result = engine.score_quiz(self._qs(), {"1": "A", "2": "B", "3": "A"})
        assert result["total_correct"] == 3
        assert result["overall_score"] == 100.0

    def test_none_correct(self, engine):
        result = engine.score_quiz(self._qs(), {"1": "B", "2": "A", "3": "B"})
        assert result["total_correct"] == 0
        assert result["overall_score"] == 0.0

    def test_partial_correct(self, engine):
        result = engine.score_quiz(self._qs(), {"1": "A", "2": "A", "3": "A"})
        assert result["total_correct"] == 2
        assert abs(result["overall_score"] - 66.7) < 0.2

    def test_topic_breakdown(self, engine):
        result = engine.score_quiz(self._qs(), {"1": "A", "2": "A", "3": "A"})
        math = next(t for t in result["topic_breakdown"] if t["topic"] == "Math")
        sci  = next(t for t in result["topic_breakdown"] if t["topic"] == "Science")
        assert math["score_percentage"] == 50.0
        assert sci["score_percentage"] == 100.0

    def test_missing_answer_counts_wrong(self, engine):
        result = engine.score_quiz(self._qs(), {})
        assert result["total_correct"] == 0

    def test_case_insensitive_answer(self, engine):
        qs = [{"id": 1, "question": "Q?", "options": [], "correct_answer": "A", "topic": "T", "explanation": ""}]
        result = engine.score_quiz(qs, {"1": "a"})
        assert result["total_correct"] == 1

    def test_empty_questions(self, engine):
        result = engine.score_quiz([], {})
        assert result["total_questions"] == 0
        assert result["overall_score"] == 0.0


# ── analyze_weak_areas ─────────────────────────────────────────
class TestAnalyzeWeakAreas:
    def test_empty_history_returns_message(self, engine):
        result = engine.analyze_weak_areas([])
        assert result["weak_areas"] == []
        assert "message" in result

    def test_llm_bad_json_returns_error(self, engine):
        history = [{"topic_breakdown": [{"topic": "Math", "score_percentage": 30}]}]
        mock_response = MagicMock()
        mock_response.content = "Sorry I cannot analyse this."

        with patch.object(engine, "_get_llm", return_value=MagicMock()), \
             patch("app.core.rag_engine.WEAK_AREAS_PROMPT") as mp:
            chain = MagicMock()
            chain.invoke.return_value = mock_response
            mp.__or__ = MagicMock(return_value=chain)
            result = engine.analyze_weak_areas(history)

        assert "error" in result
