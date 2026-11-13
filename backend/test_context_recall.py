
import asyncio

from app.evaluation_service import create_evaluation_metrics


async def main():
    print("Starting RAGAS Context Recall Evaluation...")

    metrics = create_evaluation_metrics()
    context_recall = metrics["context_recall"]

    user_input = "Which programming concepts does Python support?"

    retrieved_contexts = [
        "Python supports variables and functions."
    ]

    reference = (
        "Python supports variables, functions, loops and conditions."
    )

    print("\nEvaluation Input:")
    print("Question:", user_input)
    print("Retrieved Contexts:", retrieved_contexts)
    print("Reference Answer:", reference)

    print("\nCalling Amazon Bedrock for evaluation...")

    result = await context_recall.ascore(
        user_input=user_input,
        retrieved_contexts=retrieved_contexts,
        reference=reference
    )

    print("\nContext Recall Evaluation Result:")
    print("Score:", result.value)

    print("\nEvaluation completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())