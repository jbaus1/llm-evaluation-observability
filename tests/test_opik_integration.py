from __future__ import annotations

import os
from datetime import datetime
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


def test_observer_configuration_matches_real_observer_path(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Verify observer uses real configuration path, not test-specific overrides.

    This test ensures the integration test exercises the same observer
    configuration as production, preventing false reassurance from a test
    that independently sets different SDK parameters.
    """
    if os.getenv("OPIK_ENABLED", "false").lower() != "true":
        pytest.skip("set OPIK_ENABLED=true to run against local Opik")
    if not _local_endpoint_is_reachable():
        pytest.skip("configured local Opik endpoint is not reachable")

    from opik import Opik

    # Use a unique project name to avoid prior traces
    project_name = f"observer-config-test-{datetime.now().isoformat()}"
    monkeypatch.setenv("OPIK_CAPTURE_LLM_IO", "true")

    # Create observer using REAL configuration path (no manual batching override)
    observer = OpikObserver()

    # Verify the observer's internal client was created
    assert observer._client is not None, "Observer should create Opik client"

    # Run investigation to generate traces
    run_investigation(observer)

    # Flush to ensure all spans are persisted
    observer._client.flush()

    # Query traces using a fresh client to verify persistence
    query_client = Opik(project_name=project_name, batching=False)
    traces = query_client.search_traces(
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
    assert len(expected_traces) == 1, f"Expected 1 trace, found {len(expected_traces)}"
    trace = expected_traces[0]

    # Validate trace integrity
    assert trace.name is not None, "Trace name must not be None"
    assert trace.name == "investigation:CASE-001"
    assert trace.input["case_id"] == "CASE-001"
    assert trace.start_time is not None, "Trace start_time must not be None"
    assert (
        trace.start_time.year > 1970
    ), f"Trace start_time must not be epoch, got {trace.start_time}"
    assert trace.end_time is not None, "Trace end_time must not be None"
    assert (
        trace.end_time.year > 1970
    ), f"Trace end_time must not be epoch, got {trace.end_time}"

    # Query spans for this trace
    spans = query_client.search_spans(
        project_name=project_name,
        trace_id=trace.id,
        max_results=10,
    )

    # Expected span names from run_investigation
    expected_span_names = {
        "evidence:process",
        "llm:extract_facts",
        "review:human",
    }
    actual_span_names = {span.name for span in spans}
    assert (
        actual_span_names == expected_span_names
    ), f"Expected spans {expected_span_names}, got {actual_span_names}"

    # Validate span count
    assert (
        len(spans) == 3
    ), f"Expected 3 spans, got {len(spans)}"
    assert trace.span_count == 3, f"Trace span_count must be 3, got {trace.span_count}"

    spans_by_name = {span.name: span for span in spans}

    # Validate each span
    for span_name, span in spans_by_name.items():
        assert span.name is not None, f"Span {span_name} name must not be None"
        assert (
            span.name != ""
        ), f"Span {span_name} name must not be empty"
        assert span.type is not None, f"Span {span_name} type must not be None"
        assert (
            span.type != ""
        ), f"Span {span_name} type must not be empty"
        assert span.start_time is not None, f"Span {span_name} start_time must not be None"
        assert (
            span.start_time.year > 1970
        ), f"Span {span_name} start_time must not be epoch, got {span.start_time}"
        assert span.end_time is not None, f"Span {span_name} end_time must not be None"
        assert (
            span.end_time.year > 1970
        ), f"Span {span_name} end_time must not be epoch, got {span.end_time}"
        assert (
            span.trace_id == trace.id
        ), f"Span {span_name} trace_id must match trace.id"

    # Validate specific span properties
    evidence_span = spans_by_name["evidence:process"]
    assert evidence_span.type == "general", "evidence:process must be general type"
    assert evidence_span.output is not None, "evidence:process must have output"

    llm_span = spans_by_name["llm:extract_facts"]
    assert llm_span.type == "llm", "llm:extract_facts must be llm type"
    assert (
        llm_span.input is not None
    ), "llm:extract_facts must have input when OPIK_CAPTURE_LLM_IO=true"
    assert (
        llm_span.output is not None
    ), "llm:extract_facts must have output when OPIK_CAPTURE_LLM_IO=true"
    assert (
        llm_span.usage is not None
    ), "llm:extract_facts must have usage information"
    assert (
        llm_span.usage.total_tokens == 54
    ), f"Expected total_tokens=54 (34+20), got {llm_span.usage.total_tokens}"

    review_span = spans_by_name["review:human"]
    assert review_span.type == "general", "review:human must be general type"
    assert review_span.output is not None, "review:human must have output"

    # Verify no malformed records with null/epoch values
    for span in spans:
        assert span.name not in (
            None,
            "",
        ), f"Found malformed span with null/empty name: {span}"
        assert span.type not in (
            None,
            "",
        ), f"Found malformed span with null/empty type: {span}"
        assert (
            span.start_time.year > 1970
        ), f"Found malformed span with epoch start_time: {span}"


def test_records_investigation_to_local_opik(monkeypatch: pytest.MonkeyPatch) -> None:
    """Legacy test: verify basic trace recording still works.

    This test maintains backward compatibility with the original integration
    test while the new test_observer_configuration_matches_real_observer_path
    provides stronger configuration validation.
    """
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
