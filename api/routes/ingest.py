"""Document ingestion and transcription endpoints."""
import os
import time
import uuid
import logging
import asyncio
import tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Request, Depends, BackgroundTasks
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import verify_api_key
from api.services.chatbot import chatbot_service
from api.services.job_store import job_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Ingestion"], dependencies=[Depends(verify_api_key)])
limiter = Limiter(key_func=get_remote_address)

UPLOAD_DIR = Path("./uploads")
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xls", ".csv", ".png", ".jpg", ".jpeg", ".webp"}
MAX_FILE_SIZE = 50 * 1024 * 1024


def _run_ingestion_job(job_id: str, file_path: str, doc_id: str, filename: str):
    """Background task: run ingestion and update job status."""
    from ingestion.pipeline import IngestionPipeline
    job_store.update(job_id, status="processing")
    try:
        pipeline = IngestionPipeline()
        start = time.perf_counter()
        success = pipeline.run(file_path, doc_id)
        elapsed = round((time.perf_counter() - start) * 1000, 2)

        if success:
            chatbot_service.shutdown()
            chatbot_service.initialize()
            job_store.update(job_id, status="done", result={
                "doc_id": doc_id, "filename": filename,
                "ingestion_ms": elapsed
            })
        else:
            job_store.update(job_id, status="failed", error="Ingestion returned False")
    except Exception as e:
        job_store.update(job_id, status="failed", error=str(e))
        logger.error(f"Background ingestion failed: {e}", exc_info=True)
    finally:
        if Path(file_path).exists():
            Path(file_path).unlink()


@router.post("/ingest")
@limiter.limit("5/minute")
async def ingest_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload and ingest a document asynchronously.
    Returns a job_id immediately. Poll /ingest/jobs/{job_id} for status.
    """
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{suffix}'. Allowed: PDF, DOCX"
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 50MB."
        )

    UPLOAD_DIR.mkdir(exist_ok=True)
    doc_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    safe_name = f"{int(time.time())}_{Path(file.filename).name}"
    file_path = UPLOAD_DIR / safe_name

    try:
        file_path.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    job_store.create(job_id, file.filename)
    background_tasks.add_task(_run_ingestion_job, job_id, str(file_path), doc_id, file.filename)

    return {
        "status": "queued",
        "job_id": job_id,
        "doc_id": doc_id,
        "filename": file.filename,
        "size_kb": round(len(content) / 1024, 1),
        "message": "Ingestion started. Poll /api/v1/ingest/jobs/{job_id} for status."
    }


@router.get("/ingest/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Poll ingestion job status."""
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    return job


@router.get("/ingest/documents")
async def list_documents():
    """List all ingested documents."""
    from ingestion.vector_store import VectorStoreManager
    mgr = VectorStoreManager()
    return {"documents": mgr.list_documents()}


@router.delete("/ingest/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Remove a document from the registry (vectors remain until full rebuild)."""
    from ingestion.vector_store import VectorStoreManager
    mgr = VectorStoreManager()
    if not mgr.delete_document(doc_id):
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found.")
    return {"status": "success", "message": f"Document {doc_id} removed from registry."}


@router.get("/ingest/status")
async def ingest_status():
    """Check if a vector index exists and is ready."""
    from core.config import config
    index_path = Path(config.FAISS_INDEX_PATH)
    return {
        "index_ready": (index_path / "index.faiss").exists() and (index_path / "bm25.pkl").exists(),
        "faiss_index": (index_path / "index.faiss").exists(),
        "bm25_index": (index_path / "bm25.pkl").exists(),
    }


@router.post("/transcribe")
@limiter.limit("20/minute")
async def transcribe_audio(request: Request, file: UploadFile = File(...)):
    """Transcribe audio via OpenAI Whisper."""
    try:
        import openai
        content = await file.read()
        if len(content) > 25 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Audio too large (max 25MB)")

        suffix = Path(file.filename or "audio.webm").suffix or ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            client = openai.OpenAI()
            with open(tmp_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", file=f, response_format="text"
                )
            return {"text": transcript.strip()}
        finally:
            os.unlink(tmp_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
