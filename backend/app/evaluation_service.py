import os
from pathlib import Path
import litellm
import instructor

from dotenv import load_dotenv
from ragas.llms import llm_factory
from ragas.embeddings.base import embedding_factory

from ragas.metrics.collections import (
    Faithfulness,
    ContextPrecisionWithoutReference,
    ContextRecall,
    AnswerRelevancy,
    AnswerCorrectness,
)

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
CHAT_MODEL_ID = os.getenv(
    "BEDROCK_CHAT_MODEL_ID",
    "us.amazon.nova-2-lite-v1:0"
)
EMBEDDING_MODEL_ID = os.getenv(
    "BEDROCK_EMBEDDING_MODEL_ID",
    "amazon.titan-embed-text-v2:0"
)


# Define this function BEFORE create_evaluation_models()
async def bedrock_acompletion(*args, **kwargs):
    response = await litellm.acompletion(*args, **kwargs)

    for choice in response.choices:
        content = choice.message.content

        if isinstance(content, str):
            content = content.strip()

            if content.startswith("```"):
                lines = content.splitlines()

                if lines and lines[0].startswith("```"):
                    lines = lines[1:]

                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]

                choice.message.content = "\n".join(lines).strip()

    return response


def create_evaluation_models():
    os.environ["AWS_REGION_NAME"] = AWS_REGION
    os.environ["AWS_DEFAULT_REGION"] = AWS_REGION

    
    ragas_llm = llm_factory(
    model=f"bedrock/{CHAT_MODEL_ID}",
    provider="litellm",
    client=bedrock_acompletion,
    adapter="instructor",
    temperature=0,
    max_tokens=4096
    )


    ragas_embeddings = embedding_factory(
        provider="litellm",
        model=f"bedrock/{EMBEDDING_MODEL_ID}"
    )

    return ragas_llm, ragas_embeddings


def create_evaluation_metrics():
    ragas_llm, ragas_embeddings = create_evaluation_models()

    return {
        "faithfulness": Faithfulness(llm=ragas_llm),
        "context_precision": ContextPrecisionWithoutReference(llm=ragas_llm),
        "context_recall": ContextRecall(llm=ragas_llm),
        "answer_relevancy": AnswerRelevancy(
            llm=ragas_llm,
            embeddings=ragas_embeddings
        ),
        "answer_correctness": AnswerCorrectness(
            llm=ragas_llm,
            embeddings=ragas_embeddings
        )
    }