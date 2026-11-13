
import asyncio

from app.evaluation_service import create_evaluation_metrics


async def main():
    print("Starting RAGAS Answer Correctness Evaluation...")

    metrics = create_evaluation_metrics()
    answer_correctness = metrics["answer_correctness"]

    user_input = "What is Python?"

    response = "Python is a programming language."

    reference = (
        "Python is a high-level programming language."
    )

    print("\nEvaluation Input:")
    print("Question:", user_input)
    print("Generated Answer:", response)
    print("Reference Answer:", reference)

    print("\nCalling Amazon Bedrock for evaluation...")

    result = await answer_correctness.ascore(
        user_input=user_input,
        response=response,
        reference=reference
    )

    print("\nAnswer Correctness Evaluation Result:")
    print("Score:", result.value)

    print("\nEvaluation completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())