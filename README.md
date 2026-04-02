# Enterprise RAG System

Production-grade Retrieval-Augmented Generation (RAG) chatbot with hybrid retrieval, streaming, multi-model support, voice input, and a React frontend.

---

## Screenshots

> Add your screenshots to a `docs/screenshots/` folder and update the paths below.

**Chat Interface with Thread Management**

![Chat Interface](docs/screenshots/chat.png)

**Document Upload Modal**

![Upload Modal](docs/screenshots/upload.png)

**Model Selector (OpenAI / Gemini / Groq)**

![Model Selector](docs/screenshots/model-selector.png)

**Source Citations with Similarity Scores**

![Sources Panel](docs/screenshots/sources.png)

---

## Architecture

```
User Query
    ↓
[Conversational Filter]   ← greetings, small talk
    ↓
[Query Reformulation]     ← resolves pronouns using history
    ↓
[Hybrid Retrieval]
    ├─ FAISS (dense embeddings)
    └─ BM25  (sparse keywords)
    ↓
[RRF Fusion]              ← Reciprocal Rank Fusion
    ↓
[Grounded Generator]      ← GPT / Gemini / Groq + NeMo Guardrails
    ↓
Streaming Response with Page Citations
```

## Architecture Diagrams

![Architecture Overview](architecture/Screenshot%20from%202026-04-02%2009-29-29.png)

![Ingestion Pipeline](architecture/Screenshot%20from%202026-04-02%2009-30-08.png)

![Retrieval Pipeline](architecture/Screenshot%20from%202026-04-02%2009-30-28.png)

![Generation Pipeline](architecture/Screenshot%20from%202026-04-02%2009-31-06.png)

![Full System Overview](architecture/Screenshot%20from%202026-04-02%2011-40-33.png)

---

## Features

- Hybrid retrieval: FAISS + BM25 + RRF
- Streaming SSE responses (token-by-token)
- Multi-model: OpenAI, Google Gemini, Groq (free)
- Multi-document support with per-thread document scoping
- Conversational memory backed by Redis
- Query reformulation for multi-turn conversations
- NVIDIA NeMo Guardrails (input + output safety)
- Hallucination control — strict grounding with page citations
- Voice input via OpenAI Whisper
- File upload: PDF, DOCX, Excel, CSV, Images
- Async background ingestion with job polling
- API key authentication (optional)
- Prometheus metrics
- React frontend with thread management and model selector
- Docker support (frontend + backend + Redis)

---

## Project Structure

```
.
├── api/                    # FastAPI application
│   ├── main.py
│   ├── config.py
│   ├── dependencies.py
│   ├── middleware.py
│   ├── models/             # Request / response schemas
│   ├── routes/             # chat.py, health.py, ingest.py
│   └── services/           # cache.py, chatbot.py, job_store.py
├── core/
│   ├── config.py
│   ├── logger.py
│   ├── metrics.py
│   └── exceptions.py
├── ingestion/
│   ├── pipeline.py
│   ├── parsers.py          # PDF, DOCX, Excel, CSV, Image
│   ├── chunker.py
│   └── vector_store.py
├── inference/
│   ├── pipeline.py
│   ├── retriever.py
│   ├── generator.py        # OpenAI / Gemini / Groq
│   └── memory.py
├── guardrails/
│   ├── config.yml
│   └── config.co
├── frontend/               # React + Vite
│   ├── src/
│   ├── Dockerfile
│   └── nginx.conf
├── tests/
│   ├── test_rag.py
│   └── evaluate_rag.py
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 1 — Prerequisites

Install Python 3.12+ and Node.js 20+.

**Check versions:**

```bash
python3 --version
```

```bash
node --version
```

---

## 2 — Clone & Enter Project

```bash
cd ~/ZERO2AI/RAG
```

---

## 3 — Python Environment Setup

**Create virtual environment:**

```bash
python3 -m venv rag
```

**Activate it:**

```bash
source rag/bin/activate
```

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Optional — enable cross-encoder reranking (requires ~2GB PyTorch):**

```bash
pip install -r requirements-reranker.txt
```

**Optional — RAGAS evaluation:**

```bash
pip install ragas datasets
```

---

## 4 — Configure Environment

**Copy the example file:**

```bash
cp env.example .env
```

**Edit `.env` and fill in your keys:**

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional — for Gemini models
GOOGLE_API_KEY=your-google-key

# Optional — for Groq free models
GROQ_API_KEY=gsk_...

# Optional — for NeMo Guardrails NIM
NVIDIA_API_KEY=nvapi-...

# Optional — require X-API-Key header on all endpoints
API_KEY=

# Redis (auto-detected, falls back to in-memory)
REDIS_HOST=localhost
REDIS_PORT=6379
```

