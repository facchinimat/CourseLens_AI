from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.rag_engine import rag_engine
from app.models.schemas import WeakAreaRequest, WeakAreaResponse

router = APIRouter()


@router.post("/weak-areas", response_model=WeakAreaResponse)
async def get_weak_areas(request: WeakAreaRequest):
    """Analyse accumulated quiz history to identify the student's weak areas."""
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured.")

    try:
        return rag_engine.analyze_weak_areas(request.quiz_history)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to analyse weak areas: {exc}"
        ) from exc
