#!/bin/bash
# Quick start script for RAG API

set -e

echo "🚀 Starting RAG API Server..."
echo ""

# Check if vector DB exists
if [ ! -d "vector_db/faiss_index" ]; then
    echo "❌ Vector database not found!"
    echo "   Please run ingestion first:"
    echo "   python3 -m ingestion.pipeline"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "   Please create .env with your OPENAI_API_KEY"
    exit 1
fi

# Check dependencies
echo "📦 Checking dependencies..."
python3 -c "import fastapi, uvicorn, slowapi" 2>/dev/null || {
    echo "❌ Missing API dependencies. Installing..."
    pip install fastapi uvicorn slowapi python-multipart
}

echo "✅ All checks passed"
echo ""
echo "🌐 Starting server on http://localhost:8000"
echo "📚 API docs: http://localhost:8000/docs"
echo ""

# Start the server
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
