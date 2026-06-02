from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.rag_engine import rag_engine
from app.models.schemas import QuestionRequest, QuestionResponse

router = APIRouter()


@router.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """Answer a student question using RAG over uploaded course materials."""
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured.")

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        return rag_engine.answer_question(
            question=request.question,
            source_filter=request.source_filter,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to answer question: {exc}"
        ) from exc
