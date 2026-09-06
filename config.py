"""
Config for the merged project. Model IDs below were verified against
AWS's own docs mid-session (via AWS MCP), not just assumed — both are
confirmed Active with EOL no sooner than late 2026:
  - Claude Sonnet 4.5: EOL no sooner than 9/29/2026
  - Claude Haiku 4.5:  EOL no sooner than 10/1/2026
Re-check these before this project's exam value expires — Bedrock
retires model versions on its own schedule (we hit this once already,
with claude-3-5-sonnet-20241022-v2:0).
"""

import os

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

S3_BUCKET = os.environ.get("CLAIMS_BUCKET")
if not S3_BUCKET:
    raise RuntimeError(
        "Set the CLAIMS_BUCKET environment variable to your S3 bucket name "
        "(see .env.example)."
    )
S3_RAW_PREFIX = "raw/"
S3_POLICY_PREFIX = "policies/"

# Note the `us.` prefix — required for on-demand invocation of current
# Claude models on Bedrock. The bare ID (no prefix) throws
# ValidationException. Confirmed working live this session.
MODEL_DOC_UNDERSTANDING = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
MODEL_EXTRACTION = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
MODEL_SUMMARY = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

# Cheaper alternative for the Step 4 (evaluate.py) comparison.
MODEL_EXTRACTION_CHEAP = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
