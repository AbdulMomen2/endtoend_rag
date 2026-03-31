import time
from typing import Dict, Any
from inference.memory import SessionMemoryManager
from inference.retriever import HybridRetriever
from inference.generator import GroundedGenerator
from core.logger import analytics_logger
from dotenv import load_dotenv
load_dotenv()

class ChatbotPipeline:
    def __init__(self):
        self.memory = SessionMemoryManager()
        self.retriever = HybridRetriever(similarity_threshold=-8.0, use_reranker=False)
        self.generator = GroundedGenerator()
        self.exact_fallback = "This information is not present in the provided document."

    def chat(self, session_id: str, user_query: str, top_k: int = 5) -> Dict[str, Any]:
        start_time = time.time()
        metrics = {"fallback_triggered": False}
        
        try:
            # 1. Fetch conversational context
            history = self.memory.get_history_string(session_id)
            
            # 2. Add user query to memory
            self.memory.add_message(session_id, "user", user_query)
            
            # (Optional Bonus: Here we would add a lightweight LLM call to Reformulate the Query 
            # based on history, e.g., resolving "it" to "PTO policy". For brevity, omitted here.)

            # 3. Retrieve & Evaluate (The Guardrail)
            sources, short_circuit = self.retriever.retrieve_with_guardrails(user_query, top_k=top_k)
            
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