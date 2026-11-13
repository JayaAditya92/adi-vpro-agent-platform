
import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone

from app.evaluation_service import create_evaluation_metrics
from app.custom_evaluation import evaluate_custom_metrics


BASE_DIR = Path(__file__).resolve().parent

DATASET_PATH = BASE_DIR / "data" / "vpro_rag_evaluation_dataset.json"

REPORT_DIR = BASE_DIR / "reports"

# Start with one record to verify the complete pipeline.
# Change to None to evaluate all records.
MAX_RECORDS = None


async def evaluate_sample(sample, metrics):

    question = sample["question"]
    contexts = sample["retrieved_contexts"]
    answer = sample["generated_answer"]
    reference = sample["reference_answer"]

    print("\n" + "=" * 60)
    print("Evaluating:", question)
    print("=" * 60)

    results = {}

    # 1. Faithfulness
    results["faithfulness"] = (
        await metrics["faithfulness"].ascore(
            user_input=question,
            response=answer,
            retrieved_contexts=contexts
        )
    ).value

    print("Faithfulness:", results["faithfulness"])

    # 2. Context Precision
    results["context_precision"] = (
        await metrics["context_precision"].ascore(
            user_input=question,
            response=answer,
            retrieved_contexts=contexts
        )
    ).value

    print("Context Precision:", results["context_precision"])

    # 3. Context Recall
    results["context_recall"] = (
        await metrics["context_recall"].ascore(
            user_input=question,
            retrieved_contexts=contexts,
            reference=reference
        )
    ).value

    print("Context Recall:", results["context_recall"])

    # 4. Answer Relevance
    results["answer_relevance"] = (
        await metrics["answer_relevancy"].ascore(
            user_input=question,
            response=answer
        )
    ).value

    print("Answer Relevance:", results["answer_relevance"])

    # 5. Answer Correctness
    results["answer_correctness"] = (
        await metrics["answer_correctness"].ascore(
            user_input=question,
            response=answer,
            reference=reference
        )
    ).value

    print("Answer Correctness:", results["answer_correctness"])

    # Custom evaluation
    custom_results = evaluate_custom_metrics(
        question=question,
        answer=answer,
        retrieved_contexts=contexts,
        required_keywords=sample.get("required_keywords", [])
    )

    return {
        "question": question,
        "generated_answer": answer,
        "reference_answer": reference,
        "ragas_metrics": results,
        "custom_metrics": custom_results
    }


async def main():

    print("Starting Automated RAG Evaluation Pipeline...")

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Evaluation dataset not found: {DATASET_PATH}"
        )

    with open(DATASET_PATH, "r", encoding="utf-8") as file:
        dataset = json.load(file)

    if not isinstance(dataset, list) or not dataset:
        raise ValueError("Evaluation dataset must be a non-empty JSON list.")

    if MAX_RECORDS is not None:
        dataset = dataset[:MAX_RECORDS]

    print("Total records to evaluate:", len(dataset))

    metrics = create_evaluation_metrics()

    evaluation_results = []

    for index, sample in enumerate(dataset, start=1):

        print(f"\nProcessing record {index}/{len(dataset)}")

        try:
            result = await evaluate_sample(sample, metrics)
            result["status"] = "success"

        except Exception as error:
            print("Evaluation failed:", str(error))

            result = {
                "question": sample.get("question"),
                "status": "failed",
                "error": str(error)
            }

        evaluation_results.append(result)

    # Calculate average for each RAGAS metric
    metric_names = [
        "faithfulness",
        "context_precision",
        "context_recall",
        "answer_relevance",
        "answer_correctness"
    ]

    summary = {}

    successful_results = [
        item for item in evaluation_results
        if item["status"] == "success"
    ]

    for metric_name in metric_names:

        scores = [
            item["ragas_metrics"][metric_name]
            for item in successful_results
            if item["ragas_metrics"].get(metric_name) is not None
        ]

        summary[metric_name] = (
            sum(scores) / len(scores) if scores else None
        )

    report = {
        "project": "VPRO Skills Agentic AI",
        "evaluation_date": datetime.now(timezone.utc).isoformat(),
        "total_records": len(dataset),
        "successful_records": len(successful_results),
        "failed_records": len(dataset) - len(successful_results),
        "average_ragas_scores": summary,
        "results": evaluation_results
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report_path = REPORT_DIR / "rag_evaluation_report.json"

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("AUTOMATED RAG EVALUATION SUMMARY")
    print("=" * 60)

    for name, score in summary.items():
        print(f"{name}: {score}")

    print("\nSuccessful records:", len(successful_results))
    print("Failed records:", len(dataset) - len(successful_results))
    print("Report saved at:", report_path)

    print("\nAutomated RAG Evaluation Completed.")


if __name__ == "__main__":
    asyncio.run(main())