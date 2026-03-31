# Enterprise RAG System

Production-grade Retrieval-Augmented Generation (RAG) system with hybrid retrieval, cross-encoder reranking, and NVIDIA NeMo Guardrails.

## Features

- **Hybrid Retrieval**: Dense (FAISS) + Sparse (BM25) with Reciprocal Rank Fusion
- **Cross-Encoder Reranking**: Precision scoring using `ms-marco-MiniLM-L-6-v2`
- **Guardrails**: NVIDIA NeMo Guardrails for input/output safety
- **Structured Prompting**: Chain-of-thought with mandatory source citations
- **Multi-turn Memory**: Session-based conversation history
- **Analytics Logging**: Structured JSON logs for observability

## Architecture

```
User Query
    ↓
[Hybrid Retrieval]
    ├─ FAISS (dense embeddings)
    └─ BM25 (sparse keywords)
    ↓
[RRF Fusion]
    ↓
[Cross-Encoder Reranking]
    ↓
[Grounded Generator + Guardrails]
    ↓
Response with Citations
```

## Installation

### 1. Create Virtual Environment

```bash
python3 -m venv rag
source rag/bin/activate  # On Windows: rag\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your-openai-api-key-here
NVIDIA_API_KEY=your-nvidia-api-key-here  # Optional, for NeMo Guardrails NIM
```

## Usage

### Phase 1: Document Ingestion

Ingest a PDF or DOCX document to build the vector index:

```bash
python3 -m ingestion.pipeline
```

This will:
- Parse the document (default: `CIFFND__Cross_Modal_Attention_Fusion_of_Caption_and_Images_for_AI_Generated_Content_Detection.pdf`)
- Chunk text with overlap
- Generate embeddings via OpenAI `text-embedding-3-small`
- Build FAISS (dense) and BM25 (sparse) indexes
- Save to `./vector_db/faiss_index/`

To ingest a different document, edit `ingestion/pipeline.py`:

```python
pipeline.run("path/to/your/document.pdf")
```

### Phase 2: Inference (CLI)

Run the chatbot pipeline directly:

```bash
python3 -m inference.pipeline
```

Or integrate into your application:

```python
from inference.pipeline import ChatbotPipeline
import uuid

chatbot = ChatbotPipeline()
session_id = str(uuid.uuid4())

response = chatbot.chat(
    session_id=session_id,
    user_query="What dataset is used in this paper?",
    top_k=3  # Number of chunks to retrieve
)

print(response["answer"])
print(response["sources"])
```

### Phase 3: Production API

#### Test Components First

Before starting the API, verify all components work:

```bash
python3 api/test_components.py
```

This will test:
- Module imports
- Configuration loading
- Redis cache connectivity
- Chatbot service initialization
- Query processing

#### Start the API Server

**Option 1: Direct (Development)**

```bash
pip install fastapi uvicorn slowapi
python3 -m api.main
```

API will be available at `http://localhost:8000`

**Option 2: Docker (Production)**

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f rag_api

# Stop
docker-compose down
```

#### API Endpoints

**Health Check**
```bash
curl http://localhost:8000/health
```

**Chat**
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What dataset is used in this paper?",
    "session_id": "user-123",
    "top_k": 3,
    "use_cache": true
  }'
```

**Clear Session**
```bash
curl -X DELETE http://localhost:8000/api/v1/session/user-123
```

**Interactive Documentation**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

#### Python Client Example

```python
from api.example_client import RAGClient

client = RAGClient(base_url="http://localhost:8000")

# Check health
health = client.health_check()
print(health)

# Ask a question
response = client.chat("What dataset is used?", top_k=3)
print(response["answer"])

# Clear session
client.clear_session()
```

Run the full example:
```bash
python3 api/example_client.py
```

## Configuration

### Core Settings (`core/config.py`)

```python
CHUNK_SIZE: int = 512           # Characters per chunk
CHUNK_OVERLAP: int = 50         # Overlap between chunks
FAISS_INDEX_PATH: str = "./vector_db/faiss_index"
EMBEDDING_MODEL: str = "text-embedding-3-small"
```

### Retrieval Settings (`inference/retriever.py`)

```python
similarity_threshold: float = -8.0  # Cross-encoder logit floor (range: -15 to +5)
fetch_k: int = 10                   # Candidates before reranking
```

### Guardrails (`guardrails/config.yml`)

Customize input/output policies:

```yaml
rails:
  input:
    flows:
      - self check input
  output:
    flows:
      - self check output
```

## Project Structure

```
.
├── api/                      # Production API (organized)
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # API configuration
│   ├── dependencies.py      # Dependency injection
│   ├── middleware.py        # Custom middleware
│   ├── models/              # Pydantic models
│   │   ├── requests.py      # Request schemas
│   │   └── responses.py     # Response schemas
│   ├── routes/              # API endpoints
│   │   ├── chat.py          # Chat endpoints
│   │   └── health.py        # Health/metrics
│   ├── services/            # Business logic
│   │   ├── cache.py         # Redis cache layer
│   │   └── chatbot.py       # Chatbot service
│   ├── example_client.py    # Example API client
│   └── test_components.py   # Component tests
├── core/
│   ├── config.py            # Core configuration
│   ├── logger.py            # Analytics logging
│   └── exceptions.py        # Custom exceptions
├── ingestion/
│   ├── parsers.py           # PDF/DOCX parsers
│   ├── chunker.py           # Text splitting
│   ├── vector_store.py      # FAISS + BM25 indexing
│   └── pipeline.py          # Ingestion orchestration
├── inference/
│   ├── retriever.py         # Hybrid retrieval + reranking
│   ├── generator.py         # Grounded LLM generation
│   ├── memory.py            # Session memory
│   └── pipeline.py          # Inference orchestration
├── guardrails/
│   ├── config.yml           # NeMo Guardrails config
│   └── config.co            # Colang flow definitions
├── models/                  # Cached models (auto-created)
├── vector_db/               # FAISS + BM25 indexes (auto-created)
├── tests/                   # Unit tests
├── .env                     # API keys (create this)
├── .gitignore
├── requirements.txt         # Python dependencies
├── Dockerfile               # Production Docker image
├── docker-compose.yml       # Multi-container setup
├── start_api.sh             # Quick start script
└── README.md                # This file
```

