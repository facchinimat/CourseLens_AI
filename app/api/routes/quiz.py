from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.rag_engine import rag_engine
from app.models.schemas import QuizGenerateRequest, QuizScoreResponse, QuizSubmitRequest

router = APIRouter()


@router.post("/generate")
async def generate_quiz(request: QuizGenerateRequest):
    """Generate multiple-choice quiz questions from uploaded course materials."""
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured.")

    try:
        result = rag_engine.generate_quiz(
            topic=request.topic or "",
            num_questions=request.num_questions,
            source_filter=request.source_filter,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate quiz: {exc}"
        ) from exc

    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/submit", response_model=QuizScoreResponse)
async def submit_quiz(request: QuizSubmitRequest):
    """Submit quiz answers, receive scored results with per-topic breakdown."""
    if not request.questions:
        raise HTTPException(status_code=400, detail="No questions provided.")

    try:
        return rag_engine.score_quiz(
            questions=request.questions,
            answers=request.answers,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to score quiz: {exc}"
        ) from exc
