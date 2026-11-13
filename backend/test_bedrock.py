
import boto3
import json

REGION = "us-east-1"
MODEL_ID = "us.amazon.nova-2-lite-v1:0"

client = boto3.client(
    "bedrock-runtime",
    region_name=REGION
)

try:

    response = client.converse(
        modelId=MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": "Explain Python in two simple sentences."
                    }
                ]
            }
        ],
        inferenceConfig={
            "maxTokens": 200,
            "temperature": 0.2
        }
    )

    answer = response["output"]["message"]["content"][0]["text"]

    print("\nBEDROCK CONNECTION SUCCESSFUL")
    print("\nMODEL RESPONSE:")
    print(answer)

except Exception as error:

    print("\nBEDROCK CONNECTION FAILED")
    print("Error type:", type(error).__name__)
    print("Error details:", str(error))