"""
CLI entrypoint.

Usage:
    python main.py sample_data/claim_1_auto_clean.txt
    python main.py sample_data/claim_1_auto_clean.txt --upload
"""

import argparse
import json

from document_processor import ClaimProcessor
from s3_upload import DocumentUploader


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Path to a local claim document")
    parser.add_argument("--upload", action="store_true", help="Also upload to S3 before processing")
    args = parser.parse_args()

    with open(args.file, encoding="utf-8") as f:
        raw_text = f.read()

    if args.upload:
        uploader = DocumentUploader()
        uri = uploader.upload(args.file)
        print(f"Uploaded to {uri}")

    processor = ClaimProcessor()
    result = processor.process(raw_text)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
