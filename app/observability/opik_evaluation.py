from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from evaluation.models import EvaluationResult


@dataclass(frozen=True, slots=True)
class FeedbackPublicationResult:
    success: bool
    published_count: int
    evaluation_results: tuple[EvaluationResult, ...]
    error: str | None = None


def _create_opik_client() -> Any:
    from opik import Opik

    return Opik(batching=False)


def publish_evaluation_results(
    trace_id: str,
    results: Sequence[EvaluationResult],
    *,
    client: Any | None = None,
) -> FeedbackPublicationResult:
    preserved_results = tuple(results)
    if not preserved_results:
        return FeedbackPublicationResult(
            success=True,
            published_count=0,
            evaluation_results=preserved_results,
        )

    feedback_scores = [
        {
            "id": trace_id,
            "name": result.metric_name,
            "value": result.score,
            "reason": result.reason,
        }
        for result in preserved_results
    ]

    try:
        opik_client = client if client is not None else _create_opik_client()
        opik_client.log_traces_feedback_scores(scores=feedback_scores)
    except Exception as error:
        return FeedbackPublicationResult(
            success=False,
            published_count=0,
            evaluation_results=preserved_results,
            error=f"{type(error).__name__}: {error}",
        )

    return FeedbackPublicationResult(
        success=True,
        published_count=len(preserved_results),
        evaluation_results=preserved_results,
    )
