"""
Document upload — verified live against the real bucket in step 8.
This uploads the incoming CLAIM document (raw/ prefix). Policy
documents are separate — they live under policies/ and are read by
rag.py, not uploaded per-claim.
"""

import os

import boto3

import config


class DocumentUploader:
    def __init__(self, bucket: str = config.S3_BUCKET, region: str = config.AWS_REGION):
        self.bucket = bucket
        self.client = boto3.client("s3", region_name=region)

    def upload(self, local_path: str, key_prefix: str = config.S3_RAW_PREFIX) -> str:
        filename = os.path.basename(local_path)
        key = f"{key_prefix}{filename}"
        self.client.upload_file(local_path, self.bucket, key)
        return f"s3://{self.bucket}/{key}"

    def download_text(self, key: str) -> str:
        obj = self.client.get_object(Bucket=self.bucket, Key=key)
        return obj["Body"].read().decode("utf-8")
