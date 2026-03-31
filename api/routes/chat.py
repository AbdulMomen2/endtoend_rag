"""Chat endpoints."""
import time
import json
import logging
import asyncio
import re
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.models.requests import ChatRequest
from api.models.responses import ChatResponse, SourceNode
from api.services.chatbot import ChatbotService
from api.services.cache import CacheService
from api.dependencies import get_chatbot_service, get_cache_service
from api.config import api_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Chat"])
limiter = Limiter(key_func=get_remote_address)

FALLBACK = "This information is not present in the provided document."

# Patterns that are conversational — don't route through RAG
_CONVERSATIONAL = re.compile(
    r"^(hi|hello|hey|thanks|thank you|ok|okay|sure|yes|no|bye|goodbye|"
    r"are you there|how are you|what('s| is) your name|who are you|"
    r"my name is|remember (me|my|that|this)|i am |i'm )",
    re.IGNORECASE
)

def _is_conversational(query: str) -> str | None:
    """
    Returns a friendly reply if the query is conversational, else None.
    Stores name mentions in a simple way via the response text.
    """
    q = query.strip().lower()

    if re.match(r"^(hi|hello|hey)\b", q):
        return "Hello! I'm your document assistant. Ask me anything about the ingested document and I'll answer strictly from its contents."

    if re.match(r"^(are you there|you there)\b", q):
        return "Yes, I'm here! Go ahead and ask your question about the document."

    if re.match(r"^(how are you|how r u)\b", q):
        return "I'm ready to help! What would you like to know about the document?"

    if re.match(r"^(thanks|thank you|thx)\b", q):
        return "You're welcome! Feel free to ask anything else about the document."

    if re.match(r"^(bye|goodbye|see you)\b", q):
        return "Goodbye! Come back anytime you have questions about the document."

    if re.match(r"^my name is (.+)", q):
        name = re.match(r"^my name is (.+)", q).group(1).strip().title()
        return f"Got it, {name}! I'll remember that for this conversation. What would you like to know about the document?"

    if re.match(r"^(who are you|what are you|what('s| is) your name)\b", q):
        return "I'm a RAG (Retrieval-Augmented Generation) document assistant. I answer questions strictly based on the content of the ingested document — no outside knowledge."

    return None


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(api_config.RATE_LIMIT)
async def chat_endpoint(
    request: Request,
    chat_request: ChatRequest,
    bot: ChatbotService = Depends(get_chatbot_service),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Process a chat query with caching and rate limiting.
    
    - **query**: User question (3-500 chars)
    - **session_id**: Unique session identifier
    - **top_k**: Number of chunks to retrieve (1-10)
    - **use_cache**: Enable response caching
    
    Returns answer with source citations and metadata.
    """
    start_time = time.perf_counter()
    
    # Check cache
    cache_key = cache.get_cache_key(chat_request.session_id, chat_request.query)
    
    if chat_request.use_cache:
        cached_response = cache.get(cache_key)
        if cached_response:
            logger.info(f"Cache hit for session {chat_request.session_id}")
            # Update latency and cached flag
            cached_response["cached"] = True
            cached_response["latency_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
            return ChatResponse(**cached_response)
    
    try:
        # Run chatbot in thread pool to avoid blocking event loop
        response_data = await asyncio.to_thread(
            bot.chat,
            session_id=chat_request.session_id,
            user_query=chat_request.query,
            top_k=chat_request.top_k
        )
        
        # Format sources
        formatted_sources = [
            SourceNode(
                page=src.get("page", "N/A"),
                text_snippet=src.get("text", "")[:300],  # Truncate for efficiency
                similarity_score=round(src.get("similarity_score", 0.0), 4)
            )
            for src in response_data.get("sources", [])
        ]
        
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        
        response = ChatResponse(
            answer=response_data["answer"],
            sources=formatted_sources,
            latency_ms=latency,
            session_id=chat_request.session_id,
            cached=False,
            fallback_triggered=len(formatted_sources) == 0
        )
        
        # Cache the response
        if chat_request.use_cache:
            cache.set(cache_key, response.model_dump())
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred processing your request. Please try again."
        )


@router.delete("/session/{session_id}")
@limiter.limit("10/minute")
async def clear_session(
    request: Request,
    session_id: str,
    bot: ChatbotService = Depends(get_chatbot_service),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Clear conversation history and cache for a session.
    """
    try:
        memory_cleared = bot.clear_session(session_id)
        cache_cleared = cache.clear_session(session_id)
        return {
            "status": "success",
            "message": f"Session {session_id} cleared",
            "memory_cleared": memory_cleared,
            "cache_entries_cleared": cache_cleared
        }
    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear session"
        )


