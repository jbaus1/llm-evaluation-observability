# Deterministic Evaluation Strategy

Milestone 2 starts with deterministic metrics because their inputs, rules, and expected outputs can be inspected and reproduced exactly. They provide a stable baseline before adding probabilistic evaluators. The evaluation package is vendor-neutral and makes no network calls.

## Data contract

An `EvaluationCase` contains evidence records, required fact IDs, proposed facts, final human review decisions, and generated claims. Proposed facts carry a generated disposition of `ACCEPT`, `REJECT`, or `REVISE`. Generated claims refer to facts and evidence by ID.

Every metric returns an `EvaluationResult` with a metric name, score, numerator, denominator, structured details, and a human-readable reason. Scores are in the range 0.0 to 1.0. A metric with no items to assess returns 0.0 with a zero denominator and an explicit reason rather than reporting unsupported success.

## Fact coverage

`fact_coverage` measures how many required fact IDs appear on generated claims:

$$
\text{fact coverage} = \frac{\text{represented required fact IDs}}{\text{required fact IDs}}
$$

The result reports missing fact IDs. It does not assess whether claims are true, well written, sufficiently detailed, or supported by evidence. With no required facts, the result is 0.0 and marked not assessable.

## Evidence attribution

`evidence_attribution` measures how many generated claims reference at least one evidence ID present in the case:

$$
\text{evidence attribution} = \frac{\text{claims with a valid evidence ID}}{\text{generated claims}}
$$

Claims with no evidence IDs are reported separately from claims containing invalid IDs. A claim with both valid and invalid IDs counts as attributed because it has at least one valid reference, while its invalid IDs are still reported.

Evidence attribution is not semantic groundedness. It verifies structured links, not whether the cited evidence actually entails the claim. It also does not detect hallucinations, contradictions, incomplete evidence, or misleading citations.

## Human alignment

`human_alignment` compares each generated fact disposition with the final human disposition for that fact:

$$
\text{human alignment} = \frac{\text{matching dispositions}}{\text{facts with final human decisions}}
$$

Only facts with a final human decision are included. If decisions repeat for a fact, the last decision in the case is final. A missing generated disposition is a mismatch, never an agreement. With no final human decisions, the result is 0.0 and marked not assessable.

For v0.1, `REVISE` matches only an explicit generated `REVISE` disposition. The metric cannot determine whether requested edits were incorporated or whether revised content is better. Human alignment is also not factual correctness: a person and a generated result can agree and still be wrong.

## CASE-001

The reusable synthetic fixture has five required facts and four represented facts. It contains four generated claims: two cite valid evidence, one has no evidence, and one cites an invalid evidence ID. Three of five generated dispositions match the final human dispositions.

| Metric | Numerator | Denominator | Score |
| --- | ---: | ---: | ---: |
| `fact_coverage` | 4 | 5 | 0.80 |
| `evidence_attribution` | 2 | 4 | 0.50 |
| `human_alignment` | 3 | 5 | 0.60 |

## Publishing results

Metric computation and result publication are separate operations:

```text
EvaluationCase
	-> evaluate_case()
	-> EvaluationResult[]
	-> Opik evaluation adapter
	-> trace feedback scores
```

The `evaluation` package remains vendor-neutral. It does not import Opik, read environment configuration, or perform network calls. The adapter in `app/observability/opik_evaluation.py` maps each result's `metric_name` to an Opik feedback-score name, `score` to its value, and `reason` to the supported reason field.

Opik is the current evaluation-results backend, not the metric engine. Publication failures return an explicit unsuccessful status containing the original `EvaluationResult` objects. They do not discard results, rerun evaluation, or report success. Retries and alternate publication backends are intentionally outside this milestone.

The complete local example is:

```bash
python examples/publish_case_evaluation.py
```

## Known limitations

- Fact IDs and evidence IDs must be assigned before evaluation.
- Coverage does not compare claim wording or meaning.
- Attribution validates references, not evidentiary support.
- Human alignment compares categorical dispositions, not correctness or review quality.
- Duplicate or inconsistent source records are not validated in v0.1.
- The fixture is intentionally small and synthetic; it does not establish production thresholds.

## Semantic groundedness

`semantic_groundedness` is intentionally separate from the deterministic engine. It asks an injected LLM judge whether a claim is actually supported by its referenced evidence. It does not change `evidence_attribution`, connect to Opik, or publish feedback scores.

The judge must return JSON with `supported`, a score from 0.0 to 1.0, a short reason, and one rubric classification:

- `fully_supported`: all material parts follow from the evidence.
- `partially_supported`: some material parts follow, but at least one does not.
- `unsupported`: the evidence neither establishes nor directly refutes the claim.
- `contradicted`: the evidence directly conflicts with the claim.
- `insufficient`: evidence is absent, limited, or internally conflicting.

Structured output makes classifications testable and rejects malformed or internally inconsistent responses. It does not make the judge deterministic. Scores and borderline classifications may vary by model, model version, prompt interpretation, and provider behavior.

CASE-005 is the primary calibration case. Its ventilation-failure claim cites a valid humidity record, so deterministic attribution is 1.00. A semantic judge should classify the claim as unsupported or otherwise not supported, with a low score rather than a fixed expected value. The mock calibration returns `unsupported` at 0.10; a real judge is expected to remain in the unsupported range from 0.0 through 0.4.

CASE-008 is the conflict calibration case. Its incompatible green and red observations are passed to the judge without automatic resolution. The mock calibration returns `insufficient` at 0.25. A real judge may describe the situation as insufficient or conflicting, but should expose the ambiguity rather than select one observation without justification.

Judge calibration against human-labeled claims is required before scores can support production thresholds. Future work should measure agreement, repeatability, sensitivity to prompt/model versions, and treatment of partial support and contradiction. Claim correctness, completeness, and revision quality remain separate future metrics.
