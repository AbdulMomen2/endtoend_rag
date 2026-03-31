"""
Example client for the RAG API.
Demonstrates proper usage with error handling and session management.
"""
import requests
import uuid
import time
from typing import Dict, Any


class RAGClient:
    """Production-ready client for RAG API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = str(uuid.uuid4())
        self.session = requests.Session()
        
    def health_check(self) -> Dict[str, Any]:
        """Check if API is healthy."""
        response = self.session.get(f"{self.base_url}/health", timeout=5)
        response.raise_for_status()
        return response.json()
    
    def chat(
        self,
        query: str,
        top_k: int = 3,
        use_cache: bool = True,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Send a chat query to the API.
        
        Args:
            query: User question
            top_k: Number of chunks to retrieve (1-10)
            use_cache: Enable response caching
            timeout: Request timeout in seconds
            
        Returns:
            API response with answer and sources
        """
        payload = {
            "query": query,
            "session_id": self.session_id,
            "top_k": top_k,
            "use_cache": use_cache
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/chat",
            json=payload,
            timeout=timeout
        )
        response.raise_for_status()
        return response.json()
    
    def clear_session(self) -> Dict[str, Any]:
        """Clear conversation history."""
        response = self.session.delete(
            f"{self.base_url}/api/v1/session/{self.session_id}",
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    
    def new_session(self):
        """Start a new conversation session."""
        self.session_id = str(uuid.uuid4())


def main():
    """Example usage."""
    client = RAGClient()
    
    # Check health
    print("🔍 Checking API health...")
    health = client.health_check()
    print(f"✅ API Status: {health['status']}")
    print(f"   Version: {health['version']}")
    print(f"   Index Loaded: {health['index_loaded']}\n")
    
    # Example conversation
    queries = [
        "What dataset is used in this paper?",
        "How many validation pairs are there?",
        "What is the company PTO policy?"  # Should trigger fallback
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"{'='*60}")
        print(f"Query {i}: {query}")
        print(f"{'='*60}")
        
        try:
            start = time.time()
            response = client.chat(query, top_k=3)
            elapsed = time.time() - start
            
            print(f"Answer: {response['answer']}\n")
            
            if response['sources']:
                print(f"Sources ({len(response['sources'])}):")
                for j, source in enumerate(response['sources'], 1):
                    print(f"  {j}. Page {source['page']} (score: {source['similarity_score']:.4f})")
                    print(f"     {source['text_snippet'][:150]}...\n")
            else:
                print("No sources (fallback triggered)\n")
            
            print(f"Latency: {response['latency_ms']:.2f}ms (total: {elapsed*1000:.2f}ms)")
            print(f"Cached: {response.get('cached', False)}")
            print(f"Fallback: {response.get('fallback_triggered', False)}\n")
            
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
            print(f"   Response: {e.response.text}\n")
        except requests.exceptions.Timeout:
            print(f"❌ Request timed out\n")
        except Exception as e:
            print(f"❌ Error: {e}\n")
    
    # Clear session
    print("🧹 Clearing session...")
    result = client.clear_session()
    print(f"✅ {result['message']}\n")


if __name__ == "__main__":
    main()
