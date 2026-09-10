from __future__ import annotations

import subprocess
import sys
from typing import Any

from app.observability.opik_evaluation import publish_evaluation_results
from evaluation.models import EvaluationResult


def _results() -> list[EvaluationResult]:
    return [
        EvaluationResult("fact_coverage", 0.8, 4, 5, {}, "4 of 5 facts."),
        EvaluationResult("evidence_attribution", 0.5, 2, 4, {}, "2 of 4 claims."),
        EvaluationResult("human_alignment", 0.6, 3, 5, {}, "3 of 5 decisions."),
    ]


class RecordingClient:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def log_traces_feedback_scores(self, **arguments: Any) -> None:
        self.calls.append(arguments)
        if self.error is not None:
            raise self.error


def test_maps_results_to_feedback_scores() -> None:
    client = RecordingClient()
    results = _results()

    publication = publish_evaluation_results("trace-123", results, client=client)

    scores = client.calls[0]["scores"]
    assert [score["name"] for score in scores] == [
        "fact_coverage",
        "evidence_attribution",
        "human_alignment",
    ]
    assert [score["value"] for score in scores] == [0.8, 0.5, 0.6]
    assert all(score["id"] == "trace-123" for score in scores)
    assert [score["reason"] for score in scores] == [
        result.reason for result in results
    ]
    assert publication.success is True
    assert publication.published_count == 3
    assert publication.evaluation_results == tuple(results)


def test_publication_failure_preserves_evaluation_results() -> None:
    results = _results()
    client = RecordingClient(error=RuntimeError("Opik is unavailable"))

    publication = publish_evaluation_results("trace-123", results, client=client)

    assert publication.success is False
    assert publication.published_count == 0
    assert publication.evaluation_results == tuple(results)
    assert publication.error == "RuntimeError: Opik is unavailable"


def test_empty_results_are_safe_and_do_not_call_opik() -> None:
    client = RecordingClient()

    publication = publish_evaluation_results("trace-123", [], client=client)

    assert publication.success is True
    assert publication.published_count == 0
    assert publication.evaluation_results == ()
    assert client.calls == []


def test_evaluation_package_does_not_import_opik() -> None:
    script = """
import builtins

real_import = builtins.__import__

def reject_opik(name, *args, **kwargs):
    if name == "opik" or name.startswith("opik."):
        raise AssertionError("evaluation imported Opik")
    return real_import(name, *args, **kwargs)

builtins.__import__ = reject_opik
import evaluation
"""

    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
