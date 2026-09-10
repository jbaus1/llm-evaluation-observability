from __future__ import annotations

import os
from typing import Any

from app.observability import OpikObserver
from app.observability.opik_evaluation import (
    FeedbackPublicationResult,
    publish_evaluation_results,
)
from evaluation.cases import CASE_001
from evaluation.evaluate import evaluate_case
from examples.run_investigation import run_investigation


class _TraceCapturingClient:
    def __init__(self, client: Any) -> None:
        self.client = client
        self.trace_id: str | None = None

    def trace(self, **arguments: Any) -> Any:
        trace = self.client.trace(**arguments)
        self.trace_id = str(trace.id)
        return trace


def _capture_llm_io_enabled() -> bool:
    return os.getenv("OPIK_CAPTURE_LLM_IO", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def run_and_publish_case_001(
    client: Any | None = None,
) -> tuple[str, FeedbackPublicationResult]:
    if client is None:
        from opik import Opik

        client = Opik(batching=False)

    capturing_client = _TraceCapturingClient(client)
    observer = OpikObserver(
        client=capturing_client,
        capture_llm_io=_capture_llm_io_enabled(),
    )

    run_investigation(observer)
    if capturing_client.trace_id is None:
        raise RuntimeError("The investigation did not create an application trace.")

    results = evaluate_case(CASE_001)
    publication = publish_evaluation_results(
        capturing_client.trace_id,
        results,
        client=client,
    )
    client.flush()
    return capturing_client.trace_id, publication


if __name__ == "__main__":
    trace_id, publication = run_and_publish_case_001()
    print(
        {
            "trace_id": trace_id,
            "published": publication.success,
            "feedback_scores": {
                result.metric_name: result.score
                for result in publication.evaluation_results
            },
            "error": publication.error,
        }
    )
