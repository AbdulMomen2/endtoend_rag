# Enterprise RAG System

Production-grade Retrieval-Augmented Generation (RAG) with hybrid retrieval, streaming, multi-document support, voice input, and a React frontend.

---

## Table of Contents

-   [Architecture](#architecture)
-   [Features](#features)
-   [Project Structure](#project-structure)
-   [Quick Start](#quick-start)
-   [Installation](#installation)
-   [Configuration](#configuration)
-   [Running the System](#running-the-system)
-   [Docker](#docker)
-   [API Reference](#api-reference)
-   [Testing](#testing)
-   [Evaluation](#evaluation)
-   [Verification Checklist](#verification-checklist)
-   [Troubleshooting](#troubleshooting)

---

## Architecture

<p align="center">
  <img src="architecture/Screenshot from 2026-04-02 09-29-29.png" width="45%" /><br/>
  <img src="architecture/Screenshot from 2026-04-02 09-30-08.png" width="45%" /><br/>
  <img src="architecture/Screenshot from 2026-04-02 09-30-28.png" width="45%" /><br/>
  <img src="architecture/Screenshot from 2026-04-02 09-31-06.png" width="45%" /><br/>
  
  
</p>



```
User Query    ↓[Conversational Filter] ← greetings, name, small talk    ↓[Query Reformulation] ← resolves pronouns using history    ↓[Hybrid Retrieval]    ├─ FAISS (dense embeddings)     ← semantic similarity    └─ BM25 (sparse keywords)       ← exact keyword match    ↓[RRF Fusion] ← Reciprocal Rank Fusion    ↓[Optional: Cross-Encoder Reranking] ← GPU recommended    ↓[Grounded Generator + NeMo Guardrails]    ↓Streaming Response with Page Citations
```

---

## Features

-   Hybrid retrieval: FAISS + BM25 + RRF
-   Streaming SSE responses (token-by-token)
-   Multi-document support — each document gets a unique `doc_id`
-   Per-thread document scoping — a thread can be locked to one document
-   Conversational memory with Redis backend (falls back to in-memory)
-   Query reformulation for multi-turn conversations
-   NVIDIA NeMo Guardrails (input + output safety)
-   Hallucination control — strict grounding with page citations
-   Voice input via OpenAI Whisper
-   File upload with async background ingestion + job polling
-   API key authentication (optional)
-   Prometheus metrics at `/metrics/prometheus`
-   React frontend with thread management, document badges, upload modal
-   Docker support (frontend + backend + Redis)

---

## Project Structure

```
.├── api/                    # FastAPI application│   ├── main.py             # App entry point│   ├── config.py           # API configuration│   ├── dependencies.py     # Auth + DI│   ├── middleware.py       # Security headers, logging│   ├── models/             # Pydantic request/response schemas│   ├── routes/             # Endpoints: chat, health, ingest│   └── services/           # Cache (Redis), chatbot, job store├── core/│   ├── config.py           # Core configuration (chunk sizes, paths)│   ├── logger.py           # Structured JSON analytics logger│   ├── metrics.py          # Prometheus metrics│   └── exceptions.py       # Custom exceptions├── ingestion/│   ├── pipeline.py         # Ingestion orchestration│   ├── parsers.py          # PDF + DOCX parsers│   ├── chunker.py          # Text splitting (doc-type aware)│   └── vector_store.py     # FAISS + BM25 multi-doc index manager├── inference/│   ├── pipeline.py         # Chat orchestration + query reformulation│   ├── retriever.py        # Hybrid retriever with doc_id filtering│   ├── generator.py        # Streaming LLM generator│   └── memory.py           # Redis-backed session memory├── guardrails/│   ├── config.yml          # NeMo Guardrails config│   └── config.co           # Colang flow definitions├── frontend/               # React + Vite│   ├── src/│   │   ├── App.jsx         # Thread management + doc binding│   │   ├── api/client.js   # API client (stream, upload, poll)│   │   └── components/     # Sidebar, ChatArea, Message, InputBar, UploadModal│   ├── Dockerfile          # nginx production build│   └── nginx.conf          # Proxy /api → backend, SPA fallback├── tests/│   ├── test_rag.py         # Unit tests (pytest)│   └── evaluate_rag.py     # RAGAS quality evaluation├── Dockerfile              # Backend Docker image├── docker-compose.yml      # Full stack: frontend + backend + Redis└── requirements.txt        # Python dependencies (no PyTorch)
```

---

## Quick Start

```bash
# 1. Clone and enter projectcd ~/ZERO2AI/RAG# 2. Create and activate virtual environmentpython3 -m venv ragsource rag/bin/activate# 3. Install dependenciespip install -r requirements.txt# 4. Configure environmentcp .env.example .env# Edit .env and set OPENAI_API_KEY# 5. Ingest a documentpython3 -m ingestion.pipeline# 6. Start the APIuvicorn api.main:app --host 0.0.0.0 --port 8000# 7. Start the frontend (new terminal)cd frontend && npm install && npm run dev# 8. Open browser# Frontend: http://localhost:3000# API docs: http://localhost:8000/docs
```

---

## Installation

### Prerequisites

-   Python 3.12+
-   Node.js 20+
-   Redis (optional but recommended)

### Python Environment

```bash
# Create virtual environmentpython3 -m venv ragsource rag/bin/activate          # Linux/macOS# ragScriptsactivate           # Windows# Install core dependencies (no PyTorch)pip install -r requirements.txt# Optional: enable cross-encoder reranking (requires ~2GB PyTorch)pip install -r requirements-reranker.txt# Optional: RAGAS evaluationpip install ragas datasets
```

### Node.js / Frontend

```bash
# Install Node.js (Ubuntu/Debian)curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -sudo apt-get install -y nodejs# Install frontend dependenciescd frontendnpm install
```

### Redis

```bash
# Option A: Docker (recommended)docker run -d --name redis -p 6379:6379 redis:7-alpine# Option B: System packagesudo apt-get install redis-serversudo systemctl start redis-serversudo systemctl enable redis-server# Option C: Existing containerdocker start my-redis# Verify Redis is runningredis-cli ping   # should return PONG
```

---

## Configuration

### `.env` file

```bash
# RequiredOPENAI_API_KEY=sk-...# OptionalNVIDIA_API_KEY=nvapi-...       # For NeMo Guardrails NIMAPI_KEY=your-secret-key        # Set to require X-API-Key header (empty = open)REDIS_HOST=localhostREDIS_PORT=6379# Ingestion tuning (optional overrides)CHUNK_SIZE=1024CHUNK_OVERLAP=150FAISS_INDEX_PATH=./vector_db/faiss_indexEMBEDDING_MODEL=text-embedding-3-small
```

### API Config (`api/config.py`)

```python
RATE_LIMIT = "30/minute"       # Per-IP rate limitCACHE_TTL = 300                # Response cache TTL (seconds)DEFAULT_TOP_K = 5              # Default chunks to retrieveMAX_TOP_K = 10                 # Maximum allowed top_k
```

---

## Running the System

### Ingestion

```bash
# Ingest the default PDFpython3 -m ingestion.pipeline# Ingest a specific filepython3 -c "from ingestion.pipeline import IngestionPipelinep = IngestionPipeline()p.run('path/to/your/document.pdf')"# List all ingested documentspython3 -c "from ingestion.pipeline import IngestionPipelinep = IngestionPipeline()print(p.list_documents())"
```

### API Server

```bash
# Development (with auto-reload)uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload# Production (no reload, single worker due to in-memory state)uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1# With custom log leveluvicorn api.main:app --host 0.0.0.0 --port 8000 --log-level debug# Using the start script./start_api.sh
```

### Frontend

```bash
cd frontend# Development server (hot reload)npm run dev# Production buildnpm run build# Preview production build locallynpm run preview# Expose on network (for remote access)npm run dev -- --host 0.0.0.0
```

### Run Pipeline Directly (CLI test)

```bash
# Test inference pipelinepython3 -m inference.pipeline# Test ingestion pipelinepython3 -m ingestion.pipeline
```

---

## Docker

### Full Stack (Frontend + Backend + Redis)

```bash
# Build and start all servicesdocker compose builddocker compose up -d# View logsdocker compose logs -fdocker compose logs -f rag_apidocker compose logs -f frontenddocker compose logs -f redis# Stop all servicesdocker compose down# Stop and remove volumes (wipes Redis data)docker compose down -v# Rebuild after code changesdocker compose build --no-cachedocker compose up -d
```

### Individual Services

```bash
# Build backend onlydocker build -t rag-api .# Run backend onlydocker run -d   --name rag_api   -p 8000:8000   -e OPENAI_API_KEY=sk-...   -v $(pwd)/vector_db:/app/vector_db   rag-api# Build frontend onlydocker build -t rag-frontend ./frontend# Run frontend onlydocker run -d --name rag_frontend -p 80:80 rag-frontend
```

### Access Points (Docker)

Service

URL

Frontend

[http://localhost](http://localhost)

API

[http://localhost:8000](http://localhost:8000)

API Docs

[http://localhost:8000/docs](http://localhost:8000/docs)

Health

[http://localhost:8000/health](http://localhost:8000/health)

Metrics

[http://localhost:8000/metrics/prometheus](http://localhost:8000/metrics/prometheus)

### Pre-ingest Before Docker

The vector index must exist before starting the API container:

```bash
# Run ingestion locally firstsource rag/bin/activatepython3 -m ingestion.pipeline# Then start Docker (index is mounted as a volume)docker compose up -d
```

---

## API Reference

### Authentication

If `API_KEY` is set in `.env`, include the header:

```bash
-H "X-API-Key: your-secret-key"
```

### Chat (Streaming)

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream   -H "Content-Type: application/json"   -d '{    "query": "What dataset is used in this paper?",    "session_id": "user-123",    "top_k": 5,    "doc_id": null  }'
```

Response events (SSE):

```
data: {"type": "sources", "sources": [...]}data: {"type": "token", "content": "The "}data: {"type": "token", "content": "dataset "}...data: {"type": "done", "latency_ms": 380}
```

### Chat (Scoped to Document)

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream   -H "Content-Type: application/json"   -d '{    "query": "What are the results?",    "session_id": "user-123",    "top_k": 5,    "doc_id": "abc-123-def-456"  }'
```

### Upload Document

```bash
curl -X POST http://localhost:8000/api/v1/ingest   -F "file=@document.pdf"
```

Response:

```json
{  "status": "queued",  "job_id": "uuid",  "doc_id": "uuid",  "filename": "document.pdf"}
```

### Poll Ingestion Job

```bash
curl http://localhost:8000/api/v1/ingest/jobs/{job_id}
```

Response when done:

```json
{  "job_id": "...",  "status": "done",  "result": {"doc_id": "...", "filename": "...", "ingestion_ms": 4200}}
```

### List Documents

```bash
curl http://localhost:8000/api/v1/ingest/documents
```

### Delete Document

```bash
curl -X DELETE http://localhost:8000/api/v1/ingest/documents/{doc_id}
```

### Clear Session

```bash
curl -X DELETE http://localhost:8000/api/v1/session/{session_id}
```

### Health Check

```bash
curl http://localhost:8000/health
```

### Prometheus Metrics

```bash
curl http://localhost:8000/metrics/prometheus
```

---

## Testing

### Unit Tests

```bash
# Run all testspytest tests/test_rag.py -v# Run with coveragepytest tests/test_rag.py -v --cov=inference --cov-report=term-missing# Run a specific testpytest tests/test_rag.py::test_exact_fallback_string_on_low_confidence -v
```

### Component Tests (API)

```bash
# Verify all components work before starting APIPYTHONPATH=$(pwd) python3 api/test_components.py
```

### Manual API Tests

```bash
# Health checkcurl http://localhost:8000/health# Index statuscurl http://localhost:8000/api/v1/ingest/status# List documentscurl http://localhost:8000/api/v1/ingest/documents# Test valid querycurl -X POST http://localhost:8000/api/v1/chat/stream   -H "Content-Type: application/json"   -d '{"query": "What dataset is used?", "session_id": "test-1"}'# Test fallback (unrelated query)curl -X POST http://localhost:8000/api/v1/chat/stream   -H "Content-Type: application/json"   -d '{"query": "What is the weather today?", "session_id": "test-2"}'# Test conversationalcurl -X POST http://localhost:8000/api/v1/chat/stream   -H "Content-Type: application/json"   -d '{"query": "Hello!", "session_id": "test-3"}'# Test voice transcriptioncurl -X POST http://localhost:8000/api/v1/transcribe   -F "file=@audio.webm"
```

---

## Evaluation

```bash
# Install evaluation dependenciespip install ragas datasets# Run RAGAS evaluation (requires ingested document)python3 tests/evaluate_rag.py
```

Output:

```
RAGAS Evaluation Results==================================================Faithfulness:       0.92  (1.0 = fully grounded)Answer Relevancy:   0.87  (1.0 = perfectly relevant)Context Precision:  0.81  (1.0 = all context used)==================================================
```

Edit `tests/evaluate_rag.py` to add your own Q&A pairs to `EVAL_DATASET`.

---

## Verification Checklist

Run these to verify all 8 improvements are working:

### 1. Multi-document support

```bash
# Ingest two different documentspython3 -c "from ingestion.pipeline import IngestionPipelinep = IngestionPipeline()p.run('doc1.pdf')p.run('doc2.pdf')print(p.list_documents())  # Should show both"# Verify via APIcurl http://localhost:8000/api/v1/ingest/documents
```

### 2. API Key Auth

```bash
# Set API_KEY=test123 in .env, restart API, then:curl http://localhost:8000/api/v1/ingest/status# Should return 401curl -H "X-API-Key: test123" http://localhost:8000/api/v1/ingest/status# Should return 200
```

### 3. Redis Session Memory

```bash
# Check Redis has session data after a chatredis-cli keys "rag:session:*"redis-cli get "rag:session:<session-id>"
```

### 4. Query Reformulation

```bash
# In API logs, look for lines like:# "Query reformulated: 'what about it?' → 'What is the dataset size?'"uvicorn api.main:app --log-level debug 2>&1 | grep reformulated
```

### 5. Prometheus Metrics

```bash
curl http://localhost:8000/metrics/prometheus | grep rag_# Should show: rag_queries_total, rag_query_latency_seconds, rag_fallbacks_total
```

### 6. Async Ingestion

```bash
# Upload and immediately get job_id back (non-blocking)curl -X POST http://localhost:8000/api/v1/ingest -F "file=@doc.pdf"# Returns immediately with job_id# Poll statuscurl http://localhost:8000/api/v1/ingest/jobs/<job_id>
```

### 7. Chunk Size Tuning

```bash
# Check configpython3 -c "from core.config import config; print(config.CHUNK_SIZE, config.CHUNK_OVERLAP)"# Should print: 1024 150
```

### 8. RAGAS Evaluation

```bash
pip install ragas datasetspython3 tests/evaluate_rag.py
```

### Per-Thread Document Scoping

```bash
# Get a doc_id from the documents listDOC_ID=$(curl -s http://localhost:8000/api/v1/ingest/documents | python3 -c "import sys, jsondocs = json.load(sys.stdin)['documents']print(docs[0]['doc_id']) if docs else print('')")# Query scoped to that documentcurl -X POST http://localhost:8000/api/v1/chat/stream   -H "Content-Type: application/json"   -d "{"query": "What is this about?", "session_id": "test", "doc_id": "$DOC_ID"}"
```

---

## Troubleshooting

### API won't start — "Failed to load FAISS index"

```bash
# Run ingestion firstpython3 -m ingestion.pipeline
```

### Redis connection failed

```bash
# Check if Redis is runningredis-cli ping# Start Redisdocker run -d --name redis -p 6379:6379 redis:7-alpine# orsudo systemctl start redis-server# The system works without Redis (falls back to in-memory)
```

### Frontend 404 at localhost:3000

```bash
# Make sure index.html is at frontend root (not frontend/public)ls frontend/index.html# Restart Vitecd frontend && npm run dev
```

### Docker build fails — "annotated-types not found"

```bash
# Use the correct build command (no --no-deps flag)docker compose build --no-cache
```

### Slow first query (~30s)

The cross-encoder is disabled by default. If you see slow queries, check:

```bash
# Should say "use_reranker=False"grep use_reranker inference/pipeline.py
```

### Import errors when running tests

```bash
# Always run from project root with PYTHONPATHPYTHONPATH=$(pwd) pytest tests/test_rag.py -v
```

### NeMo Guardrails warning

```bash
pip install nemoguardrails# The system works without it (degrades gracefully)
```

---

## Performance

Scenario

Latency

Cache hit (Redis)

5–10ms

Cache hit (memory)

1–3ms

Retrieval only (RRF)

50–100ms

Full query (first token)

300–500ms

Full query (complete)

1–3s

Ingestion (10-page PDF)

30–60s

---

## Scalability Path

Now

Next step

In-memory sessions

Redis sessions (done)

Single FAISS file

Pinecone / Weaviate

Single API worker

Multiple workers + load balancer

Sync ingestion

Background tasks (done)

No auth

API keys (done) → OAuth2

No metrics

Prometheus (done) → Grafana dashboard

docker compose downdocker compose up -ddocker compose logs -f rag_api

---

## Design Decisions & Justification

### Why Hybrid Retrieval (FAISS + BM25)?

Dense-only retrieval (FAISS) misses exact keyword matches. BM25 catches exact terms. Combining both via Reciprocal Rank Fusion (RRF) gives the best of both worlds with no tunable parameters — the same pattern used by Cohere, Elasticsearch, and Google's RAG systems.

### Why RRF over weighted fusion?

Weighted fusion requires per-dataset tuning. RRF is parameter-free and consistently outperforms weighted fusion across benchmarks. It's also robust to score scale differences between dense and sparse retrievers.

### Why GPT-4o-mini?

Delivers ~95% of GPT-4's quality on grounded Q&A at ~10x lower cost and ~3x lower latency. For a document chatbot where the LLM is constrained to provided context, the quality gap is negligible.

### Why FAISS over Pinecone/Weaviate?

FAISS runs locally with zero infrastructure cost. The multi-document merge capability (`FAISS.merge_from`) makes it viable for small-to-medium deployments. Pinecone is the right choice at scale (millions of chunks).

### Why NeMo Guardrails?

The assessment explicitly requires hallucination control and prompt injection protection. NeMo provides both input rails (blocks jailbreak attempts) and output rails (catches hallucinated responses) as a declarative layer without modifying core generation logic.

### Why streaming SSE?

First-token latency (300ms) matters more than total latency (2-3s) for UX. SSE renders tokens as they arrive — the same approach used by ChatGPT and Claude.

### Why Redis for session memory?

In-memory storage is lost on restart and can't be shared across workers. Redis provides persistence, TTL-based expiration (24h), and horizontal scalability with graceful in-memory fallback.

### Why async background ingestion?

Large PDFs take 30-60s to ingest. Blocking the HTTP request causes timeouts. Background tasks with job polling return immediately while ingestion runs asynchronously.

### Chunk Size (1024 chars, 150 overlap)

Default 512-char chunks cut sentences mid-thought. 1024 chars with 150-char overlap preserves paragraph-level context while keeping chunks precise enough for retrieval.

---

## Libraries & Tools

Category

Library

Purpose

LLM

`langchain-openai`

GPT-4o-mini integration

Embeddings

`openai`

text-embedding-3-small

Vector DB

`faiss-cpu`

Dense similarity search

Sparse retrieval

`rank-bm25`

BM25 keyword search

Document parsing

`PyMuPDF`

PDF text extraction

Document parsing

`python-docx`

DOCX text extraction

Guardrails

`nemoguardrails`

Input/output safety rails

API framework

`fastapi`

REST API + SSE streaming

Cache/sessions

`redis`

Distributed cache + memory

Rate limiting

`slowapi`

Per-IP rate limiting

Metrics

`prometheus-client`

Observability

Frontend

React + Vite

Chat UI

Frontend serving

nginx

Static files + API proxy

Containerization

Docker + Compose

Full stack deployment

---

## Estimated Development Time

Phase

Time

Document ingestion pipeline (parsers, chunker, FAISS, BM25)

3h

Hybrid retrieval + RRF fusion

2h

Grounded generator + prompt engineering

2h

Streaming SSE endpoint

1.5h

Conversational memory (Redis-backed)

1h

NeMo Guardrails integration

1.5h

FastAPI application structure + auth + rate limiting

2h

React frontend (thread management, upload, voice)

4h

Docker + nginx setup

1.5h

Multi-document support + async ingestion

2h

Query reformulation + Prometheus metrics

1.5h

Testing + RAGAS evaluation

1.5h

Documentation

1h

**Total**

**~25 hours**

---

## Bonus Features Implemented

All optional bonus items from the assessment are implemented:

-   **Source citation** — every answer includes `(Page N)` citations
-   **Similarity score display** — shown in the sources panel per chunk
-   **Prompt injection protection** — NeMo Guardrails input rails + conversational bypass
-   **Docker setup** — full `docker-compose.yml` with frontend, backend, Redis
-   **Request/response logging** — structured JSON analytics at every interaction
-   **Cloud deployment ready** — health checks, Prometheus metrics, Redis sessions, nginx proxy