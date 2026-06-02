import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.core.config import settings
from app.core.document_processor import DocumentProcessor
from app.core.vector_store import vector_store

router = APIRouter()
processor = DocumentProcessor()


@router.post("/upload")
async def upload_document(
    _background: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Upload a PDF, extract text, and index it into the vector store."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "OpenAI API key not configured. "
                "Please set OPENAI_API_KEY in your .env file."
            ),
        )

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename

    with file_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    try:
        documents = processor.process_file(str(file_path), file.filename)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to parse PDF: {exc}"
        ) from exc

    if not documents:
        raise HTTPException(
            status_code=400,
            detail=(
                "Could not extract text from this PDF. "
                "The file may be scanned or empty."
            ),
        )

    try:
        ids = vector_store.add_documents(documents)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to index document: {exc}"
        ) from exc

    return {
        "status": "success",
        "filename": file.filename,
        "chunks_indexed": len(ids),
        "message": f"Successfully processed and indexed {file.filename}.",
    }


@router.get("")
async def list_documents():
    """Return all document names currently indexed."""
    sources = vector_store.list_sources()
    return {"documents": sources, "count": len(sources)}


@router.delete("/{filename}")
async def delete_document(filename: str):
    """Remove a document from the vector store and the uploads folder."""
    # Accept only the base filename to prevent path traversal attacks.
    safe_name = Path(filename).name
    if not safe_name or safe_name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    vector_store.delete_document(safe_name)

    # Enumerate the upload directory to obtain a filesystem-derived path for
    # the target file.  This breaks the taint chain: the Path handed to
    # unlink() comes from the directory listing, not from the user-supplied
    # filename parameter.
    upload_dir = Path(settings.upload_dir).resolve()
    if upload_dir.is_dir():
        for entry in upload_dir.iterdir():
            if entry.name == safe_name:
                entry.unlink()
                break

    return {"status": "success", "message": f"Deleted {safe_name}."}
