"""
Test and evaluate: run 3 sample claims through the full S3-backed
pipeline, twice each — once with Sonnet on extraction, once with
Haiku — and record what differs. claim_2 is the interesting case: it
has an illegible claimant name, testing whether the cheaper model
correctly returns null or fabricates a value.

Run from claims_poc_final/: python tests/evaluate.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from document_processor import ClaimProcessor

SAMPLE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_data"
)

SAMPLE_FILES = [
    "claim_1_auto_clean.txt",
    "claim_2_auto_missing_field.txt",
    "claim_3_home_water_damage.txt",
]

MODEL_CONFIGS = {
    "sonnet_extraction": {"extraction": config.MODEL_EXTRACTION},
    "haiku_extraction": {"extraction": config.MODEL_EXTRACTION_CHEAP},
}


def run():
    processor = ClaimProcessor()  # one instance -> policy index cached across all runs
    report_rows = []

    for filename in SAMPLE_FILES:
        path = os.path.join(SAMPLE_DIR, filename)
        with open(path, encoding="utf-8") as f:
            raw_text = f.read()

        for config_name, overrides in MODEL_CONFIGS.items():
            start = time.time()
            result = processor.process(raw_text, model_overrides=overrides)
            elapsed = time.time() - start

            row = {
                "document": filename,
                "extraction_model": config_name,
                "elapsed_seconds": round(elapsed, 2),
                "claimant_name": result["extracted_fields"].get("claimant_name"),
                "extraction_valid": result["extraction_validation"]["is_valid"],
                "extraction_errors": result["extraction_validation"]["errors"],
                "summary_valid": result["summary_validation"]["is_valid"],
                "summary_warnings": result["summary_validation"]["warnings"],
            }
            report_rows.append(row)
            print(json.dumps(row, indent=2))

    findings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "findings.json")
    with open(findings_path, "w") as f:
        json.dump(report_rows, f, indent=2)
    print(f"\nWrote {findings_path}")


if __name__ == "__main__":
    run()
