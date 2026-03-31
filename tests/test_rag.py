import pytest
from unittest.mock import MagicMock, patch
from inference.pipeline import ChatbotPipeline

# ==========================================
# Test Suite Setup
# ==========================================
@pytest.fixture
def chatbot():
    """
    Pytest fixture to initialize the ChatbotPipeline.
    We mock the FAISS loading so we don't need a real DB to run unit tests.
    """
    with patch('inference.retriever.FAISS.load_local'):
        bot = ChatbotPipeline()
        return bot

# ==========================================
# Test Case 1: Strict Fallback Requirement
# ==========================================
def test_exact_fallback_string_on_low_confidence(chatbot):
    """
    REQUIREMENT #4 TEST:
    If the vector DB returns low similarity scores (short-circuit triggered), 
    the system MUST return the exact hardcoded string.
    """
    exact_required_string = "This information is not present in the provided document."
    
    # Mock the retriever to simulate a situation where no relevant chunks are found 
    # (short_circuit = True)
    chatbot.retriever.retrieve_with_guardrails = MagicMock(return_value=([], True))
    
    # Execute
    result = chatbot.chat(session_id="test_session_1", user_query="How do I bake a cake?")
    
    # ASSERTIONS
    assert result["answer"] == exact_required_string, \
        f"Expected exact string, got: {result['answer']}"
    assert len(result["sources"]) == 0, "Sources should be empty on fallback."

# ==========================================
# Test Case 2: Output Guardrail Sanitization
# ==========================================
def test_llm_hallucination_sanitization(chatbot):
    """
    REQUIREMENT #4 TEST (Defense in Depth):
    Even if chunks are found, if the LLM decides the answer isn't there and 
    generates a slight variation like "I'm sorry, this information is not present.",
    our output guardrail MUST catch it and overwrite it with the exact string.
    """
    exact_required_string = "This information is not present in the provided document."
    
    # 1. Mock retriever to pretend it found valid chunks
    mock_sources =[{"page": 1, "text": "Some text", "similarity_score": 0.9}]
    chatbot.retriever.retrieve_with_guardrails = MagicMock(return_value=(mock_sources, False))
    
    # 2. Mock the LLM generator to output a slight variation of the failure string
    chatbot.generator.generate = MagicMock(return_value="I am sorry, but this information is not present in the provided document.")
    
    # Execute
    result = chatbot.chat(session_id="test_session_2", user_query="What is XYZ?")
    
    # ASSERTION: The pipeline should have intercepted the LLM's apology and forced the exact string.
    assert result["answer"] == exact_required_string, "Output guardrail failed to sanitize LLM output."

# ==========================================
# Test Case 3: Memory Context Continuity
# ==========================================
def test_conversational_memory_continuity(chatbot):
    """
    REQUIREMENT #5 TEST:
    Ensure the system maintains conversation context across multiple turns.
    """
    session_id = "memory_test_session"
    
    # Mock retrieval and generation to just pass through
    chatbot.retriever.retrieve_with_guardrails = MagicMock(return_value=([{"page": 1, "text": "...", "similarity_score": 0.99}], False))
    chatbot.generator.generate = MagicMock(return_value="Valid answer.")
    
    # Turn 1
    chatbot.chat(session_id=session_id, user_query="What is the PTO policy?")
    
    # Turn 2
    chatbot.chat(session_id=session_id, user_query="How many days is it?")
    
    # Fetch memory
    history = chatbot.memory.get_history_string(session_id)
    
    # ASSERTIONS: Memory must contain both user queries and the assistant's reply
    assert "User: What is the PTO policy?" in history
    assert "Assistant: Valid answer." in history
    assert "User: How many days is it?" in history