# Claims Document Processing PoC

A working proof-of-concept for automating insurance claim document processing, built for AWS's Generative AI Developer certification (Task 1.1: analyze requirements and design GenAI solutions). Built and tested live against Amazon Bedrock and S3, using synthetic test data throughout (see `sample_data/`) — no real insurer or customer data.

## Architecture

```
S3 (raw claim upload)
      |
      v
Orchestrator
      |
  +---+---+-------------+
  |       |             |
Extract  Retrieve     Summary  <- grounded on both
(tool     (RAG, S3        |
 call)     policies)      v
                       Output (validated)
```

- **Extraction**: Claude Sonnet via tool-use, forcing structured JSON output instead of parsing prose.
- **Retrieval**: Titan embeddings + cosine similarity over policy documents stored in S3, cached after first build.
- **Summary**: grounded on both the extracted fields and the retrieved policy text — this is what let it correctly flag a rideshare coverage exclusion neither step was explicitly told to look for.
- **Validation**: pure-Python checks, no model calls — catches missing required fields and un-grounded summaries.

## Setup

```bash
pip install -r requirements.txt
aws configure   # region: us-east-1
```

Bedrock model access is now automatic on first invoke per AWS account (the old manual "Model Access" console page has been retired). Anthropic models may prompt a one-time use-case form on first call.

Create the bucket and seed policy documents:
```bash
aws s3 mb s3://your-bucket-name
aws s3 cp sample_data/policies/POL-1001.txt s3://your-bucket-name/policies/
aws s3 cp sample_data/policies/POL-2044.txt s3://your-bucket-name/policies/
```

Set `CLAIMS_BUCKET` in `config.py` or as an environment variable to match.

## Run

Point the pipeline at your bucket. `CLAIMS_BUCKET` is required — the app
fails fast if it's unset (see `.env.example` for the full list of vars):

```bash
export CLAIMS_BUCKET=your-bucket-name
python main.py sample_data/claim_1_auto_clean.txt
```

## Test and evaluate

```bash
python tests/evaluate.py
```
Compares Claude Sonnet vs. Haiku on extraction across 3 sample documents. See `tests/FINDINGS.md` for real results — Haiku matched Sonnet's correctness (including correctly returning `null` on an illegible field) while running 20–30% faster.

## Gotchas I hit building this (real, not hypothetical)

- **Model IDs go stale fast.** Bedrock retires model versions on its own schedule. The IDs in `config.py` were verified current as of this writing — if you get `ResourceNotFoundException: This model version has reached the end of its life`, check AWS's model lifecycle docs for the current ID.
- **Current Claude models need the `us.` (or `eu.`/`global.`) inference-profile prefix** for on-demand invocation — a bare `anthropic.claude-...` model ID without it throws a validation error.
- **AWS Marketplace requires a credit card, not direct debit**, even though direct debit works fine for regular AWS billing. The resulting error (`INVALID_PAYMENT_INSTRUMENT`) doesn't make this obvious — if you hit it despite having a payment method on file, check the card type specifically.
- **A Python venv freezes whatever Python version was active at creation time.** Fixing your Python version (e.g. via pyenv) *after* a venv already exists does nothing — you have to delete and recreate the venv. Always check `python3 --version` immediately before *and* after `python3 -m venv .venv`.
- **`X | None` type hints require Python 3.10+.** On older Python, add `from __future__ import annotations` at the top of the file rather than rewriting every type hint.
- **IAM changes take a few seconds to propagate.** If a Lambda function or role reports an assume-role error immediately after creation, wait ~10 seconds and retry before assuming something's actually broken.

## Known limitations

- Test set is 3 documents — a directional signal, not production-scale evidence.
- The validator checks structure (are required fields present), not semantic correctness (are the values actually right).
- No scanned, handwritten, or adversarial documents tested — samples were plain text.
- Retry logic exists in `model_invoker.py` but throttling was never actually observed/triggered during testing.
