
import re


def normalize_text(text):
    """Convert text into lowercase words."""
    return re.findall(r"\b[a-z0-9]+\b", str(text).lower())


def contains_phrase(text, phrase):
    """Check whether a keyword or phrase exists in the text."""
    text_tokens = normalize_text(text)
    phrase_tokens = normalize_text(phrase)

    if not phrase_tokens:
        return False

    phrase_length = len(phrase_tokens)

    for index in range(len(text_tokens) - phrase_length + 1):
        if text_tokens[index:index + phrase_length] == phrase_tokens:
            return True

    return False


def evaluate_custom_metrics(
    question,
    answer,
    retrieved_contexts,
    required_keywords=None,
    min_answer_words=5,
    max_answer_words=300
):
    """
    Evaluate a RAG response using simple custom metrics.
    """

    required_keywords = required_keywords or []
    answer = answer or ""
    retrieved_contexts = retrieved_contexts or []

    # 1. Context Availability
    valid_contexts = [
        context.strip()
        for context in retrieved_contexts
        if isinstance(context, str) and context.strip()
    ]

    context_available = len(valid_contexts) > 0

    # 2. Empty Answer Detection
    answer_is_empty = not answer.strip()

    # 3. Answer Length
    answer_word_count = len(normalize_text(answer))

    answer_length_valid = (
        min_answer_words <= answer_word_count <= max_answer_words
    )

    # 4. Source Coverage
    combined_context = " ".join(valid_contexts)

    if required_keywords:
        covered_keywords = [
            keyword for keyword in required_keywords
            if contains_phrase(combined_context, keyword)
        ]

        source_coverage = (
            len(covered_keywords) / len(required_keywords)
        )
    else:
        covered_keywords = []
        source_coverage = None

    # 5. Keyword Matching
    if required_keywords:
        matched_keywords = [
            keyword for keyword in required_keywords
            if contains_phrase(answer, keyword)
        ]

        keyword_match_score = (
            len(matched_keywords) / len(required_keywords)
        )
    else:
        matched_keywords = []
        keyword_match_score = None

    return {
        "question": question,
        "context_available": context_available,
        "total_contexts": len(valid_contexts),
        "answer_is_empty": answer_is_empty,
        "answer_word_count": answer_word_count,
        "answer_length_valid": answer_length_valid,
        "source_coverage": source_coverage,
        "covered_keywords": covered_keywords,
        "keyword_match_score": keyword_match_score,
        "matched_keywords": matched_keywords
    }