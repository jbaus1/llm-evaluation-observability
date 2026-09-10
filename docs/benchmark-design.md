# Synthetic Benchmark Design

The benchmark contains ten small, intentionally designed cases. Ten is enough to cover positive controls, isolated metric failures, review outcomes, conflicting evidence, and sparse evidence while keeping every fixture readable in one sitting. The cases are deterministic, public-safe, and contain no external data, network calls, or generated randomness.

Each immutable `BenchmarkCase` contains a title, description, purpose, evidence, required fact IDs, proposed facts, final human review decisions, generated claims, and expected metric results. Expected scores include explicit numerators, denominators, and explanations. Tests run every fixture through the unchanged `evaluate_case()` engine and require exact agreement.

## Case inventory

| Case | Purpose | Fact coverage | Evidence attribution | Human alignment |
| --- | --- | ---: | ---: | ---: |
| CASE-001 | Partial extraction baseline | 4/5 = 0.80 | 2/4 = 0.50 | 3/5 = 0.60 |
| CASE-002 | Clean, compact positive control | 3/3 = 1.00 | 3/3 = 1.00 | 3/3 = 1.00 |
| CASE-003 | Omit two required facts | 3/5 = 0.60 | 3/3 = 1.00 | 5/5 = 1.00 |
| CASE-004 | Include missing and invalid evidence references | 4/4 = 1.00 | 2/4 = 0.50 | 4/4 = 1.00 |
| CASE-005 | Cite valid evidence that does not support a claim | 2/2 = 1.00 | 2/2 = 1.00 | 1/2 = 0.50 |
| CASE-006 | Reject one generated ACCEPT disposition | 4/4 = 1.00 | 4/4 = 1.00 | 3/4 = 0.75 |
| CASE-007 | Match a generated and human REVISE disposition | 3/3 = 1.00 | 3/3 = 1.00 | 3/3 = 1.00 |
| CASE-008 | Preserve incompatible evidence interpretations | 3/3 = 1.00 | 3/3 = 1.00 | 3/3 = 1.00 |
| CASE-009 | Provide too little evidence for a complete investigation | 2/4 = 0.50 | 1/2 = 0.50 | 1/3 = 0.33 |
| CASE-010 | Broad perfect end-to-end positive control | 4/4 = 1.00 | 4/4 = 1.00 | 4/4 = 1.00 |

CASE-002 and CASE-010 are positive controls. CASE-002 is deliberately compact; CASE-010 covers a wider four-fact flow with mixed `ACCEPT` and `REVISE` dispositions. CASE-001, CASE-003, CASE-004, CASE-005, CASE-006, and CASE-009 intentionally reduce at least one metric. CASE-008 exposes a limitation even though all deterministic scores are perfect.

## Structural attribution is not groundedness

CASE-005 contains a generated claim that the ventilation system failed. It cites E2, a real evidence record that only reports humidity. The deterministic evaluator correctly gives the claim structural attribution because the evidence ID exists, producing `evidence_attribution = 1.00`.

The claim is not semantically supported by that evidence. Therefore:

```text
evidence_attribution != semantic groundedness
```

This is intentional and provides a concrete justification for a future semantic evaluator. No semantic matching logic belongs in the current deterministic metric.

## REVISE behavior

CASE-007 includes a generated `REVISE` disposition and a final human `REVISE` decision for the same fact. Under v0.1 semantics they align because the labels match exactly. The benchmark does not determine whether a revision was completed, whether feedback was incorporated, or whether revised wording improved. Revision quality remains future scope.

## Conflicting and sparse evidence

CASE-008 records two incompatible observations about the same indicator and preserves both references. The deterministic metrics can verify representation, references, and disposition agreement, but they cannot resolve the conflict.

CASE-009 provides one evidence record for four required facts. It intentionally demonstrates incomplete coverage, partial attribution, and review disagreement caused by an underspecified record set.

## Why synthetic data

Synthetic fixtures are inspectable, stable, safe to publish, and designed around exact evaluation behaviors. They avoid credentials, private schemas, domain-sensitive records, and changing external sources. They are controls for engineering behavior, not evidence of model quality in a real deployment.

## Adding cases

Add a case only when it introduces a distinct behavior or boundary. Give it a stable sequential ID, concise synthetic evidence, an explicit purpose, structured expected counts, and a human-readable explanation for every metric. Run the full benchmark test to prove the expected counts and scores match `evaluate_case()`. Do not add random filler, duplicate controls, or metric-specific logic to the fixture layer.

Use the computed summary when reviewing the benchmark:

```bash
python examples/benchmark_summary.py
```