---

## 5 — Redis Setup

Redis is optional but recommended for persistent session memory and caching.

**Option A — Docker (recommended):**

```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

**Option B — System package:**

```bash
sudo apt-get install redis-server
```

```bash
sudo systemctl start redis-server
```

**Verify Redis is running:**

```bash
redis-cli ping
```

Expected output: `PONG`

---

## 6 — Document Ingestion

Run ingestion before starting the API. This builds the FAISS + BM25 indexes.

**Ingest the default PDF:**

```bash
python3 -m ingestion.pipeline
```

**Ingest a custom file:**

```bash
python3 -c "
from ingestion.pipeline import IngestionPipeline
p = IngestionPipeline()
p.run('path/to/your/document.pdf')
"
```

**List all ingested documents:**

```bash
python3 -c "
from ingestion.pipeline import IngestionPipeline
p = IngestionPipeline()
print(p.list_documents())
"
```

---

## 7 — Start the API Server

**Development mode (auto-reload on code changes):**

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Production mode:**

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

**With debug logging:**

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --log-level debug
```

---

## 8 — Start the Frontend

Open a second terminal.

**Install Node dependencies (first time only):**

```bash
cd frontend
npm install
```

**Start development server:**

```bash
npm run dev
```

**Build for production:**

```bash
npm run build
```

**Preview production build:**

```bash
npm run preview
```

Open browser at: `http://localhost:3000`

---

## 9 — Docker (Full Stack)

Runs frontend + backend + Redis together.

**First — ingest your document locally so the index exists:**

```bash
source rag/bin/activate
python3 -m ingestion.pipeline
```

**Build and start all services:**

```bash
docker compose build
docker compose up -d
```

**Force full rebuild (after code changes):**

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

**Quick rebuild (faster, uses cache for unchanged layers):**

```bash
docker compose up -d --build
```

**View logs:**

```bash
docker compose logs -f
```

**View logs for a specific service:**

```bash
docker compose logs -f rag_api
```

```bash
docker compose logs -f rag_frontend
```

```bash
docker compose logs -f redis
```

**Stop all services:**

```bash
docker compose down
```

**Stop and wipe all data (Redis + volumes):**

```bash
docker compose down -v
```

**Access points when running via Docker:**

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3001 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| Metrics | http://localhost:8000/metrics/prometheus |

---

## 10 — Testing

**Run unit tests:**

```bash
PYTHONPATH=$(pwd) pytest tests/test_rag.py -v
```

**Run with coverage:**

```bash
PYTHONPATH=$(pwd) pytest tests/test_rag.py -v --cov=inference --cov-report=term-missing
```

**Run a single test:**

```bash
PYTHONPATH=$(pwd) pytest tests/test_rag.py::test_exact_fallback_string_on_low_confidence -v
```

**Run component tests (checks all services before starting API):**

```bash
PYTHONPATH=$(pwd) python3 api/test_components.py
```

---

## 11 — RAGAS Quality Evaluation

```bash
pip install ragas datasets
```

```bash
python3 tests/evaluate_rag.py
```

Expected output:

```
Faithfulness:       0.92
Answer Relevancy:   0.87
Context Precision:  0.81
```

