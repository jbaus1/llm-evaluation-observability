from __future__ import annotations

import os
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import pytest

from examples.run_investigation import run_investigation
from app.observability import OpikObserver


pytestmark = pytest.mark.integration


def _local_endpoint_is_reachable() -> bool:
    endpoint = os.getenv("OPIK_URL_OVERRIDE", "http://localhost:5173/api")
    try:
        with urlopen(endpoint, timeout=2) as response:
            return response.status < 400
    except HTTPError:
        return False
    except URLError:
        return False


def test_records_investigation_to_local_opik(monkeypatch: pytest.MonkeyPatch) -> None:
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
    observer = OpikObserver(client=client, capture_llm_io=True)

    run_investigation(observer)
    client.flush()

    traces = client.search_traces(
        project_name=project_name,
        max_results=10,
    )
    expected_traces = [
        trace
        for trace in traces
        if trace.name == "investigation:CASE-001"
        and trace.input
        and trace.input.get("case_id") == "CASE-001"
    ]
    assert len(expected_traces) == 1
    trace = expected_traces[0]
    assert trace.name == "investigation:CASE-001"
    assert trace.input["case_id"] == "CASE-001"

    spans = client.search_spans(
        project_name=project_name,
        trace_id=trace.id,
        max_results=10,
    )
    spans_by_name = {span.name: span for span in spans}

    evidence_span = spans_by_name["evidence:process"]
    llm_span = spans_by_name["llm:extract_facts"]

    assert evidence_span.type == "general"
    assert llm_span.type == "llm"
    assert llm_span.input
    assert llm_span.output
    assert llm_span.usage
    assert all(span.start_time and span.start_time.year > 1970 for span in spans)
