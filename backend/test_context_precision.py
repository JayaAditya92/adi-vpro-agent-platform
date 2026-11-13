
import asyncio

from app.evaluation_service import create_evaluation_metrics


async def main():
    print("Starting RAGAS Context Precision Evaluation...")

    metrics = create_evaluation_metrics()
    context_precision = metrics["context_precision"]

    user_input = "What is Python?"

    response = "Python is a programming language."

    # First chunk is irrelevant.
    # Second chunk is relevant.
    retrieved_contexts = [
        "Java supports Object Oriented Programming.",
        "Python is a programming language."
    ]

    print("\nEvaluation Input:")
    print("Question:", user_input)
    print("Generated Answer:", response)

    print("\nRetrieved Contexts:")
    for index, context in enumerate(retrieved_contexts, start=1):
        print(f"Chunk {index}: {context}")

    print("\nCalling Amazon Bedrock for evaluation...")

    result = await context_precision.ascore(
        user_input=user_input,
        response=response,
        retrieved_contexts=retrieved_contexts
    )

    print("\nContext Precision Evaluation Result:")
    print("Score:", result.value)

    print("\nEvaluation completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())