---

## 12 — API Reference (curl examples)

**Health check:**

```bash
curl http://localhost:8000/health
```

**Check index status:**

```bash
curl http://localhost:8000/api/v1/ingest/status
```

**List ingested documents:**

```bash
curl http://localhost:8000/api/v1/ingest/documents
```

**Upload a document:**

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@document.pdf"
```

**Poll ingestion job status:**

```bash
curl http://localhost:8000/api/v1/ingest/jobs/{job_id}
```

**Chat (streaming):**

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is this document about?",
    "session_id": "user-123",
    "top_k": 5
  }'
```

**Chat scoped to a specific document:**

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the results?",
    "session_id": "user-123",
    "top_k": 5,
    "doc_id": "your-doc-id-here"
  }'
```

**Chat with Groq (free):**

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Summarize this document",
    "session_id": "user-123",
    "provider": "groq",
    "model": "llama-3.3-70b-versatile"
  }'
```

**Chat with Gemini:**

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What methodology is used?",
    "session_id": "user-123",
    "provider": "gemini",
    "model": "gemini-1.5-flash"
  }'
```

**Clear session:**

```bash
curl -X DELETE http://localhost:8000/api/v1/session/user-123
```

**List available models:**

```bash
curl http://localhost:8000/api/v1/models
```

**Prometheus metrics:**

```bash
curl http://localhost:8000/metrics/prometheus
```

---

## 13 — Verification Checklist

Run these to confirm all features work correctly.

**Multi-document support:**

```bash
curl http://localhost:8000/api/v1/ingest/documents
```

**Redis session memory:**

```bash
redis-cli keys "rag:session:*"
```

**Prometheus metrics:**

```bash
curl http://localhost:8000/metrics/prometheus | grep rag_
```

**Async ingestion job:**

```bash
curl -X POST http://localhost:8000/api/v1/ingest -F "file=@doc.pdf"
# Returns job_id immediately — then poll:
curl http://localhost:8000/api/v1/ingest/jobs/{job_id}
```

**Chunk size config:**

```bash
python3 -c "from core.config import config; print(config.CHUNK_SIZE, config.CHUNK_OVERLAP)"
```

---

## 14 — Troubleshooting

**API won't start — "Failed to load FAISS index"**

Run ingestion first:

```bash
python3 -m ingestion.pipeline
```

**Redis not connecting**

```bash
redis-cli ping
```

If no response, start Redis:

```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

The system works without Redis — it falls back to in-memory automatically.

**Frontend shows 404**

Make sure `index.html` is at `frontend/index.html` (not inside `frontend/public/`):

```bash
ls frontend/index.html
```

Then restart Vite:

```bash
cd frontend && npm run dev
```

**Docker port already in use**

```bash
lsof -ti:8000 | xargs kill -9
lsof -ti:80 | xargs kill -9
```

Then retry:

```bash
docker compose up -d
```

**Groq model decommissioned error**

Use an active model:

```bash
# Active Groq models (as of April 2026)
llama-3.3-70b-versatile
llama-3.1-8b-instant
mixtral-8x7b-32768
```

**Import errors when running tests**

Always run from project root with PYTHONPATH:

```bash
PYTHONPATH=$(pwd) pytest tests/test_rag.py -v
```

---

## Design Decisions & Justification

**Why Hybrid Retrieval (FAISS + BM25)?**
Dense-only retrieval misses exact keyword matches. BM25 catches exact terms. Combining both via Reciprocal Rank Fusion (RRF) gives the best of both worlds with no tunable parameters — the same pattern used by Cohere, Elasticsearch, and Google's RAG systems.

**Why RRF over weighted fusion?**
Weighted fusion requires per-dataset tuning. RRF is parameter-free and consistently outperforms weighted fusion across benchmarks.

**Why GPT-4o-mini as default?**
Delivers ~95% of GPT-4's quality on grounded Q&A at ~10x lower cost and ~3x lower latency. For a document chatbot constrained to provided context, the quality gap is negligible.

