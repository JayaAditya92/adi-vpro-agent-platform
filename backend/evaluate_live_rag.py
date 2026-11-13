
import asyncio
import json
import urllib.request
import urllib.error

from pathlib import Path
from datetime import datetime, timezone

from app.database import SessionLocal
from app import models
from app.evaluation_service import create_evaluation_metrics
from app.custom_evaluation import evaluate_custom_metrics


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DATASET_PATH = (
    BASE_DIR / "data" / "vpro_rag_evaluation_dataset.json"
)

REPORT_DIR = BASE_DIR / "reports"

REPORT_PATH = (
    REPORT_DIR / "live_rag_evaluation_report.json"
)

RAG_API_URL = "http://localhost:8000/api/rag/ask"

MAX_RECORDS = None

API_TIMEOUT = 120


# --------------------------------------------------
# CALL LIVE RAG API
# --------------------------------------------------

def call_live_rag_api(question):

    payload = json.dumps({
        "question": question
    }).encode("utf-8")

    request = urllib.request.Request(
        RAG_API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=API_TIMEOUT
        ) as response:

            return json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as error:

        error_body = error.read().decode(
            "utf-8",
            errors="replace"
        )

        raise RuntimeError(
            f"RAG API returned HTTP {error.code}: {error_body}"
        )

    except urllib.error.URLError as error:

        raise RuntimeError(
            f"Cannot connect to RAG API: {error.reason}"
        )


# --------------------------------------------------
# FETCH ACTUAL RETRIEVED CHUNK CONTENT
# --------------------------------------------------

def fetch_retrieved_contexts(sources):

    contexts = []

    db = SessionLocal()

    try:
        for source in sources:

            document_id = source.get("document_id")
            chunk_number = source.get("chunk_number")

            if document_id is None or chunk_number is None:
                continue

            chunk = (
                db.query(models.DocumentChunk)
                .filter(
                    models.DocumentChunk.document_id == document_id,
                    models.DocumentChunk.chunk_number == chunk_number
                )
                .first()
            )

            if chunk:
                contexts.append(chunk.content)

    finally:
        db.close()

    return contexts


# --------------------------------------------------
# EVALUATE ONE LIVE RAG RESPONSE
# --------------------------------------------------

async def evaluate_record(
    record,
    metrics,
    record_number
):

    question = record["question"]
    reference_answer = record["reference_answer"]

    print("\n" + "=" * 60)
    print(f"Live Evaluation Record: {record_number}")
    print(f"Question: {question}")
    print("=" * 60)

    # Step 1: Call actual RAG application
    api_result = call_live_rag_api(question)

    if api_result.get("status") != "success":
        raise RuntimeError(
            f"RAG API did not succeed: {api_result}"
        )

    generated_answer = api_result.get("answer", "")

    if not generated_answer.strip():
        raise ValueError("Live RAG returned an empty answer.")

    # Step 2: Get actual source metadata
    sources = api_result.get("sources", [])

    # Step 3: Fetch actual chunk text from PostgreSQL
    retrieved_contexts = fetch_retrieved_contexts(sources)

    print("Retrieved sources:", len(sources))
    print("Retrieved contexts:", len(retrieved_contexts))

    if sources and not retrieved_contexts:
        raise ValueError(
            "Sources were returned, but no matching chunk content "
            "was found in PostgreSQL."
        )

    # Step 4: Run RAGAS metrics
    faithfulness = await metrics["faithfulness"].ascore(
        user_input=question,
        response=generated_answer,
        retrieved_contexts=retrieved_contexts
    )

    context_precision = await metrics["context_precision"].ascore(
        user_input=question,
        response=generated_answer,
        retrieved_contexts=retrieved_contexts
    )

    context_recall = await metrics["context_recall"].ascore(
        user_input=question,
        retrieved_contexts=retrieved_contexts,
        reference=reference_answer
    )

    answer_relevance = await metrics["answer_relevancy"].ascore(
        user_input=question,
        response=generated_answer
    )

    answer_correctness = await metrics["answer_correctness"].ascore(
        user_input=question,
        response=generated_answer,
        reference=reference_answer
    )

    ragas_scores = {
        "faithfulness": float(faithfulness),
        "context_precision": float(context_precision),
        "context_recall": float(context_recall),
        "answer_relevance": float(answer_relevance),
        "answer_correctness": float(answer_correctness)
    }

    # Step 5: Custom evaluation
    custom_scores = evaluate_custom_metrics(
        question=question,
        answer=generated_answer,
        retrieved_contexts=retrieved_contexts,
        required_keywords=record.get("required_keywords", [])
    )

    print("\nRAGAS Scores:")

    for metric, score in ragas_scores.items():
        print(f"{metric}: {score:.4f}")

    return {
        "question": question,
        "reference_answer": reference_answer,
        "generated_answer": generated_answer,
        "total_sources": api_result.get("total_sources", 0),
        "retrieved_contexts": retrieved_contexts,
        "ragas_metrics": ragas_scores,
        "custom_metrics": custom_scores,
        "status": "success"
    }


