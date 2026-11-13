
from app.evaluation_service import (
    create_evaluation_models,
    create_evaluation_metrics
)


def main():

    print("Testing RAGAS and Amazon Bedrock configuration...")

    llm, embeddings = create_evaluation_models()

    print("Modern RAGAS LLM created successfully.")
    print("Modern RAGAS embedding model created successfully.")

    metrics = create_evaluation_metrics()

    print("\nAvailable evaluation metrics:")

    for name in metrics:
        print("-", name)

    print("\nRAGAS configuration completed successfully.")


if __name__ == "__main__":
    main()