## How It Works

### 1. Hybrid Retrieval

Combines two complementary approaches:

- **Dense (FAISS)**: Semantic similarity via embeddings
- **Sparse (BM25)**: Keyword matching (TF-IDF-like)

Results are fused using **Reciprocal Rank Fusion (RRF)**, a parameter-free algorithm used by Cohere, Elasticsearch, and Google.

### 2. Cross-Encoder Reranking

The fused candidates are re-scored by a cross-encoder that reads the full `(query, chunk)` pair together, not just embeddings. This dramatically improves precision.

Model: `cross-encoder/ms-marco-MiniLM-L-6-v2` (trained on MS MARCO passage ranking)

Scores are raw logits in range `[-15, +5]`:
- Below `-10`: Irrelevant
- `-10` to `-5`: Weak match
- `-5` to `0`: Good match
- Above `0`: Highly relevant

### 3. Grounded Generation

The LLM (GPT-4o-mini) generates answers with:

- **Strict grounding**: Only use provided context
- **Mandatory citations**: Every fact must cite page numbers
- **Fallback handling**: Returns "This information is not present in the provided document." when uncertain

### 4. Guardrails

NVIDIA NeMo Guardrails provides:

- **Input rails**: Block jailbreak attempts, prompt injection
- **Output rails**: Prevent hallucinations, harmful content

Degrades gracefully if not installed.

## Performance

Typical latencies (on CPU):

- **Ingestion**: ~30-60s for a 10-page PDF
- **Retrieval**: ~500-800ms (first query downloads cross-encoder model)
- **Subsequent queries**: ~200-400ms (model cached locally)
- **Cached queries**: ~5-10ms

## Production Features

### Security

- **Rate Limiting**: 30 requests/minute per IP (configurable)
- **Input Validation**: Strict Pydantic models with regex validation
- **Query Sanitization**: Removes control characters and excessive whitespace
- **Security Headers**: X-Frame-Options, X-Content-Type-Options, HSTS
- **Non-root User**: Docker container runs as unprivileged user
- **Trusted Host Middleware**: Prevents host header attacks

### Performance Optimization

- **Response Caching**: 5-minute TTL, LRU eviction (100 entries max)
- **Async Processing**: Non-blocking I/O with asyncio.to_thread
- **Model Caching**: Cross-encoder downloaded once, reused
- **Connection Pooling**: Reuses HTTP connections
- **Health Checks**: Kubernetes/Docker-ready liveness probes

### Observability

- **Structured Logging**: JSON logs for ELK/Splunk ingestion
- **Metrics Endpoint**: `/metrics` for Prometheus scraping
- **Request Tracing**: Session ID tracking across requests
- **Error Handling**: Graceful degradation with user-friendly messages

### Scalability

- **Stateless Design**: Can scale horizontally (with Redis for sessions)
- **Resource Limits**: Docker memory/CPU constraints
- **Graceful Shutdown**: Proper cleanup on SIGTERM
- **Zero-downtime Deploys**: Health check integration

## Troubleshooting

### "No module named 'nemoguardrails'"

```bash
pip install nemoguardrails
```

Or run without guardrails (system degrades gracefully).

### "Failed to load Vector DB"

Run ingestion first:

```bash
python3 -m ingestion.pipeline
```

### Slow first query

The cross-encoder model downloads on first use (~90MB). Subsequent queries use the cached model in `./models/cross_encoder/`.

To pre-download:

```python
from sentence_transformers import CrossEncoder
CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", cache_folder="./models/cross_encoder")
```

### Low retrieval scores

Adjust the threshold in `inference/pipeline.py`:

```python
self.retriever = HybridRetriever(similarity_threshold=-10.0)  # Lower = more permissive
```

Cross-encoder logit ranges:
- `-8.0` (default): Balanced precision/recall
- `-10.0`: More permissive, higher recall
- `-5.0`: Stricter, higher precision

## Production Deployment

### Recommended Enhancements

1. **Replace in-memory session store** with Redis:
   ```python
   # inference/memory.py
   import redis
   self.store = redis.Redis(host='localhost', port=6379)
   ```

2. **Add query reformulation** for multi-turn conversations:
   ```python
   # Use LLM to resolve pronouns: "What about it?" → "What about the dataset?"
   ```

3. **Implement caching** for repeated queries (Redis/Memcached)

4. **Add monitoring** (Prometheus, Grafana) using the structured logs

5. **Scale retrieval** with Pinecone/Weaviate for production vector DBs

## License

MIT

## References

- [LangChain Documentation](https://python.langchain.com/)
- [NVIDIA NeMo Guardrails](https://docs.nvidia.com/nemo/guardrails/)
- [Sentence Transformers](https://www.sbert.net/)
- [Reciprocal Rank Fusion](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)

## uvicorn api.main:app --host 0.0.0.0 --port 8000 