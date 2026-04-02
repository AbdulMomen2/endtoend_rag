"""
RAGAS evaluation script for measuring RAG answer quality.
Metrics: faithfulness, answer_relevancy, context_precision, context_recall

Usage:
    pip install ragas datasets
    python tests/evaluate_rag.py

Requires a running vector index (run ingestion first).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Sample evaluation dataset — add your own Q&A pairs here
EVAL_DATASET = [
    {
        "question": "What dataset is used in this paper?",
        "ground_truth": "The MiRAGeNews dataset is used, containing 15,000 caption-image pairs."
    },
    {
        "question": "What model architecture is proposed?",
        "ground_truth": "CIVA-Net uses cross-modal attention fusion combining image and text encoders."
    },
    {
        "question": "What are the key results?",
        "ground_truth": "The model achieves competitive performance on the MiRAGeNews dataset compared to unimodal baselines."
    },
    {
        "question": "What loss function is used?",
        "ground_truth": "Binary cross-entropy loss with AdamW optimizer and weight decay regularization."
    },
]


def run_evaluation():
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_precision
        from datasets import Dataset
    except ImportError:
        print("Install evaluation deps: pip install ragas datasets")
        return

    from inference.pipeline import ChatbotPipeline
    import uuid

    print("Loading pipeline...")
    pipeline = ChatbotPipeline()
    session = str(uuid.uuid4())

    questions, answers, contexts, ground_truths = [], [], [], []

    print(f"Running {len(EVAL_DATASET)} evaluation queries...")
    for item in EVAL_DATASET:
        result = pipeline.chat(session_id=session, user_query=item["question"], top_k=5)
        questions.append(item["question"])
        answers.append(result["answer"])
        contexts.append([s["text"] for s in result.get("sources", [])])
        ground_truths.append(item["ground_truth"])
        print(f"  Q: {item['question'][:60]}...")
        print(f"  A: {result['answer'][:100]}...")
        print()

    dataset = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    })

    print("Running RAGAS evaluation...")
    results = evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_precision])

    print("\n" + "="*50)
    print("RAGAS Evaluation Results")
    print("="*50)
    print(f"Faithfulness:       {results['faithfulness']:.3f}  (1.0 = fully grounded)")
    print(f"Answer Relevancy:   {results['answer_relevancy']:.3f}  (1.0 = perfectly relevant)")
    print(f"Context Precision:  {results['context_precision']:.3f}  (1.0 = all context used)")
    print("="*50)

    return results


if __name__ == "__main__":
    run_evaluation()
