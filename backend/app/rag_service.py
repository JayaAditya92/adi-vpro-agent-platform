import os
import re
from pathlib import Path

from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from app.prompt_manager import load_prompt
from app.security_service import (
    moderation_check,
    secure_retrieved_context,
    validate_output,
)


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
MODEL_ID = os.getenv("BEDROCK_CHAT_MODEL_ID", "us.amazon.nova-2-lite-v1:0")

llm = ChatBedrockConverse(
    model=MODEL_ID,
    region_name=AWS_REGION,
    temperature=0.0,
    max_tokens=1000,
)

answer_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        load_prompt("rag_answer")
    ),
    (
        "human",
        "Student question: {question}"
    ),
])

answer_chain = answer_prompt | llm | StrOutputParser()


def _format_history(history):
    if not history:
        return "No previous conversation."

    lines = []
    for item in history:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "user")).strip().lower()
        content = str(item.get("content", "")).strip()
        if content:
            speaker = "Student" if role == "user" else "Assistant"
            lines.append(f"{speaker}: {content}")

    return "\n".join(lines) if lines else "No previous conversation."


def _extract_raw_context(retrieved_chunks):
    parts = []
    for chunk in retrieved_chunks or []:
        if isinstance(chunk, dict):
            value = str(chunk.get("content", "")).strip()
        elif chunk is not None:
            value = str(chunk).strip()
        else:
            value = ""
        if value:
            parts.append(value)
    return "\n".join(parts)


def _format_secure_context(retrieved_chunks):
    context_items = []
    for chunk in retrieved_chunks or []:
        if not isinstance(chunk, dict):
            context_items.append({"content": str(chunk)})
            continue

        content = (
            f"Filename: {chunk.get('filename', 'Unknown')}\n"
            f"Chunk number: {chunk.get('chunk_number', 'Unknown')}\n"
            f"Content:\n{chunk.get('content', '')}"
        )
        context_items.append({"content": content})

    return secure_retrieved_context(context_items)


_STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "what", "which", "who",
    "where", "when", "why", "how", "does", "do", "did", "can", "could",
    "would", "should", "please", "tell", "me", "about", "explain", "describe",
    "list", "mention", "mentions", "mentioned", "document", "documents",
    "knowledge", "and", "or", "of", "in", "on", "for", "to", "with",
    "that", "this", "it", "its", "there", "any", "all", "basic",
    "widely", "used", "use", "support", "supports", "supported",
    "python", "programming",
}

_PHRASES = (
    "object oriented programming",
    "artificial intelligence",
    "machine learning",
    "data science",
    "web development",
)


def _tokens(text):
    return {
        token.lower()
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", text)
        if token.lower() not in _STOP_WORDS and len(token) > 1
    }


def _sentences(text):
    # Join wrapped lines before splitting so a line break does not truncate lists.
    # Short title-like lines (no end punctuation) are headings: end them with a
    # period so they do not get glued onto the next sentence.
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(
        f"{line}." if 0 < len(line) < 60 and line[0].isupper()
        and line[-1] not in ".!?:;,)" else line
        for line in lines
    )
    normalized = re.sub(r"\s+", " ", text).strip()
    return [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+", normalized)
        if part.strip()
    ]


def _question_kind(question):
    q = question.strip().lower()

    if re.search(r"\b(why|how|explain|describe|compare|difference|example|write code|implement)\b", q):
        return "explanation"
    if re.match(r"^(what is|define)\b", q):
        return "definition"
    if re.search(r"\b(in which areas|where is|where are|used in|use cases|applications)\b", q):
        return "application_areas"
    if re.search(r"\b(mention|mentions|mentioned)\b", q) or "document" in q or "knowledge document" in q:
        return "document_fact"
    if re.search(r"\b(which|what)\b", q) and re.search(
        r"\b(concepts|features|types|methods|items|libraries|tools)\b", q
    ):
        return "list"
    if re.match(r"^(does|do|did|is|are|can|has|have)\b", q):
        return "yes_no"
    return "short_fact"


def _requested_phrases(question, context):
    q_lower = question.lower()
    c_lower = context.lower()
    return [phrase for phrase in _PHRASES if phrase in q_lower and phrase in c_lower]


def _requested_concepts(question, context):
    """
    Return only meaningful requested concepts, excluding the subject (Python)
    and question scaffolding (document/knowledge/mention/support).
    """
    phrases = _requested_phrases(question, context)
    q_tokens = _tokens(question)
    c_lower = context.lower()

    # Remove words already represented by recognized multiword phrases.
    phrase_words = {word for phrase in phrases for word in phrase.split()}
    terms = [
        token for token in sorted(q_tokens)
        if token not in phrase_words and re.search(rf"\b{re.escape(token)}\b", c_lower)
    ]

    labels = []
    for phrase in phrases:
        labels.append(phrase.title())

    for term in terms:
        labels.append(term.title())

    # Stable de-duplication.
    result = []
    seen = set()
    for label in labels:
        key = label.lower()
        if key not in seen:
            result.append(label)
            seen.add(key)
    return result


