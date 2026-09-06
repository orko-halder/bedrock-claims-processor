# Step 4 — Test and evaluate: findings and recommendations

## Setup
3 sample claim documents, each run through the full pipeline twice —
extraction step only swapped between Claude Sonnet 4.5 and Claude
Haiku 4.5. Doc-understanding wasn't a separate step in this
implementation (samples were plain text, not scanned images); summary
generation stayed on Sonnet in both runs, so this comparison isolates
the extraction step specifically.

`claim_2_auto_missing_field.txt` was deliberately constructed with an
illegible claimant name (`[illegible]` in the source text) — this is
the case that actually tests model behavior, not just speed.

## Results

| Document | Model | Latency (s) | Extraction valid | claimant_name |
|---|---|---|---|---|
| claim_1 (clean) | Sonnet | 9.45 | ✅ | Marcus Reed |
| claim_1 (clean) | Haiku | 6.90 | ✅ | Marcus Reed |
| claim_2 (illegible field) | Sonnet | 7.48 | ❌ (correctly flagged missing) | null |
| claim_2 (illegible field) | Haiku | 6.10 | ❌ (correctly flagged missing) | null |
| claim_3 (home, different policy) | Sonnet | 7.42 | ✅ | Priya Nathan |
| claim_3 (home, different policy) | Haiku | 5.94 | ✅ | Priya Nathan |

## Findings

**1. No correctness gap on this sample.** The concern going in was that
a cheaper model might guess a value for the illegible claimant field
instead of correctly returning null. Haiku didn't — it matched Sonnet
exactly on all three documents, including the ambiguous one. Both
models correctly triggered the validator's "missing required field"
error on claim_2 rather than silently passing bad data through.

**2. Haiku was consistently faster** — roughly 20–30% lower latency on
every document (9.45→6.90s, 7.48→6.10s, 7.42→5.94s). For a
high-volume extraction step, that's a meaningful throughput/cost
difference with no observed correctness cost.

**3. RAG retrieval correctly discriminated between policies** across
both claim types tested — the auto claims retrieved POL-1001, the home
claim retrieved POL-2044, with no cross-contamination. This was
independent of which model handled extraction.

**4. Summary generation caught non-obvious coverage issues on every
document**, not just the one designed to test it:
   - claim_1: flagged that rideshare status wasn't stated, so the
     exclusion couldn't be ruled out
   - claim_2: flagged the rideshare exclusion directly
   - claim_3: flagged the sudden-vs-gradual damage distinction that
     determines whether the plumbing exclusion applies

This wasn't something explicitly engineered into the prompt for each
specific scenario — it's the grounded-summary prompt (root the
response in retrieved policy text) generalizing correctly across
different coverage questions.

## Recommendation

**Use Haiku for the extraction step.** On this test set, it matched
Sonnet's correctness — including the specific failure mode being
tested for (fabricating values on ambiguous input) — while running
meaningfully faster. Keep Sonnet for summary generation, since that's
the output a human actually reads and where prose quality/reasoning
depth matters more than raw speed.

## Honest limitations of this evaluation

- **Sample size is 3 documents.** This is not enough to make a
  production go/no-go call — it's a directional signal, not a
  statistically meaningful comparison. A real decision would need
  dozens to hundreds of documents, including a wider range of
  illegibility/ambiguity patterns, not just one.
- **No adversarial or heavily degraded input was tested** — real
  scanned claim forms have OCR errors, multi-page structure, and
  handwriting quality issues that plain text samples can't simulate.
- **The validator's checks are structural, not semantic** — it
  confirms required fields are non-null, not that the values are
  *correct*. A model could return a plausible-looking but wrong
  claim number and this evaluation wouldn't catch it.
- **Cost wasn't measured directly** — only latency. Token usage
  (`usage.input_tokens` / `usage.output_tokens`) is available on every
  response via `model_invoker.py` but wasn't captured in this run;
  a real cost comparison should include it, since Haiku's per-token
  price is also lower, compounding the latency advantage.
- **Only one extraction schema was tested** — a more complex claim
  type (e.g. more fields, nested structures) might show a bigger gap
  between models than this relatively simple 7-field schema does.

# Step 5 — how you score matters more than which model you pick

The step-4 comparison scored the *extraction* step, where fields are
exact strings and lexical matching is fine. Scoring the *summary* step —
free text, where a correct answer can be phrased many ways — is where the
choice of metric bites. `tests/eval_scoring.py` scores each generated
summary against a reference answer (`tests/ground_truth.json`) two ways:

- **word_overlap** — token Jaccard against the reference. The naive metric
  a quick script reaches for.
- **llm_judge** — a second model (Sonnet) rates factual accuracy 1–5,
  explicitly told to ignore wording.

Extraction was held constant on Sonnet; only the summary model was swapped
(Sonnet vs. Haiku), so the summary is the only variable.

## Results (live)

| Document | word-overlap (Sonnet / Haiku) | overlap "winner" | judge 1–5 (Sonnet / Haiku) | judge verdict |
|---|---|---|---|---|
| claim_1 | 0.451 / 0.396 | Sonnet | 5 / 5 | tie |
| claim_2 | 0.371 / 0.404 | Haiku  | 4 / 4 | tie |
| claim_3 | 0.511 / 0.505 | Sonnet | 5 / 5 | tie |

## Finding

**Word overlap named a winner on all three documents; the judge found none.**
The overlap margins (0.005–0.055) are phrasing noise, not accuracy — both
summaries were rated factually equivalent on every document. Tellingly,
both models dropped to a judge score of 4 on `claim_2` for the *same*
reason (each omitted the fact that the claimant name is illegible and must
be obtained), which is evidence the judge is tracking factual content
rather than wording. A team that trusted the lexical metric would "prefer"
a model that is no more correct — the metric manufactures a ranking the
task doesn't support.

Practical takeaway: use exact/lexical matching only where the correct
output is genuinely fixed (e.g. extracted field values), and use
task-aware judging for free-text outputs.

## Limitations of this eval

- **The judge is Sonnet grading both its own and Haiku's output**, so it
  could favor its own phrasing (self-preference bias) — yet it still rated
  them tied, if anything understating the point.
- **3 documents, one reference answer each** — directional, not
  conclusive; a larger set with adversarial paraphrases would test the gap
  between the two metrics more strongly.
- **Single judge model, no human adjudication** — a production eval would
  calibrate the judge against human ratings before trusting it.
