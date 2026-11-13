
from app.custom_evaluation import evaluate_custom_metrics


def main():

    print("Starting Custom RAG Evaluation...")

    question = "Which programming concepts does Python support?"

    retrieved_contexts = [
        "Python supports variables and functions.",
        "Python supports loops and conditions."
    ]

    answer = (
        "Python supports variables, functions, "
        "loops and conditions."
    )

    required_keywords = [
        "variables",
        "functions",
        "loops",
        "conditions"
    ]

    result = evaluate_custom_metrics(
        question=question,
        answer=answer,
        retrieved_contexts=retrieved_contexts,
        required_keywords=required_keywords,
        min_answer_words=5,
        max_answer_words=100
    )

    print("\nCustom Evaluation Results:")

    for metric, value in result.items():
        print(f"{metric}: {value}")

    print("\nCustom RAG Evaluation Completed Successfully.")


if __name__ == "__main__":
    main()