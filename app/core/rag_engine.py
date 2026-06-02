from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.vector_store import vector_store


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

QA_PROMPT = ChatPromptTemplate.from_template(
    """You are CourseLens AI, a helpful study assistant. Answer the student's \
question based on the provided context from their course materials.

Context from course materials:
{context}

Student's Question: {question}

Instructions:
1. Answer clearly and accurately based on the context.
2. If the answer is not fully covered, acknowledge the gap.
3. Be educational and help the student understand the concept.
4. Reference the source material where relevant.

Answer:"""
)

QUIZ_PROMPT = ChatPromptTemplate.from_template(
    """You are CourseLens AI, a study assistant that creates quiz questions to \
help students test their knowledge.

Context from course materials:
{context}

Topic (if specified): {topic}

Create {num_questions} multiple-choice quiz questions based on the context above.

Return your response as a valid JSON object with this exact structure:
{{
  "questions": [
    {{
      "id": 1,
      "question": "Question text here?",
      "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
      "correct_answer": "A",
      "topic": "Topic or concept being tested",
      "explanation": "Brief explanation of why the answer is correct"
    }}
  ]
}}

Requirements:
- Each question must test a specific concept from the material.
- All four options should be plausible; only one should be correct.
- The correct_answer field must be just the letter (A, B, C, or D).
- Topics should be specific (e.g., "Neural Networks", "Photosynthesis").

JSON Response:"""
)