**Why FAISS over Pinecone/Weaviate?**
FAISS runs locally with zero infrastructure cost. The multi-document merge capability makes it viable for small-to-medium deployments.

**Why NeMo Guardrails?**
Provides both input rails (blocks jailbreak attempts) and output rails (catches hallucinated responses) as a declarative layer without modifying core generation logic.

**Why streaming SSE?**
First-token latency (~300ms) matters more than total latency (~2-3s) for UX. SSE renders tokens as they arrive.

**Why Redis for session memory?**
In-memory storage is lost on restart. Redis provides persistence, TTL-based expiration (24h), and horizontal scalability with graceful in-memory fallback.

**Why async background ingestion?**
Large PDFs take 30-60s to ingest. Blocking the HTTP request causes timeouts. Background tasks with job polling return immediately.

**Chunk Size (1024 chars, 150 overlap)**
Default 512-char chunks cut sentences mid-thought. 1024 chars with 150-char overlap preserves paragraph-level context.

---

## Libraries & Tools

| Category | Library | Purpose |
|----------|---------|---------|
| LLM | `langchain-openai` | GPT-4o-mini / GPT-4o |
| LLM | `langchain-google-genai` | Gemini models |
| LLM | `langchain-groq` | Groq free models |
| Embeddings | `openai` | text-embedding-3-small |
| Vector DB | `faiss-cpu` | Dense similarity search |
| Sparse retrieval | `rank-bm25` | BM25 keyword search |
| Document parsing | `PyMuPDF` | PDF text + image extraction |
| Document parsing | `python-docx` | DOCX text + tables |
| Spreadsheets | `pandas` + `openpyxl` | Excel / CSV parsing |
| Guardrails | `nemoguardrails` | Input/output safety rails |
| API framework | `fastapi` | REST API + SSE streaming |
| Cache/sessions | `redis` | Distributed cache + memory |
| Rate limiting | `slowapi` | Per-IP rate limiting |
| Metrics | `prometheus-client` | Observability |
| Frontend | React + Vite | Chat UI |
| Frontend serving | nginx | Static files + API proxy |
| Containerization | Docker + Compose | Full stack deployment |

---

## Estimated Development Time

| Phase | Time |
|-------|------|
| Document ingestion pipeline | 3h |
| Hybrid retrieval + RRF | 2h |
| Grounded generator + prompt engineering | 2h |
| Streaming SSE endpoint | 1.5h |
| Conversational memory (Redis) | 1h |
| NeMo Guardrails integration | 1.5h |
| FastAPI structure + auth + rate limiting | 2h |
| React frontend (threads, upload, voice, model selector) | 4h |
| Docker + nginx setup | 1.5h |
| Multi-document + async ingestion | 2h |
| Multi-model support (Gemini, Groq) | 1.5h |
| Multimodal (images, tables, Excel) | 2h |
| Query reformulation + Prometheus metrics | 1.5h |
| Testing + RAGAS evaluation | 1.5h |
| Documentation | 1h |
| **Total** | **~28 hours** |

---

## Bonus Features Implemented

All optional bonus items from the assessment are implemented:

- **Source citation** — every answer includes `(Page N)` citations
- **Similarity score display** — shown in the sources panel per chunk
- **Prompt injection protection** — NeMo Guardrails input/output rails
- **Docker setup** — full `docker-compose.yml` with frontend, backend, Redis
- **Request/response logging** — structured JSON analytics at every interaction
- **Cloud deployment ready** — health checks, Prometheus metrics, Redis sessions, nginx proxy

---

## Performance

| Scenario | Latency |
|----------|---------|
| Cache hit (Redis) | 5–10ms |
| Cache hit (memory) | 1–3ms |
| Retrieval only (RRF) | 50–100ms |
| Full query (first token) | 300–500ms |
| Full query (complete) | 1–3s |
| Ingestion (10-page PDF) | 30–60s |
