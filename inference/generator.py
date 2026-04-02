"""
Grounded generator supporting multiple LLM providers:
- OpenAI (gpt-4o-mini, gpt-4o, gpt-4-turbo)
- Google Gemini (gemini-1.5-flash, gemini-1.5-pro)
- Groq (llama-3.3-70b-versatile, mixtral-8x7b, gemma2-9b)
"""
from typing import List, Dict, AsyncIterator, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core.logger import track_latency
import logging

logger = logging.getLogger(__name__)

# NeMo Guardrails — optional
try:
    from nemoguardrails import RailsConfig
    from nemoguardrails.integrations.langchain.runnable_rails import RunnableRails
    import os as _os
    _rails_config = RailsConfig.from_path(
        _os.path.join(_os.path.dirname(__file__), "..", "guardrails")
    )
    GUARDRAILS_ENABLED = True
    logger.info("NVIDIA NeMo Guardrails loaded.")
except Exception as e:
    GUARDRAILS_ENABLED = False
    logger.warning(f"NeMo Guardrails not available: {e}")


# Available models per provider
AVAILABLE_MODELS = {
    "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
    "gemini": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
    "groq":   ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
}

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_PROVIDER = "openai"


def _build_llm(provider: str, model: str, streaming: bool = True):
    """Build LLM instance for the given provider and model."""
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model_name=model, temperature=0.0, streaming=streaming)

    elif provider == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            import os
            api_key = os.getenv("GOOGLE_API_KEY", "")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not set. Add it to your .env file.")
            return ChatGoogleGenerativeAI(
                model=model, temperature=0.0,
                streaming=streaming, google_api_key=api_key
            )
        except ImportError:
            raise ImportError("Run: pip install langchain-google-genai")

    elif provider == "groq":
        try:
            from langchain_groq import ChatGroq
            import os
            api_key = os.getenv("GROQ_API_KEY", "")
            if not api_key:
                raise ValueError("GROQ_API_KEY not set. Add it to your .env file.")
            return ChatGroq(model_name=model, temperature=0.0, groq_api_key=api_key)
        except ImportError:
            raise ImportError("Run: pip install langchain-groq")

    else:
        raise ValueError(f"Unknown provider: {provider}. Choose from: {list(AVAILABLE_MODELS.keys())}")


SYSTEM_PROMPT = """\
You are a senior research analyst. You have been given CONTEXT extracted from a document \
and must answer the user's question with depth, accuracy, and clarity.

## Strict Grounding Rules (Hallucination Control)
- Use ONLY facts explicitly stated in the CONTEXT below. Zero outside knowledge.
- Every sentence containing a fact MUST end with a page citation: (Page N).
- If multiple pages support a fact, cite all: (Pages 2, 4).
- If the CONTEXT does not contain enough information to answer, say EXACTLY:
  "This information is not present in the provided document."
- Never say "I think", "probably", "likely", or make assumptions.

## Answer Quality Rules
- Be comprehensive. Cover ALL relevant aspects from the context, not just the first match.
- Synthesize across chunks — connect related information from different pages.
- Always include: numbers, percentages, model names, dataset sizes, results when present.
- Use markdown: **bold** key terms, bullet lists for multiple items, headers for long answers.
- For methodology questions: describe the full pipeline step by step.
- For results questions: include all metrics and comparisons mentioned.
- For image/table content: describe what is shown based on the extracted description.

## Conversational Memory
- The CHAT HISTORY below shows prior turns. Use it to resolve pronouns and follow-up questions.

---
CHAT HISTORY:
{history}

---
CONTEXT (retrieved document chunks):
{context}

---
Remember: cite every fact with (Page N). Be thorough. No hallucination.
"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{query}"),
])

FALLBACK = "This information is not present in the provided document."
FALLBACK_TRIGGERS = [
    "not present in the provided document",
    "not found in the provided",
    "i don't know",
    "i cannot answer",
    "no information",
    "context does not",
    "not mentioned in",
]


class GroundedGenerator:
    def __init__(self, provider: str = DEFAULT_PROVIDER, model: str = DEFAULT_MODEL):
        self.fallback_string = FALLBACK
        self.provider = provider
        self.model = model
        self._init_error: Optional[str] = None

        try:
            llm = _build_llm(provider, model, streaming=True)
            self.base_chain = _prompt | llm | StrOutputParser()
            if GUARDRAILS_ENABLED:
                self.chain = RunnableRails(_rails_config, runnable=self.base_chain)
            else:
                self.chain = self.base_chain
            logger.info(f"Generator initialized: provider={provider}, model={model}")
        except (ImportError, ValueError) as e:
            self._init_error = str(e)
            logger.error(f"Generator init failed: {e}")
            # Fall back to OpenAI default
            if provider != "openai":
                logger.warning("Falling back to gpt-4o-mini")
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.0, streaming=True)
                self.base_chain = _prompt | llm | StrOutputParser()
                self.chain = self.base_chain

    def _build_context(self, sources: List[Dict]) -> str:
        parts = []
        for s in sources:
            page = s.get('page', 'N/A')
            score = s.get('similarity_score', 0)
            text = s.get('text', '')
            # Include image descriptions if present
            img_desc = s.get('image_description', '')
            chunk = f"[Page {page}] (score={score:.4f}):\n{text}"
            if img_desc:
                chunk += f"\n[Image on this page]: {img_desc}"
            parts.append(chunk)
        return "\n\n".join(parts)

    @track_latency("LLM_Generation")
    def generate(self, query: str, history: str, sources: List[Dict]) -> str:
        context_text = self._build_context(sources)
        try:
            result = self.chain.invoke({"context": context_text, "query": query, "history": history})
            response = result.get("output", result) if isinstance(result, dict) else result
            response = response.strip()
            if any(t in response.lower() for t in FALLBACK_TRIGGERS):
                return self.fallback_string
            return response
        except Exception as e:
            logger.error(f"LLM Generation failed: {e}")
            raise

    async def astream(self, query: str, history: str, sources: List[Dict]) -> AsyncIterator[str]:
        # Surface init errors immediately
        if self._init_error:
            yield f"\x00ERROR\x00{self._init_error}"
            return

        context_text = self._build_context(sources)
        full_response = []
        try:
            async for chunk in self.base_chain.astream(
                {"context": context_text, "query": query, "history": history}
            ):
                full_response.append(chunk)
                yield chunk

            complete = "".join(full_response)
            if any(t in complete.lower() for t in FALLBACK_TRIGGERS):
                yield "\x00FALLBACK\x00"

        except Exception as e:
            err = str(e)
            # Surface rate limit errors clearly
            if "429" in err or "rate_limit" in err.lower():
                logger.error(f"Rate limit hit during streaming: {e}")
                yield "\x00ERROR\x00Rate limit reached. Please wait a moment and try again."
            else:
                logger.error(f"LLM Streaming failed: {e}")
                yield "\x00ERROR\x00Generation failed. Please try again."