WEAK_AREAS_PROMPT = ChatPromptTemplate.from_template(
    """You are CourseLens AI, a study assistant that analyses a student's quiz \
performance to identify weak areas.

Quiz Results:
{quiz_results}

Based on the quiz performance data above, analyse the student's strengths and weaknesses.

Return a valid JSON object with this exact structure:
{{
  "weak_areas": [
    {{
      "topic": "Topic name",
      "score_percentage": 40,
      "questions_attempted": 5,
      "questions_correct": 2,
      "severity": "high",
      "recommendation": "Specific study recommendation for this topic"
    }}
  ],
  "strong_areas": [
    {{
      "topic": "Topic name",
      "score_percentage": 85,
      "questions_attempted": 4,
      "questions_correct": 3
    }}
  ],
  "overall_score": 65,
  "study_plan": "General study recommendation based on all weak areas"
}}

Severity levels: "high" (score < 40 %), "medium" (40–60 %), "low" (60–70 %).
Only include areas with score < 70 % in weak_areas.

JSON Response:"""
)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class RAGEngine:
    """Core RAG engine: Q&A, quiz generation, quiz scoring, weak-area analysis."""

    def __init__(self) -> None:
        self._llm: Optional[ChatOpenAI] = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_llm(self) -> ChatOpenAI:
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=settings.llm_model,
                openai_api_key=settings.openai_api_key,
                temperature=0.1,
            )
        return self._llm

    def _format_context(self, docs: List[Document]) -> str:
        parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "Unknown")
            page = doc.metadata.get("page", "?")
            parts.append(f"[Source {i}: {source}, Page {page}]\n{doc.page_content}")
        return "\n\n---\n\n".join(parts)

    def _extract_sources(self, docs: List[Document]) -> List[Dict[str, Any]]:
        seen: set = set()
        sources: List[Dict[str, Any]] = []
        for doc in docs:
            source = doc.metadata.get("source", "Unknown")
            page = doc.metadata.get("page", "?")
            key = (source, page)
            if key not in seen:
                seen.add(key)
                excerpt = doc.page_content
                sources.append(
                    {
                        "document": source,
                        "page": page,
                        "excerpt": excerpt[:200] + "…" if len(excerpt) > 200 else excerpt,
                    }
                )
        return sources

    @staticmethod
    def _parse_json_from_response(content: str) -> Optional[Dict[str, Any]]:
        """Extract the first complete JSON object from an LLM response string."""
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(content[start:end])
            except json.JSONDecodeError:
                pass
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def answer_question(
        self,
        question: str,
        source_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Answer *question* with RAG; returns answer text + source citations."""
        filter_dict = {"source": source_filter} if source_filter else None
        docs = vector_store.similarity_search(question, filter_dict=filter_dict)

        if not docs:
            return {
                "answer": (
                    "I couldn't find relevant information in your course materials "
                    "to answer this question. Please make sure you have uploaded "
                    "the relevant documents."
                ),
                "sources": [],
            }

        context = self._format_context(docs)
        sources = self._extract_sources(docs)
        chain = QA_PROMPT | self._get_llm()
        response = chain.invoke({"context": context, "question": question})
        return {"answer": response.content, "sources": sources}

    def generate_quiz(
        self,
        topic: str = "",
        num_questions: int = 5,
        source_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate *num_questions* multiple-choice questions from course materials."""
        query = topic if topic else "key concepts and important topics"
        filter_dict = {"source": source_filter} if source_filter else None
        docs = vector_store.similarity_search(query, k=8, filter_dict=filter_dict)

        if not docs:
            return {
                "questions": [],
                "error": "No course materials found. Please upload documents first.",
            }

        context = self._format_context(docs)
        chain = QUIZ_PROMPT | self._get_llm()
        response = chain.invoke(
            {
                "context": context,
                "topic": topic or "all available topics",
                "num_questions": num_questions,
            }
        )

        result = self._parse_json_from_response(response.content)
        if result is not None:
            return result

        return {
            "questions": [],
            "error": "Failed to parse quiz questions. Please try again.",
        }

    def score_quiz(
        self,
        questions: List[Dict[str, Any]],
        answers: Dict[str, str],
    ) -> Dict[str, Any]:
        """Score *answers* against *questions* and compute per-topic breakdown."""
        topic_scores: Dict[str, Dict[str, Any]] = {}
        results: List[Dict[str, Any]] = []

        for q in questions:
            q_id = str(q["id"])
            user_answer = answers.get(q_id, "").strip().upper()
            correct = q["correct_answer"].strip().upper()
            is_correct = user_answer == correct
            topic = q.get("topic", "General")

            if topic not in topic_scores:
                topic_scores[topic] = {"correct": 0, "total": 0}

            topic_scores[topic]["total"] += 1
            if is_correct:
                topic_scores[topic]["correct"] += 1

            results.append(
                {
                    "question_id": q["id"],
                    "question": q["question"],
                    "user_answer": user_answer,
                    "correct_answer": correct,
                    "is_correct": is_correct,
                    "explanation": q.get("explanation", ""),
                    "topic": topic,
                }
            )

        total_correct = sum(1 for r in results if r["is_correct"])
        total_questions = len(results)
        overall_score = (total_correct / total_questions * 100) if total_questions else 0.0

        topic_breakdown = [
            {
                "topic": t,
                "score_percentage": round(
                    (d["correct"] / d["total"] * 100) if d["total"] else 0.0, 1
                ),
                "questions_correct": d["correct"],
                "questions_attempted": d["total"],
            }
            for t, d in topic_scores.items()
        ]

        return {
            "total_correct": total_correct,
            "total_questions": total_questions,
            "overall_score": round(overall_score, 1),
            "results": results,
            "topic_breakdown": topic_breakdown,
        }

    def analyze_weak_areas(
        self, quiz_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use the LLM to derive weak areas from accumulated quiz results."""
        if not quiz_results:
            return {
                "weak_areas": [],
                "strong_areas": [],
                "overall_score": 0,
                "study_plan": (
                    "No quiz data available. Take some quizzes to see your analysis."
                ),
                "message": "No quiz history provided.",
            }

        results_text = json.dumps(quiz_results, indent=2)
        chain = WEAK_AREAS_PROMPT | self._get_llm()
        response = chain.invoke({"quiz_results": results_text})

        parsed = self._parse_json_from_response(response.content)
        if parsed is not None:
            return parsed

        return {
            "weak_areas": [],
            "strong_areas": [],
            "overall_score": 0,
            "study_plan": "Unable to analyse results. Please try again.",
            "error": "Failed to parse analysis results.",
        }


rag_engine = RAGEngine()
