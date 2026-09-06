"""
Policy RAG — S3-backed, not local files. This is the real difference
from the original claims_poc/rag.py, which read from a local
sample_data/policies/ directory. This version lists and downloads from
S3 directly (list_objects_v2 + get_object), matching the architecture
diagram where S3 is the actual document store.

Caching: policy embeddings are built once per ClaimProcessor lifetime
and reused — verified today that re-embedding on every call (the
naive first version) works but is wasteful once policy text is stable.
"""

import math

from botocore.client import BaseClient

import config
from model_invoker import ModelInvoker


class PolicyRAG:
    def __init__(
        self,
        invoker: ModelInvoker,
        s3_client: BaseClient,
        bucket: str = config.S3_BUCKET,
        prefix: str = config.S3_POLICY_PREFIX,
    ):
        self.invoker = invoker
        self.s3 = s3_client
        self.bucket = bucket
        self.prefix = prefix
        self._index: list[tuple[str, str, list[float]]] | None = None  # (key, text, vector)

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def build_index(self):
        response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=self.prefix)
        keys = [obj["Key"] for obj in response.get("Contents", [])]

        index = []
        for key in keys:
            obj = self.s3.get_object(Bucket=self.bucket, Key=key)
            text = obj["Body"].read().decode("utf-8")
            vector = self.invoker.invoke_embedding(text)
            index.append((key, text, vector))

        self._index = index

    def retrieve(self, query: str, top_k: int = 1) -> list[str]:
        if self._index is None:
            self.build_index()
        if not self._index:
            return []

        query_vector = self.invoker.invoke_embedding(query)
        scored = [
            (self._cosine_similarity(query_vector, vector), key, text)
            for key, text, vector in self._index
        ]
        scored.sort(reverse=True)
        return [f"{key}: {text}" for _, key, text in scored[:top_k]]