def _select_extractive_answer(question, retrieved_chunks):
    kind = _question_kind(question)
    if kind == "explanation":
        return None

    context = _extract_raw_context(retrieved_chunks)
    if not context:
        return None

    candidates = _sentences(context)
    if not candidates:
        return None

    q_lower = question.lower()

    if kind == "definition":
        definitions = [
            sentence for sentence in candidates
            if re.search(r"\b(is|are)\s+(a|an|the)\b", sentence.lower())
        ]
        if definitions:
            q_terms = _tokens(question)

            if not q_terms:
                # Generic question (e.g. "What is Python?"): prefer concise.
                return min(definitions, key=len)

            def overlap(sentence):
                # Compare singular forms so "container" matches "containers".
                singular = lambda words: {w.rstrip("s") for w in words}
                return len(singular(q_terms) & singular(_tokens(sentence)))

            best = max(definitions, key=lambda sent: (overlap(sent), -len(sent)))

            # Only trust the shortcut when the sentence really matches the
            # question; otherwise let the grounded LLM answer.
            if overlap(best) / len(q_terms) >= 0.5:
                return best
            return None

    if kind == "list":
        # Choose the source sentence that contains the requested enumeration.
        # A multi-item list is a stronger match than a single supported feature.
        support_sentences = [
            sentence for sentence in candidates
            if re.search(r"\b(support|supports)\b", sentence.lower())
        ]

        if support_sentences:
            def list_item_count(sentence):
                parts = re.split(r"\s*,\s*|\s+and\s+", sentence, flags=re.IGNORECASE)
                items = [part.strip(" .,:;") for part in parts if part.strip(" .,:;")]
                if items:
                    items[0] = re.sub(
                        r"^.+?\b(supports?|includes?|has)\b",
                        "",
                        items[0],
                        flags=re.IGNORECASE,
                    ).strip()
                return sum(1 for item in items if item)

            ranked_support = sorted(
                enumerate(support_sentences),
                key=lambda pair: (-list_item_count(pair[1]), pair[0]),
            )
            best_sentence = ranked_support[0][1]
            if list_item_count(best_sentence) >= 2:
                return best_sentence

            # No clear enumeration in the source: do not select an arbitrary
            # sentence; allow the grounded LLM fallback to answer.
            return None

    if kind == "application_areas":
        area_sentences = [
            sentence for sentence in candidates
            if re.search(r"\b(used|use|applications|areas)\b", sentence.lower())
        ]
        if area_sentences:
            return area_sentences[0]

    if kind == "yes_no":
        # Require the requested object/feature to appear in the same source
        # sentence as the relevant support/being relationship.
        requested_phrases = _requested_phrases(question, context)
        requested_terms = _tokens(question)

        for sentence in candidates:
            s_lower = sentence.lower()

            if requested_phrases:
                phrase_match = any(phrase in s_lower for phrase in requested_phrases)
            else:
                phrase_match = False

            # Fallback requires meaningful non-subject term overlap.
            term_match = bool(requested_terms & _tokens(sentence))

            if phrase_match and re.search(
                r"\b(supports|support|is|are|has|have|can)\b", s_lower
            ):
                return f"Yes. {sentence}"

            if not requested_phrases and term_match and re.search(
                r"\b(supports|support|is|are|has|have|can)\b", s_lower
            ):
                return f"Yes. {sentence}"

        return None

    if kind == "document_fact":
        concepts = _requested_concepts(question, context)
        if concepts:
            if len(concepts) == 1:
                concept_text = concepts[0]
            elif len(concepts) == 2:
                concept_text = f"{concepts[0]} and {concepts[1]}"
            else:
                concept_text = ", ".join(concepts[:-1]) + f", and {concepts[-1]}"
            return f"Yes. The document mentions {concept_text}."

    # Conservative fallback for short factual questions.
    q_tokens = _tokens(question)
    ranked = []
    for index, sentence in enumerate(candidates):
        overlap = len(q_tokens & _tokens(sentence))
        score = overlap / max(len(q_tokens), 1)
        score -= index * 0.001
        ranked.append((score, sentence))

    ranked.sort(key=lambda item: item[0], reverse=True)
    if ranked and ranked[0][0] >= 0.35:
        return ranked[0][1]

    return None


def generate_rag_answer(question, retrieved_chunks, history=None):
    """
    Prefer conservative source-grounded extraction for simple questions.
    Use Bedrock for explanations or when no reliable source sentence is found.
    Existing function signature and security checks are retained.
    """
    moderation = moderation_check(question)
    if not moderation["allowed"]:
        return (
            "I can't process this question because it was blocked by "
            f"the security checks. Reason: {moderation['reason']}"
        )

    answer = _select_extractive_answer(question, retrieved_chunks)

    if not answer:
        answer = answer_chain.invoke({
            "history": _format_history(history),
            "context": _format_secure_context(retrieved_chunks),
            "question": question,
        }).strip()

    if not answer:
        return "The available knowledge documents do not provide enough information to answer this question."

    validation = validate_output(answer)
    if not validation["safe"]:
        return (
            "I couldn't provide a response because it did not pass "
            "the output validation checks."
        )

    return validation["content"]