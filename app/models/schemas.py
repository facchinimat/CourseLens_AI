from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


class DocumentListResponse(BaseModel):
    documents: List[str]
    count: int


# ---------------------------------------------------------------------------
# Q&A
# ---------------------------------------------------------------------------


class QuestionRequest(BaseModel):
    question: str
    source_filter: Optional[str] = None


class Source(BaseModel):
    document: str
    page: Any
    excerpt: str


class QuestionResponse(BaseModel):
    answer: str
    sources: List[Source]


# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------


class QuizGenerateRequest(BaseModel):
    topic: Optional[str] = ""
    num_questions: int = Field(default=5, ge=1, le=20)
    source_filter: Optional[str] = None


class QuizSubmitRequest(BaseModel):
    questions: List[Dict[str, Any]]
    answers: Dict[str, str]


class QuizResult(BaseModel):
    question_id: int
    question: str
    user_answer: str
    correct_answer: str
    is_correct: bool
    explanation: str
    topic: str


class TopicBreakdown(BaseModel):
    topic: str
    score_percentage: float
    questions_correct: int
    questions_attempted: int


class QuizScoreResponse(BaseModel):
    total_correct: int
    total_questions: int
    overall_score: float
    results: List[QuizResult]
    topic_breakdown: List[TopicBreakdown]


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


class WeakAreaRequest(BaseModel):
    quiz_history: List[Dict[str, Any]]


class WeakArea(BaseModel):
    topic: str
    score_percentage: float
    questions_attempted: int
    questions_correct: int
    severity: Optional[str] = "medium"
    recommendation: Optional[str] = ""


class StrongArea(BaseModel):
    topic: str
    score_percentage: float
    questions_attempted: int
    questions_correct: int


class WeakAreaResponse(BaseModel):
    weak_areas: List[WeakArea] = []
    strong_areas: List[StrongArea] = []
    overall_score: float = 0.0
    study_plan: str = ""
    error: Optional[str] = None
    message: Optional[str] = None
