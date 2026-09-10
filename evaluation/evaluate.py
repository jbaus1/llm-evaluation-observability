from evaluation.metrics.deterministic import (
    evidence_attribution,
    fact_coverage,
    human_alignment,
)
from evaluation.models import EvaluationCase, EvaluationResult


def evaluate_case(case: EvaluationCase) -> tuple[EvaluationResult, ...]:
    return (
        fact_coverage(case),
        evidence_attribution(case),
        human_alignment(case),
    )