@router.post("/chat/stream")
@limiter.limit(api_config.RATE_LIMIT)
async def chat_stream_endpoint(
    request: Request,
    chat_request: ChatRequest,
    bot: ChatbotService = Depends(get_chatbot_service),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).

    Streams tokens as they arrive from the LLM.
    First event contains sources metadata, subsequent events contain tokens.

    Event format:
    - `data: {"type": "sources", "sources": [...], "session_id": "..."}` — sent first
    - `data: {"type": "token", "content": "..."}` — one per token
    - `data: {"type": "done", "latency_ms": 123}` — final event
    - `data: {"type": "error", "detail": "..."}` — on failure
    """
    start_time = time.perf_counter()

    async def event_generator():
        try:
            # 0. Handle conversational queries — skip RAG entirely
            conversational_reply = _is_conversational(chat_request.query)
            if conversational_reply:
                # Save to memory
                bot.pipeline.memory.add_message(chat_request.session_id, "user", chat_request.query)
                bot.pipeline.memory.add_message(chat_request.session_id, "assistant", conversational_reply)
                yield f"data: {json.dumps({'type': 'sources', 'sources': [], 'session_id': chat_request.session_id, 'conversational': True})}\n\n"
                yield f"data: {json.dumps({'type': 'token', 'content': conversational_reply})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'latency_ms': round((time.perf_counter() - start_time) * 1000, 2)})}\n\n"
                return

            # 1. Retrieve sources
            sources, short_circuit = await asyncio.to_thread(
                bot.pipeline.retriever.retrieve_with_guardrails,
                chat_request.query,
                chat_request.top_k
            )

            formatted_sources = [
                {
                    "page": s.get("page", "N/A"),
                    "text_snippet": s.get("text", "")[:300],
                    "similarity_score": round(s.get("similarity_score", 0.0), 4)
                }
                for s in sources
            ]

            # 2. Send sources immediately
            yield f"data: {json.dumps({'type': 'sources', 'sources': formatted_sources, 'session_id': chat_request.session_id})}\n\n"

            if short_circuit or not sources:
                bot.pipeline.memory.add_message(chat_request.session_id, "user", chat_request.query)
                bot.pipeline.memory.add_message(chat_request.session_id, "assistant", FALLBACK)
                yield f"data: {json.dumps({'type': 'token', 'content': FALLBACK})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'latency_ms': round((time.perf_counter() - start_time) * 1000, 2), 'fallback': True})}\n\n"
                return

            # 3. Get history and save user message
            history = bot.pipeline.memory.get_history_string(chat_request.session_id)
            bot.pipeline.memory.add_message(chat_request.session_id, "user", chat_request.query)

            # 4. Stream tokens, watch for control signals
            full_response = []
            fallback_triggered = False

            async for token in bot.pipeline.generator.astream(
                query=chat_request.query,
                history=history,
                sources=sources
            ):
                if token == "\x00FALLBACK\x00":
                    fallback_triggered = True
                    break
                if token.startswith("\x00ERROR\x00"):
                    msg = token[8:]
                    yield f"data: {json.dumps({'type': 'error', 'detail': msg})}\n\n"
                    return
                full_response.append(token)
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            if fallback_triggered:
                # Clear streamed tokens and send clean fallback
                yield f"data: {json.dumps({'type': 'replace', 'content': FALLBACK})}\n\n"
                bot.pipeline.memory.add_message(chat_request.session_id, "assistant", FALLBACK)
            else:
                bot.pipeline.memory.add_message(chat_request.session_id, "assistant", "".join(full_response))

            latency = round((time.perf_counter() - start_time) * 1000, 2)
            yield f"data: {json.dumps({'type': 'done', 'latency_ms': latency, 'fallback': fallback_triggered})}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'detail': 'Stream failed. Please try again.'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Connection": "keep-alive",
        }
    )
