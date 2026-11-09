
import json
import os

import boto3

from dotenv import load_dotenv
from pathlib import Path


# Load backend environment variables
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path)


# Read AWS configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

MODEL_ID = os.getenv(
    "BEDROCK_EMBEDDING_MODEL_ID",
    "amazon.titan-embed-text-v2:0"
)

DIMENSIONS = int(
    os.getenv("EMBEDDING_DIMENSIONS", "1024")
)


# Create Bedrock client
bedrock_client = boto3.client(
    service_name="bedrock-runtime",
    region_name=AWS_REGION
)


# Generate embedding for one text chunk
def generate_embedding(text):

    if not text.strip():
        raise ValueError("Text cannot be empty")

    request_body = {
        "inputText": text,
        "dimensions": DIMENSIONS,
        "normalize": True
    }

    response = bedrock_client.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(request_body),
        accept="application/json",
        contentType="application/json"
    )

    response_body = json.loads(
        response["body"].read()
    )

    embedding = response_body["embedding"]

    if len(embedding) != DIMENSIONS:
        raise ValueError("Unexpected embedding dimensions")

    return embedding