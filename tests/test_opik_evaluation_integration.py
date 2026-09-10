from __future__ import annotations

import os
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import pytest

from examples.publish_case_evaluation import run_and_publish_case_001


pytestmark = pytest.mark.integration


def _local_endpoint_is_reachable() -> bool:
    endpoint = os.getenv("OPIK_URL_OVERRIDE", "http://localhost:5173/api")
    try:
        with urlopen(endpoint, timeout=2) as response:
            return response.status < 400
    except (HTTPError, URLError):
        return False


def test_publishes_case_001_feedback_to_its_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if os.getenv("OPIK_ENABLED", "false").lower() != "true":
        pytest.skip("set OPIK_ENABLED=true to run against local Opik")
    if not _local_endpoint_is_reachable():
        pytest.skip("configured local Opik endpoint is not reachable")

    from opik import Opik

    project_name = os.getenv(
        "OPIK_PROJECT_NAME", "llm-observability-reference-integration"
    )
    monkeypatch.setenv("OPIK_CAPTURE_LLM_IO", "true")
    client = Opik(project_name=project_name, batching=False)

    trace_id, publication = run_and_publish_case_001(client)
    client.flush()

    assert publication.success is True
    assert publication.published_count == 3

    trace = client.get_trace_content(id=trace_id)
    assert trace.id == trace_id
    assert trace.name == "investigation:CASE-001"

    feedback_by_name = {
        feedback.name: feedback.value for feedback in trace.feedback_scores or []
    }
    assert feedback_by_name == {
        "fact_coverage": 0.8,
        "evidence_attribution": 0.5,
        "human_alignment": 0.6,
    }
