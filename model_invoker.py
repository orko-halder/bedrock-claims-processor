"""
Model Invoker — single choke point for every Bedrock call, with the
retry logic none of today's step-by-step scripts had. Everything else
in this project calls through here rather than touching boto3 directly.
"""

import json
import logging
import time

import boto3
from botocore.exceptions import ClientError

import config

logger = logging.getLogger("model_invoker")


class ModelInvoker:
    def __init__(self, region: str = config.AWS_REGION, max_retries: int = 3):
        self.client = boto3.client("bedrock-runtime", region_name=region)
        self.max_retries = max_retries

    def invoke(
        self,
        model_id: str,
        messages: list[dict],
        system: str | None = None,
        max_tokens: int = 1024,
        tools: list[dict] | None = None,
        temperature: float = 0.0,
    ) -> dict:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            body["system"] = system
        if tools:
            body["tools"] = tools

        last_err = None
        for attempt in range(1, self.max_retries + 1):
            try:
                start = time.time()
                response = self.client.invoke_model(modelId=model_id, body=json.dumps(body))
                elapsed = time.time() - start
                parsed = json.loads(response["body"].read())
                parsed["_latency_seconds"] = round(elapsed, 3)
                parsed["_model_id"] = model_id
                return parsed
            except ClientError as e:
                last_err = e
                code = e.response.get("Error", {}).get("Code", "")
                logger.warning("Bedrock call failed (attempt %d): %s", attempt, code)
                if code == "ThrottlingException":
                    time.sleep(2**attempt)
                    continue
                raise
        raise last_err

    def invoke_embedding(self, text: str, model_id: str = config.EMBEDDING_MODEL) -> list[float]:
        response = self.client.invoke_model(
            modelId=model_id,
            body=json.dumps({"inputText": text}),
        )
        parsed = json.loads(response["body"].read())
        return parsed["embedding"]

    @staticmethod
    def extract_text(response: dict) -> str:
        blocks = response.get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")

    @staticmethod
    def extract_tool_input(response: dict, tool_name: str) -> dict | None:
        for block in response.get("content", []):
            if block.get("type") == "tool_use" and block.get("name") == tool_name:
                return block.get("input")
        return None
