"""Integration tests for all API endpoints using FastAPI TestClient."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Health ─────────────────────────────────────────────────────
class TestHealth:
    def test_health(self):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"


# ── Documents ──────────────────────────────────────────────────
class TestDocuments:
    def test_list_empty(self):
        with patch("app.api.routes.documents.vector_store") as vs:
            vs.list_sources.return_value = []
            res = client.get("/api/documents")
        assert res.status_code == 200
        assert res.json() == {"documents": [], "count": 0}

    def test_list_with_docs(self):
        with patch("app.api.routes.documents.vector_store") as vs:
            vs.list_sources.return_value = ["a.pdf", "b.pdf"]
            res = client.get("/api/documents")
        assert res.status_code == 200
        assert res.json()["count"] == 2

    def test_upload_non_pdf_rejected(self):
        with patch("app.api.routes.documents.settings") as s:
            s.openai_api_key = "key"
            s.upload_dir = "/tmp/test_uploads"
            res = client.post(
                "/api/documents/upload",
                files={"file": ("notes.txt", b"hello", "text/plain")},
            )
        assert res.status_code == 400

    def test_upload_without_api_key(self):
        with patch("app.api.routes.documents.settings") as s:
            s.openai_api_key = ""
            res = client.post(
                "/api/documents/upload",
                files={"file": ("test.pdf", b"%PDF", "application/pdf")},
            )
        assert res.status_code == 503

    def test_delete_document(self):
        with patch("app.api.routes.documents.vector_store") as vs:
            vs.delete_document.return_value = None
            res = client.delete("/api/documents/lecture.pdf")
        assert res.status_code == 200
        assert "Deleted" in res.json()["message"]

    def test_delete_document_path_traversal_rejected(self):
        # URL-encoded slashes are resolved by the router (→ 404) before our code runs,
        # and literal dotdot segments without slashes are caught by our name check (→ 400).
        # Either way, path traversal must never return 200.
        res = client.delete("/api/documents/..%2Fetc%2Fpasswd")
        assert res.status_code in (400, 404)


# ── Q&A ────────────────────────────────────────────────────────
class TestQA:
    def test_no_api_key_503(self):
        with patch("app.api.routes.qa.settings") as s:
            s.openai_api_key = ""
            res = client.post("/api/qa/ask", json={"question": "What is ML?"})
        assert res.status_code == 503

    def test_empty_question_400(self):
        with patch("app.api.routes.qa.settings") as s:
            s.openai_api_key = "key"
            res = client.post("/api/qa/ask", json={"question": "  "})
        assert res.status_code == 400

    def test_successful_answer(self):
        with patch("app.api.routes.qa.settings") as s, \
             patch("app.api.routes.qa.rag_engine") as engine:
            s.openai_api_key = "key"
            engine.answer_question.return_value = {
                "answer": "ML is a subset of AI.",
                "sources": [{"document": "lec.pdf", "page": 1, "excerpt": "ML…"}],
            }
            res = client.post("/api/qa/ask", json={"question": "What is ML?"})
        assert res.status_code == 200
        data = res.json()
        assert data["answer"] == "ML is a subset of AI."
        assert len(data["sources"]) == 1


# ── Quiz ───────────────────────────────────────────────────────
class TestQuiz:
    def test_generate_no_api_key(self):
        with patch("app.api.routes.quiz.settings") as s:
            s.openai_api_key = ""
            res = client.post("/api/quiz/generate", json={"num_questions": 5})
        assert res.status_code == 503

    def test_generate_no_docs(self):
        with patch("app.api.routes.quiz.settings") as s, \
             patch("app.api.routes.quiz.rag_engine") as engine:
            s.openai_api_key = "key"
            engine.generate_quiz.return_value = {
                "questions": [],
                "error": "No course materials found. Please upload documents first.",
            }
            res = client.post("/api/quiz/generate", json={"num_questions": 5})
        assert res.status_code == 400

    def test_submit_empty_questions(self):
        res = client.post("/api/quiz/submit", json={"questions": [], "answers": {}})
        assert res.status_code == 400

    def test_submit_scored(self):
        questions = [
            {"id": 1, "question": "Q?", "options": ["A) a", "B) b"],
             "correct_answer": "A", "topic": "Test", "explanation": ""},
        ]
        res = client.post("/api/quiz/submit", json={"questions": questions, "answers": {"1": "A"}})
        assert res.status_code == 200
        data = res.json()
        assert data["total_correct"] == 1
        assert data["overall_score"] == 100.0

    def test_submit_wrong_answer(self):
        questions = [
            {"id": 1, "question": "Q?", "options": ["A) a", "B) b"],
             "correct_answer": "A", "topic": "Test", "explanation": ""},
        ]
        res = client.post("/api/quiz/submit", json={"questions": questions, "answers": {"1": "B"}})
        assert res.status_code == 200
        assert res.json()["total_correct"] == 0


# ── Analysis ───────────────────────────────────────────────────
class TestAnalysis:
    def test_no_api_key_503(self):
        with patch("app.api.routes.analysis.settings") as s:
            s.openai_api_key = ""
            res = client.post("/api/analysis/weak-areas", json={"quiz_history": []})
        assert res.status_code == 503

    def test_empty_history_returns_message(self):
        with patch("app.api.routes.analysis.settings") as s, \
             patch("app.api.routes.analysis.rag_engine") as engine:
            s.openai_api_key = "key"
            engine.analyze_weak_areas.return_value = {
                "weak_areas": [],
                "strong_areas": [],
                "overall_score": 0.0,
                "study_plan": "Take some quizzes.",
                "message": "No quiz history provided.",
            }
            res = client.post("/api/analysis/weak-areas", json={"quiz_history": []})
        assert res.status_code == 200
        assert res.json()["weak_areas"] == []

    def test_analysis_with_data(self):
        with patch("app.api.routes.analysis.settings") as s, \
             patch("app.api.routes.analysis.rag_engine") as engine:
            s.openai_api_key = "key"
            engine.analyze_weak_areas.return_value = {
                "weak_areas": [
                    {"topic": "Calculus", "score_percentage": 30.0,
                     "questions_attempted": 5, "questions_correct": 1,
                     "severity": "high", "recommendation": "Review derivatives."},
                ],
                "strong_areas": [],
                "overall_score": 30.0,
                "study_plan": "Focus on Calculus.",
            }
            res = client.post(
                "/api/analysis/weak-areas",
                json={"quiz_history": [{"topic_breakdown": []}]},
            )
        assert res.status_code == 200
        assert len(res.json()["weak_areas"]) == 1
        assert res.json()["weak_areas"][0]["topic"] == "Calculus"
