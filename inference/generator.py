"""
Robust grounded generator with structured chain-of-thought prompting.
Uses NeMo Guardrails when available, degrades gracefully otherwise.
"""
from typing import List, Dict, AsyncIterator
from langchain_openai import ChatOpenAI
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
    logger.warning(f"NeMo Guardrails not available, running without: {e}")


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

## Conversational Memory
- The CHAT HISTORY below shows prior turns. Use it to resolve pronouns and follow-up questions.
- Example: if user said "tell me about the model" then asks "what dataset did it use?", \
  resolve "it" from history.

---
CHAT HISTORY:
{history}

---
CONTEXT (retrieved document chunks):
{context}

---
Remember: cite every fact with (Page N). Be thorough. No hallucination.
"""

HUMAN_PROMPT = "{query}"

_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", HUMAN_PROMPT),
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
    def __init__(self):
        self.fallback_string = FALLBACK
        self.llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.0, streaming=True)
        self.base_chain = _prompt | self.llm | StrOutputParser()

        if GUARDRAILS_ENABLED:
            self.chain = RunnableRails(_rails_config, runnable=self.base_chain)
        else:
            self.chain = self.base_chain

    def _build_context(self, sources: List[Dict]) -> str:
        return "\n\n".join(
            [f"[Page {s['page']}] (score={s['similarity_score']}):\n{s['text']}" for s in sources]
        )

    @track_latency("LLM_Generation")
    def generate(self, query: str, history: str, sources: List[Dict]) -> str:
        """Blocking generation — returns full response string."""
        context_text = self._build_context(sources)
        try:
            result = self.chain.invoke({
                "context": context_text,
                "query": query,
                "history": history,
            })
            response = result.get("output", result) if isinstance(result, dict) else result
            response = response.strip()
            if any(trigger in response.lower() for trigger in FALLBACK_TRIGGERS):
                return self.fallback_string
            return response
        except Exception as e:
            logger.error(f"LLM Generation failed: {e}")
            raise

    async def astream(self, query: str, history: str, sources: List[Dict]) -> AsyncIterator[str]:
        """
        Async streaming generation — yields tokens as they arrive.
        Uses base_chain directly (guardrails don't support streaming yet).
        """
        context_text = self._build_context(sources)
        full_response = []
        fallback_detected = False

        try:
            async for chunk in self.base_chain.astream({
                "context": context_text,
                "query": query,
                "history": history,
            }):
                full_response.append(chunk)
                yield chunk

            # Post-stream fallback check — replace entire response if needed
            complete = "".join(full_response)
            if any(trigger in complete.lower() for trigger in FALLBACK_TRIGGERS):
                fallback_detected = True

            if fallback_detected:
                # Signal client to replace content with clean fallback (no raw tag)
                yield f"\x00FALLBACK\x00"

        except Exception as e:
            logger.error(f"LLM Streaming failed: {e}")
            yield f"\x00ERROR\x00Generation failed. Please try again."
