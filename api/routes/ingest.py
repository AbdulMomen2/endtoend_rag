"""Document ingestion endpoint."""
import os
import time
import logging
import asyncio
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from api.services.chatbot import chatbot_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Ingestion"])
limiter = Limiter(key_func=get_remote_address)

UPLOAD_DIR = Path("./uploads")
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/ingest")
@limiter.limit("5/minute")
async def ingest_document(request: Request, file: UploadFile = File(...)):
    """
    Upload and ingest a document (PDF or DOCX).
    Rebuilds the vector index after ingestion.
    Returns progress status.
    """
    # Validate extension
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{suffix}'. Allowed: PDF, DOCX"
        )

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is 50MB."
        )

    # Save to disk
    UPLOAD_DIR.mkdir(exist_ok=True)
    safe_name = f"{int(time.time())}_{Path(file.filename).name}"
    file_path = UPLOAD_DIR / safe_name

    try:
        file_path.write_bytes(content)
        logger.info(f"Uploaded: {safe_name} ({len(content) / 1024:.1f} KB)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Run ingestion in thread pool
    try:
        from ingestion.pipeline import IngestionPipeline
        pipeline = IngestionPipeline()

        start = time.perf_counter()
        success = await asyncio.to_thread(pipeline.run, str(file_path))
        elapsed = round((time.perf_counter() - start) * 1000, 2)

        if not success:
            raise HTTPException(status_code=500, detail="Ingestion failed. Check server logs.")

        # Reload the chatbot pipeline so it picks up the new index
        chatbot_service.shutdown()
        chatbot_service.initialize()

        return {
            "status": "success",
            "filename": file.filename,
            "size_kb": round(len(content) / 1024, 1),
            "ingestion_ms": elapsed,
            "message": f"'{file.filename}' ingested successfully. Index rebuilt."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ingestion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up uploaded file
        if file_path.exists():
            file_path.unlink()


@router.get("/ingest/status")
async def ingest_status():
    """Check if a vector index exists and is ready."""
    from core.config import config
    index_path = Path(config.FAISS_INDEX_PATH)
    index_exists = (index_path / "index.faiss").exists()
    bm25_exists = (index_path / "bm25.pkl").exists()

    return {
        "index_ready": index_exists and bm25_exists,
        "faiss_index": index_exists,
        "bm25_index": bm25_exists,
        "index_path": str(index_path)
    }


@router.post("/transcribe")
@limiter.limit("20/minute")
async def transcribe_audio(request: Request, file: UploadFile = File(...)):
    """
    Transcribe audio using OpenAI Whisper API.
    Accepts webm/mp4/wav audio from browser MediaRecorder.
    """
    try:
        import openai
        content = await file.read()
        if len(content) > 25 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Audio too large (max 25MB)")

        client = openai.OpenAI()
        # Write to temp file — Whisper API requires a file-like object with a name
        import tempfile
        suffix = Path(file.filename or "audio.webm").suffix or ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            with open(tmp_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="text"
                )
            return {"text": transcript.strip()}
        finally:
            os.unlink(tmp_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
