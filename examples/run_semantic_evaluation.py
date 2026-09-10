from __future__ import annotations

import json

from evaluation.benchmark import BenchmarkCase, get_case
from evaluation.evaluate import evaluate_case
from evaluation.models import Evidence, GeneratedClaim
from evaluation.semantic import SemanticGroundednessEvaluator


class CalibrationJudge:
    """Deterministic stand-in for demonstrating the semantic judge contract."""

    def judge(self, prompt: str) -> str:
        if "The ventilation system failed." in prompt:
            output = {
                "supported": False,
                "score": 0.1,
                "classification": "unsupported",
                "reason": "A humidity reading does not establish a ventilation failure.",
            }
        else:
            output = {
                "supported": False,
                "score": 0.25,
                "classification": "insufficient",
                "reason": "The observations conflict, so a single status cannot be established.",
            }
        return json.dumps(output)


def _referenced_evidence(
    benchmark_case: BenchmarkCase,
    claim: GeneratedClaim,
) -> tuple[Evidence, ...]:
    evidence_by_id = {item.evidence_id: item for item in benchmark_case.evidence}
    return tuple(
        evidence_by_id[evidence_id]
        for evidence_id in claim.evidence_ids
        if evidence_id in evidence_by_id
    )


def _print_calibration(
    evaluator: SemanticGroundednessEvaluator,
    case_id: str,
    claim_index: int,
) -> None:
    benchmark_case = get_case(case_id)
    claim = benchmark_case.generated_claims[claim_index]
    evidence = _referenced_evidence(benchmark_case, claim)
    deterministic_results = {
        result.metric_name: result
        for result in evaluate_case(benchmark_case.as_evaluation_case())
    }
    semantic_result = evaluator.evaluate(claim.claim, evidence)

    print(f"case: {case_id}")
    print(f"claim: {claim.claim}")
    print(
        "evidence: "
        + "; ".join(f"{item.evidence_id}: {item.content}" for item in evidence)
    )
    print(
        "deterministic evidence_attribution: "
        f"{deterministic_results['evidence_attribution'].score:.2f}"
    )
    print(f"semantic groundedness: {semantic_result.score:.2f}")
    print(f"judge classification: {semantic_result.details['classification']}")
    print(f"judge reason: {semantic_result.reason}")
    print()


def main() -> None:
    evaluator = SemanticGroundednessEvaluator(CalibrationJudge())
    _print_calibration(evaluator, "CASE-005", 1)
    _print_calibration(evaluator, "CASE-008", 2)


if __name__ == "__main__":
    main()
