
import asyncio

from app.evaluation_service import create_evaluation_metrics


async def main():
    print("Starting RAGAS Answer Relevance Evaluation...")

    metrics = create_evaluation_metrics()
    answer_relevance = metrics["answer_relevancy"]

    user_input = "What is Python?"

    response = "Python is a programming language."

    print("\nEvaluation Input:")
    print("Question:", user_input)
    print("Generated Answer:", response)

    print("\nCalling Amazon Bedrock for evaluation...")

    result = await answer_relevance.ascore(
        user_input=user_input,
        response=response
    )

    print("\nAnswer Relevance Evaluation Result:")
    print("Score:", result.value)

    print("\nEvaluation completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())