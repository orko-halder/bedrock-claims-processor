"""
Evaluate the summary step two ways — a naive word-overlap metric and an
LLM-as-judge — to show the metric you pick can change the ranking.

Extraction is held constant (Sonnet) so the only variable is the summary
model (Sonnet vs. Haiku). Each generated summary is scored against a
reference answer in ground_truth.json by both scorers, and we report where
the two metrics disagree on which model "won".

Run from the repo root:  python tests/eval_scoring.py
Requires CLAIMS_BUCKET (summaries are grounded on policy docs in S3).
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from scoring import llm_judge_score, word_overlap_score

import config
from document_processor import ClaimProcessor

SAMPLE_DIR = os.path.join(ROOT, "sample_data")

# Only the summary model is swapped; extraction stays on Sonnet for both.
SUMMARY_MODELS = {"sonnet": config.MODEL_SUMMARY, "haiku": config.MODEL_EXTRACTION_CHEAP}
JUDGE_MODEL = config.MODEL_SUMMARY


def _winner(scores: dict[str, float | int | None]) -> str:
    """Model with the higher score, or 'tie' (missing scores sort last)."""
    ranked = sorted(scores.items(), key=lambda kv: (kv[1] is not None, kv[1]), reverse=True)
    (top_model, top), (_, second) = ranked[0], ranked[1]
    return "tie" if top == second else top_model


def run():
    with open(os.path.join(HERE, "ground_truth.json"), encoding="utf-8") as f:
        ground_truth = json.load(f)

    processor = ClaimProcessor()
    rows = []
    disagreements = 0

    for filename, reference in ground_truth.items():
        with open(os.path.join(SAMPLE_DIR, filename), encoding="utf-8") as f:
            raw_text = f.read()

        # Extraction held constant so summary quality is the only variable.
        fields = processor.extract_fields(raw_text)

        overlap_scores: dict[str, float | int | None] = {}
        judge_scores: dict[str, float | int | None] = {}
        for model_name, model_id in SUMMARY_MODELS.items():
            summary, _ = processor.summarize(fields, model_id=model_id)
            overlap = word_overlap_score(summary, reference)
            judgment = llm_judge_score(processor.invoker, summary, reference, JUDGE_MODEL)
            overlap_scores[model_name] = round(overlap, 3)
            judge_scores[model_name] = judgment["score"]
            rows.append(
                {
                    "document": filename,
                    "summary_model": model_name,
                    "word_overlap": round(overlap, 3),
                    "judge_score": judgment["score"],
                    "judge_rationale": judgment["rationale"],
                    "summary": summary,
                }
            )

        overlap_winner = _winner(overlap_scores)
        judge_winner = _winner(judge_scores)
        disagree = overlap_winner != judge_winner
        disagreements += disagree
        print(f"\n=== {filename} ===")
        print(f"  word-overlap: {overlap_scores}  -> winner: {overlap_winner}")
        print(f"  judge (1-5):  {judge_scores}  -> winner: {judge_winner}")
        print(f"  metrics disagree on winner: {disagree}")

    out_path = os.path.join(HERE, "scoring_findings.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    print(f"\nMetrics disagreed on {disagreements}/{len(ground_truth)} documents.")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    run()
