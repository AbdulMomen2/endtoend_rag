import time
import logging
from typing import Dict, Any
from inference.memory import SessionMemoryManager
from inference.retriever import HybridRetriever
from inference.generator import GroundedGenerator
from core.logger import analytics_logger
from core.metrics import query_counter, latency_histogram, fallback_counter
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

_reformulate_llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.0)
_reformulate_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a query reformulation assistant.
Given a conversation history and a follow-up question, rewrite the question as a 
fully self-contained, standalone query that can be understood without the history.
- Resolve pronouns (it, they, this, that) to their referents
- Expand abbreviations if context makes them clear
- Keep it concise — one sentence
- If the question is already standalone, return it unchanged
- Return ONLY the reformulated query, nothing else."""),
    ("human", "History:\n{history}\n\nFollow-up: {query}")
])
_reformulate_chain = _reformulate_prompt | _reformulate_llm


def _reformulate_query(query: str, history: str) -> str:
    """Rewrite query to be standalone using conversation history."""
    if history == "No prior conversation." or len(query.split()) > 15:
        return query  # Already standalone or long enough
    try:
        result = _reformulate_chain.invoke({"history": history, "query": query})
        reformulated = result.content.strip()
        if reformulated and len(reformulated) > 3:
            return reformulated
    except Exception:
        pass
    return query

class ChatbotPipeline:
    def __init__(self, provider: str = "openai", model: str = "gpt-4o-mini"):
        self.memory = SessionMemoryManager()
        self.retriever = HybridRetriever(similarity_threshold=-8.0, use_reranker=False)
        self.generator = GroundedGenerator(provider=provider, model=model)
        self.exact_fallback = "This information is not present in the provided document."

    def chat(self, session_id: str, user_query: str, top_k: int = 5, doc_id: str = None) -> Dict[str, Any]:
        start_time = time.time()
        metrics = {"fallback_triggered": False}
        
        try:
            # 1. Fetch conversational context
            history = self.memory.get_history_string(session_id)
            
            # 2. Add user query to memory
            self.memory.add_message(session_id, "user", user_query)

            # 3. Reformulate query for better retrieval in multi-turn context
            retrieval_query = _reformulate_query(user_query, history)
            if retrieval_query != user_query:
                logger.info(f"Query reformulated: '{user_query}' → '{retrieval_query}'")

            # 4. Retrieve & Evaluate
            sources, short_circuit = self.retriever.retrieve_with_guardrails(
                retrieval_query, top_k=top_k, doc_id=doc_id
            )
            
            # 4. Generate or Short-Circuit
            if short_circuit or not sources:
                answer = self.exact_fallback
                metrics["fallback_triggered"] = True
            else:
                # 5. LLM Generation
                answer = self.generator.generate(user_query, history, sources)
                
                # Double-check if the LLM generated the fallback string
                if answer == self.exact_fallback:
                    metrics["fallback_triggered"] = True

            # 6. Save AI response to memory
            self.memory.add_message(session_id, "assistant", answer)

            metrics["latency_ms"] = round((time.time() - start_time) * 1000, 2)

            # Prometheus metrics
            query_counter.labels(session_type="fallback" if metrics["fallback_triggered"] else "rag").inc()
            latency_histogram.observe(metrics["latency_ms"] / 1000)
            if metrics["fallback_triggered"]:
                fallback_counter.inc()

            # 7. LOG ANALYTICS (Structured JSON)
            analytics_logger.log_interaction(
                session_id=session_id,
                query=user_query,
                response=answer,
                sources=sources if not metrics["fallback_triggered"] else[],
                metrics=metrics
            )
            
            # 8. Return formatted payload (satisfies Source Citation Bonus)
            return {
                "answer": answer,
                "sources": sources if not metrics["fallback_triggered"] else[],
                "latency_ms": metrics["latency_ms"],
                "session_id": session_id
            }

        except Exception as e:
            # Graceful degradation
            metrics["latency_ms"] = round((time.time() - start_time) * 1000, 2)
            analytics_logger.logger.error(f"Pipeline Error: {str(e)}")
            return {
                "answer": "An internal system error occurred.",
                "sources": [],
                "latency_ms": metrics["latency_ms"]
            }

# ==========================================
# Execution Example (Testing Phase 2)
# ==========================================
if __name__ == "__main__":
    import uuid
    chatbot = ChatbotPipeline()
    session = str(uuid.uuid4())
    
    # Test 1: Should PASS — query matches the document topic
    print("\n--- TEST 1: Valid Query (Document Topic) ---")
    res1 = chatbot.chat(session, "What Loss Function and Regularization used here?")
    print(f"Answer: {res1['answer']}")
    print(f"Sources: {res1['sources']}")
    
    # Test 2: Should trigger fallback — unrelated to the document
    print("\n--- TEST 2: Unrelated Query (Hallucination Control) ---")
    res2 = chatbot.chat(session, "Why dataset is a big issue in 2036?")
    print(f"Answer: {res2['answer']}")  # Expected: "This information is not present..."