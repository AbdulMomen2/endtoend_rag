# Production API Setup Guide

## Overview

The API has been completely reorganized into a production-ready structure with proper separation of concerns:

- **Models**: Request/response schemas
- **Routes**: Endpoint handlers
- **Services**: Business logic (chatbot, cache)
- **Middleware**: Security, logging
- **Dependencies**: Dependency injection

## New Features

### 1. Redis Cache Layer

- **Primary**: Redis for distributed caching
- **Fallback**: In-memory cache if Redis unavailable
- **Auto-failover**: Seamlessly switches between Redis and memory
- **LRU Eviction**: Automatic cleanup of old entries

### 2. Organized Structure

```
api/
├── main.py              # App entry point
├── config.py            # Configuration
├── dependencies.py      # DI
├── middleware.py        # Custom middleware
├── models/              # Pydantic schemas
│   ├── requests.py
│   └── responses.py
├── routes/              # Endpoints
│   ├── chat.py
│   └── health.py
└── services/            # Business logic
    ├── cache.py         # Redis + memory cache
    └── chatbot.py       # Chatbot wrapper
```

### 3. Component Testing

Run `python3 api/test_components.py` to verify:
- All imports work
- Configuration loads correctly
- Redis connects (or falls back to memory)
- Chatbot initializes
- Query processing works

## Installation

### 1. Install Dependencies

```bash
# Activate venv
source rag/bin/activate

# Install all dependencies including Redis
pip install -r requirements.txt
```

### 2. Configure Environment

Add to `.env`:

```bash
# Existing
OPENAI_API_KEY=your-key-here
NVIDIA_API_KEY=your-key-here

# New Redis settings (optional - will use in-memory if not available)
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 3. Start Redis (Optional)

**Option A: Docker**
```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

**Option B: Local Install**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis
```

**Option C: Skip Redis**
The API will automatically fall back to in-memory caching if Redis is unavailable.

### 4. Test Components

```bash
PYTHONPATH=/home/momen/ZERO2AI/RAG python3 api/test_components.py
```

Expected output:
```
✅ All imports successful
✅ Configuration loaded successfully
✅ Redis is available and connected  (or ⚠️ using in-memory cache)
✅ Cache set/get working
✅ Chatbot service initialized successfully
✅ Query processed successfully
```

### 5. Start API

**Development:**
```bash
./start_api.sh
```

**Production (Docker):**
```bash
docker-compose up -d
```

## API Endpoints

### Health & Metrics

- `GET /health` - Health check with Redis status
- `GET /metrics` - Cache size, uptime, Redis status
- `GET /ready` - Kubernetes readiness probe
- `GET /live` - Kubernetes liveness probe

### Chat

- `POST /api/v1/chat` - Process query (rate limited: 30/min)
- `DELETE /api/v1/session/{id}` - Clear session (clears both memory and cache)

## Cache Behavior

### With Redis

1. Query comes in
2. Check Redis cache (SHA256 key)
3. If hit: return cached response (~5-10ms)
4. If miss: process query, cache in Redis (TTL: 5min)
5. Also cache in memory as backup

### Without Redis

1. Query comes in
2. Check in-memory cache
3. If hit: return cached response
4. If miss: process query, cache in memory
5. LRU eviction when cache > 100 entries

## Configuration

All settings in `api/config.py`:

```python
# Server
HOST = "0.0.0.0"
PORT = 8000

# Security
RATE_LIMIT = "30/minute"
MAX_QUERY_LENGTH = 500

# Cache
CACHE_ENABLED = True
CACHE_TTL = 300  # 5 minutes
CACHE_MAX_SIZE = 100  # In-memory limit

# Redis
REDIS_ENABLED = True
REDIS_HOST = "localhost"
REDIS_PORT = 6379
```

Override via environment variables:
```bash
export REDIS_HOST=redis-server.example.com
export CACHE_TTL=600
export RATE_LIMIT="60/minute"
```

## Monitoring

### Logs

Structured logging with request/response timing:

```
INFO: → POST /api/v1/chat from 127.0.0.1
INFO: Cache hit for session user-123
INFO: ← POST /api/v1/chat status=200 duration=8.45ms
```

### Metrics Endpoint

```bash
curl http://localhost:8000/metrics
```

Response:
```json
{
  "cache_size": 42,
  "uptime_seconds": 3600.5,
  "redis_enabled": true
}
```

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "index_loaded": true,
  "redis_connected": true,
  "timestamp": 1774897420.123
}
```

## Troubleshooting

### Redis Connection Failed

**Symptom**: `⚠️ Redis connection failed. Using in-memory cache`

**Solution**: This is not an error! The API automatically falls back to in-memory caching. To use Redis:

1. Start Redis: `docker run -d -p 6379:6379 redis:7-alpine`
2. Or disable: Set `REDIS_ENABLED=false` in `.env`

### Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'api'`

**Solution**: Run from project root with PYTHONPATH:
```bash
cd /home/momen/ZERO2AI/RAG
PYTHONPATH=$(pwd) python3 api/test_components.py
```

### Rate Limit Exceeded

**Symptom**: `429 Too Many Requests`

**Solution**: Adjust rate limit in `api/config.py` or wait 1 minute.

## Performance

### Latency Breakdown

| Scenario | Latency | Notes |
|----------|---------|-------|
| Cache hit (Redis) | 5-10ms | Network + deserialization |
| Cache hit (memory) | 1-3ms | In-process |
| Cache miss (first query) | 500-800ms | Model download |
| Cache miss (subsequent) | 200-400ms | Retrieval + generation |

### Scaling

**Single Instance**: Handles ~100 req/s with caching

**Multi-Instance**: 
1. Enable Redis for shared cache
2. Use external session store (Redis)
3. Deploy behind load balancer
4. Set `WORKERS=4` in docker-compose

## Security Checklist

- [x] Rate limiting (30/min per IP)
- [x] Input validation (Pydantic)
- [x] Query sanitization
- [x] Security headers (HSTS, X-Frame-Options, etc.)
- [x] Non-root Docker user
- [x] Trusted host middleware
- [x] CORS configuration
- [ ] TODO: API key authentication
- [ ] TODO: Request signing
- [ ] TODO: IP whitelist

## Next Steps

1. Install dependencies: `pip install -r requirements.txt`
2. Test components: `python3 api/test_components.py`
3. Start API: `./start_api.sh`
4. Test with client: `python3 api/example_client.py`
5. Deploy with Docker: `docker-compose up -d`
