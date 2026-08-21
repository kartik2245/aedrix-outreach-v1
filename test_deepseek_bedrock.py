"""
test_deepseek_bedrock.py
Standalone test script for AWS Bedrock DeepSeek V3.2 using AWS CLI credentials via boto3.Session.
"""

import os
import boto3
from dotenv import load_dotenv

load_dotenv()

# Ensure no empty bearer token in env overrides SigV4 signing
os.environ.pop("AWS_BEARER_TOKEN_BEDROCK", None)
os.environ.pop("AWS_BEARER_TOKEN", None)

region = os.getenv("AWS_REGION", "ap-south-1")
model_id = os.getenv("BEDROCK_MODEL_ID", "deepseek.v3.2")

print("==================================================")
print(" AWS BEDROCK DEEPSEEK V3.2 CONNECTIVITY TEST")
print("==================================================")
print(f" AWS Region:       {region}")
print(f" Bedrock Model ID: {model_id}")
print(f" Auth Mode:        AWS CLI Standard Credentials (SigV4)")
print("--------------------------------------------------")

try:
    session = boto3.Session(region_name=region)
    client = session.client("bedrock-runtime")

    response = client.converse(
        modelId=model_id,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": "Reply with exactly: DeepSeek Bedrock connection successful."
                    }
                ],
            }
        ],
    )

    model_response = response["output"]["message"]["content"][0]["text"]
    print("\nModel Response:")
    print(model_response)
    print("\n[SUCCESS] AWS Bedrock DeepSeek V3.2 connection test passed!")

except Exception as e:
    print(f"\n[FAILURE] AWS Bedrock connection error: {e}")
