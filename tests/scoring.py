"""
Two ways to score a free-text claim summary against a reference answer:

  1. word_overlap_score — a naive lexical metric (token Jaccard). This is
     the kind of thing a quick benchmarking script reaches for, and it
     measures phrasing similarity, not correctness: a correct paraphrase
     that reuses none of the reference's exact words scores low.
  2. llm_judge_score — a second model reads the candidate against the
     reference facts and rates factual accuracy, ignoring wording.

The point of having both is to show they can disagree. See eval_scoring.py.
"""

import re

from model_invoker import ModelInvoker

JUDGE_TOOL = {
    "name": "record_judgment",
    "description": "Record a factual-accuracy judgment of a claim summary against reference facts.",
    "input_schema": {
        "type": "object",
        "properties": {
            "score": {
                "type": "integer",
                "description": (
                    "1-5. 5 = every reference fact is present and correct with no "
                    "contradictions; 1 = mostly wrong or contradicts the reference."
                ),
            },
            "rationale": {"type": "string", "description": "One sentence explaining the score."},
        },
        "required": ["score", "rationale"],
    },
}

JUDGE_SYSTEM = (
    "You grade an insurance claim summary for FACTUAL accuracy against a set of "
    "reference facts. Judge only whether the facts and coverage conclusions are "
    "correct and not contradicted — ignore differences in wording, length, or "
    "phrasing. Always respond by calling the record_judgment tool."
)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def word_overlap_score(candidate: str, reference: str) -> float:
    """Token Jaccard overlap in [0, 1] — the deliberately naive metric."""
    cand, ref = _tokens(candidate), _tokens(reference)
    if not cand or not ref:
        return 0.0
    return len(cand & ref) / len(cand | ref)


def llm_judge_score(invoker: ModelInvoker, candidate: str, reference: str, model_id: str) -> dict:
    """Ask a judge model to rate factual accuracy (1-5) ignoring phrasing."""
    user = f"Reference facts:\n{reference}\n\nCandidate summary:\n{candidate}"
    response = invoker.invoke(
        model_id=model_id,
        messages=[{"role": "user", "content": user}],
        system=JUDGE_SYSTEM,
        tools=[JUDGE_TOOL],
        max_tokens=300,
    )
    result = invoker.extract_tool_input(response, "record_judgment") or {}
    return {"score": result.get("score"), "rationale": result.get("rationale", "")}
