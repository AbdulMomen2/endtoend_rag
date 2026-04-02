"""
Hybrid Retriever: Dense (FAISS) + Sparse (BM25) fused via Reciprocal Rank Fusion.
Cross-encoder reranking is optional — disabled by default for low-latency (<100ms retrieval).
"""
from typing import List, Tuple, Dict, Optional
import pickle, os, re
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from rank_bm25 import BM25Okapi
from core.config import config
from core.logger import track_latency
import logging

logger = logging.getLogger(__name__)

CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
CROSS_ENCODER_CACHE = "./models/cross_encoder"


def _tokenize(text: str) -> List[str]:
    return re.sub(r"[^a-z0-9\s]", "", text.lower()).split()


def _rrf(rankings: List[List[str]], k: int = 60) -> Dict[str, float]:
    """Reciprocal Rank Fusion across multiple ranked lists of doc ids."""
    scores: Dict[str, float] = {}
    for ranked in rankings:
        for rank, doc_id in enumerate(ranked):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return scores


class HybridRetriever:
    def __init__(self, similarity_threshold: float = -8.0, use_reranker: bool = False):
        """
        similarity_threshold: RRF score floor (only used when reranker is disabled).
        use_reranker: Enable cross-encoder reranking (~10-30s on CPU, use only with GPU).
        """
        self.embeddings = OpenAIEmbeddings(model=config.EMBEDDING_MODEL)
        self.index_path = config.FAISS_INDEX_PATH
        self.similarity_threshold = similarity_threshold
        self.reranker: Optional[object] = None

        # --- Dense index ---
        try:
            self.vector_store = FAISS.load_local(
                self.index_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            logger.info("FAISS index loaded.")
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            raise

        # --- Sparse BM25 index ---
        bm25_path = os.path.join(self.index_path, "bm25.pkl")
        if os.path.exists(bm25_path):
            with open(bm25_path, "rb") as f:
                data = pickle.load(f)
            self.bm25 = data["bm25"]
            self.bm25_docs = data["docs"]
            logger.info(f"BM25 index loaded ({len(self.bm25_docs)} chunks).")
        else:
            logger.warning("BM25 index not found. Run ingestion to build it.")
            self.bm25 = None
            self.bm25_docs = []

        # --- Cross-encoder reranker (optional, GPU recommended) ---
        if use_reranker:
            try:
                from sentence_transformers import CrossEncoder
                os.makedirs(CROSS_ENCODER_CACHE, exist_ok=True)
                self.reranker = CrossEncoder(CROSS_ENCODER_MODEL, cache_folder=CROSS_ENCODER_CACHE)
                logger.info(f"Cross-encoder loaded: {CROSS_ENCODER_MODEL}")
            except ImportError:
                logger.warning("sentence-transformers not installed. Install requirements-reranker.txt to enable reranking.")
            except Exception as e:
                logger.warning(f"Cross-encoder unavailable: {e}")
        else:
            logger.info("Cross-encoder disabled (use_reranker=False). Using RRF only.")

    @track_latency("Hybrid_Retrieval")
    def retrieve_with_guardrails(self, query: str, top_k: int = 3, doc_id: str = None) -> Tuple[List[Dict], bool]:
        """
        Hybrid retrieval with optional doc_id filter.
        If doc_id is provided, only chunks from that document are returned.
        """
        fetch_k = max(top_k * 4, 12)

        # 1. Dense
        dense_results = self.vector_store.similarity_search_with_score(query, k=fetch_k)

        # Filter by doc_id if specified
        if doc_id:
            dense_results = [(doc, score) for doc, score in dense_results
                             if doc.metadata.get("doc_id") == doc_id]

        dense_docs = {str(i): doc for i, (doc, _) in enumerate(dense_results)}
        dense_ranking = list(dense_docs.keys())

        # 2. Sparse BM25
        bm25_ranking = []
        bm25_id_map = {}
        if self.bm25 and self.bm25_docs:
            tokens = _tokenize(query)
            bm25_scores = self.bm25.get_scores(tokens)
            # Filter BM25 docs by doc_id if specified
            candidates = [
                (i, score) for i, score in enumerate(bm25_scores)
                if not doc_id or self.bm25_docs[i].metadata.get("doc_id") == doc_id
            ]
            candidates.sort(key=lambda x: x[1], reverse=True)
            for idx, _ in candidates[:fetch_k]:
                did = f"bm25_{idx}"
                bm25_id_map[did] = self.bm25_docs[idx]
                bm25_ranking.append(did)

        # 3. Deduplicate
        seen_hashes = set()
        all_candidates: Dict[str, any] = {}
        for did, doc in {**dense_docs, **bm25_id_map}.items():
            h = hash(doc.page_content)
            if h not in seen_hashes:
                seen_hashes.add(h)
                all_candidates[did] = doc

        # 4. RRF fusion
        all_rankings = [dense_ranking]
        if bm25_ranking:
            all_rankings.append(bm25_ranking)
        rrf_scores = _rrf(all_rankings)

        sorted_ids = sorted(all_candidates.keys(), key=lambda d: rrf_scores.get(d, 0), reverse=True)
        top_candidates = [(all_candidates[d], rrf_scores.get(d, 0)) for d in sorted_ids[:top_k]]

        # 5. Cross-encoder reranking
        if self.reranker and top_candidates:
            pairs = [(query, doc.page_content) for doc, _ in top_candidates]
            ce_scores = self.reranker.predict(pairs)
            reranked = sorted(zip(top_candidates, ce_scores), key=lambda x: x[1], reverse=True)
            top_candidates = [(doc, float(ce_score)) for (doc, _), ce_score in reranked]

        # 6. Format
        formatted_sources = []
        highest_score = -999.0
        for doc, score in top_candidates:
            norm_score = float(score)
            if norm_score > highest_score:
                highest_score = norm_score
            formatted_sources.append({
                "text": doc.page_content,
                "page": doc.metadata.get("page", "N/A"),
                "chunk_id": doc.metadata.get("chunk_id", "N/A"),
                "doc_id": doc.metadata.get("doc_id", ""),
                "filename": doc.metadata.get("filename", ""),
                "similarity_score": round(norm_score, 4)
            })

        logger.info(f"Retrieval: {len(formatted_sources)} chunks, top={highest_score:.4f}"
                    + (f", filtered to doc_id={doc_id}" if doc_id else ""))

        short_circuit = (
            self.reranker is not None
            and len(formatted_sources) > 0
            and highest_score < self.similarity_threshold
        )
        if short_circuit:
            logger.warning(f"Low relevance ({highest_score:.4f}). Short-circuiting.")

        return formatted_sources, short_circuit
