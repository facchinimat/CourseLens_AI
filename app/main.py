from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import analysis, documents, qa, quiz

app = FastAPI(
    title="CourseLens AI",
    description=(
        "AI-powered course tutor using RAG, embeddings, and source citations "
        "to answer questions, generate quizzes, and identify weak study areas."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(qa.router, prefix="/api/qa", tags=["Q&A"])
app.include_router(quiz.router, prefix="/api/quiz", tags=["quiz"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])

_static_dir = Path("static")
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
async def root():
    index = Path("static/index.html")
    if index.exists():
        return FileResponse(str(index))
    return {"message": "CourseLens AI API", "docs": "/docs"}


@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy", "app": "CourseLens AI"}
