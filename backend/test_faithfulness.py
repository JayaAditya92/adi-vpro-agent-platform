
import asyncio

from app.evaluation_service import create_evaluation_metrics


async def main():

    print("Starting RAGAS Faithfulness Evaluation...")

    metrics = create_evaluation_metrics()
    faithfulness = metrics["faithfulness"]

    user_input = "What is Python?"

    retrieved_contexts = [
        "Python is a programming language."
    ]

    response = "Python is a programming language."

    print("\nEvaluation Input:")
    print("Question:", user_input)
    print("Retrieved Context:", retrieved_contexts)
    print("Generated Answer:", response)

    print("\nCalling Amazon Bedrock for evaluation...")

    result = await faithfulness.ascore(
        user_input=user_input,
        response=response,
        retrieved_contexts=retrieved_contexts
    )

    print("\nFaithfulness Evaluation Result:")
    print("Score:", result.value)

    print("\nEvaluation completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())