# --------------------------------------------------
# MAIN EVALUATION PIPELINE
# --------------------------------------------------

async def main():

    print("\nStarting LIVE RAG Evaluation Pipeline...")

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}"
        )

    with open(DATASET_PATH, "r", encoding="utf-8") as file:
        dataset = json.load(file)

    if not isinstance(dataset, list):
        raise ValueError("Evaluation dataset must be a JSON list.")

    if MAX_RECORDS is not None:
        dataset = dataset[:MAX_RECORDS]

    print("Total records:", len(dataset))

    if not dataset:
        raise ValueError("No evaluation records found.")

    # Create RAGAS models and metrics once
    print("\nInitializing RAGAS evaluation models...")

    metrics = create_evaluation_metrics()

    results = []

    # Process records one by one
    for index, record in enumerate(dataset, start=1):

        try:
            result = await evaluate_record(
                record,
                metrics,
                index
            )

            results.append(result)

        except Exception as error:

            print(f"\nRecord {index} failed: {error}")

            results.append({
                "question": record.get("question"),
                "status": "failed",
                "error": str(error)
            })

    # Calculate average scores
    metric_names = [
        "faithfulness",
        "context_precision",
        "context_recall",
        "answer_relevance",
        "answer_correctness"
    ]

    successful_results = [
        result for result in results
        if result["status"] == "success"
    ]

    failed_count = len(results) - len(successful_results)

    average_scores = {}

    for metric in metric_names:

        values = [
            result["ragas_metrics"][metric]
            for result in successful_results
            if result["ragas_metrics"].get(metric) is not None
        ]

        average_scores[metric] = (
            sum(values) / len(values)
            if values else None
        )

    # Build final report
    report = {
        "project": "VPRO Skills Live RAG Evaluation",
        "evaluation_date": datetime.now(
            timezone.utc
        ).isoformat(),
        "evaluation_type": "live_rag_api",
        "total_records": len(results),
        "successful_records": len(successful_results),
        "failed_records": failed_count,
        "average_ragas_scores": average_scores,
        "results": results
    }

    # Save JSON report
    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(REPORT_PATH, "w", encoding="utf-8") as file:

        json.dump(
            report,
            file,
            indent=4,
            ensure_ascii=False
        )

    # Display summary
    print("\n" + "=" * 60)
    print("LIVE RAG EVALUATION SUMMARY")
    print("=" * 60)

    for metric, score in average_scores.items():

        if score is not None:
            print(f"{metric}: {score:.4f}")
        else:
            print(f"{metric}: N/A")

    print("\nSuccessful records:", len(successful_results))
    print("Failed records:", failed_count)

    print("\nReport saved at:")
    print(REPORT_PATH)

    print("\nLIVE RAG Evaluation Completed.")


if __name__ == "__main__":
    asyncio.run(main())