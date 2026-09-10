from __future__ import annotations

from typing import Any

import pytest

from app.llm.models import TokenUsage
from app.observability import OpikObserver


class RecordingSpan:
    def __init__(self) -> None:
        self.completed: list[dict[str, Any]] = []

    def end(
        self,
        *,
        output: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        usage: dict[str, int] | None = None,
    ) -> None:
        arguments: dict[str, Any] = {"metadata": metadata}
        if output is not None:
            arguments["output"] = output
        if usage is not None:
            arguments["usage"] = usage
        self.completed.append(arguments)


class RecordingTrace:
    def __init__(self) -> None:
        self.created_spans: list[dict[str, Any]] = []
        self.completed: list[dict[str, Any]] = []

    def span(self, **arguments: Any) -> RecordingSpan:
        child = RecordingSpan()
        arguments["object"] = child
        self.created_spans.append(arguments)
        return child

    def end(
        self,
        *,
        output: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.completed.append({"output": output, "metadata": metadata})


class RecordingClient:
    def __init__(self) -> None:
        self.created_traces: list[dict[str, Any]] = []

    def trace(self, **arguments: Any) -> RecordingTrace:
        trace = RecordingTrace()
        arguments["object"] = trace
        self.created_traces.append(arguments)
        return trace


def test_creates_trace_general_span_and_evaluation_ready_llm_span() -> None:
    client = RecordingClient()
    observer = OpikObserver(client=client, capture_llm_io=True)

    with observer.trace(
        "Investigation", metadata={"request_id": "public-example"}
    ) as trace:
        with trace.span("prepare", input={"documents": 2}):
            pass
        with trace.llm_span(
            "answer",
            input={"messages": ["question"]},
            model="example-model",
            provider="example-provider",
            operation="chat",
            prompt_version="v1",
            metadata={"stage": "draft"},
        ) as llm_span:
            llm_span.complete(
                output={"answer": "result"},
                metadata={"finish_reason": "stop"},
                usage=TokenUsage(input_tokens=7, output_tokens=3),
            )

    recorded_trace = client.created_traces[0]
    trace_object = recorded_trace["object"]
    general_span, llm_span = trace_object.created_spans

    assert recorded_trace["name"] == "Investigation"
    assert general_span["type"] == "general"
    assert llm_span["type"] == "llm"
    assert llm_span["input"] == {"messages": ["question"]}
    assert llm_span["model"] == "example-model"
    assert llm_span["provider"] == "example-provider"
    assert llm_span["metadata"] == {
        "stage": "draft",
        "operation": "chat",
        "prompt_version": "v1",
    }
    assert llm_span["object"].completed == [
        {
            "metadata": {
                "stage": "draft",
                "operation": "chat",
                "prompt_version": "v1",
                "finish_reason": "stop",
            },
            "output": {"answer": "result"},
            "usage": {
                "prompt_tokens": 7,
                "completion_tokens": 3,
                "total_tokens": 10,
            },
        }
    ]


def test_disables_llm_payload_capture_but_keeps_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPIK_CAPTURE_LLM_IO", "false")
    client = RecordingClient()
    observer = OpikObserver(client=client)

    with observer.trace("Investigation") as trace:
        with trace.llm_span(
            "answer",
            input={"secret": "not-recorded"},
            model="example-model",
            operation="chat",
        ) as llm_span:
            llm_span.complete(
                output={"secret": "also-not-recorded"},
                usage=TokenUsage(input_tokens=2, output_tokens=1),
            )

    recorded_span = client.created_traces[0]["object"].created_spans[0]
    assert recorded_span["input"] is None
    assert recorded_span["model"] == "example-model"
    assert recorded_span["metadata"]["operation"] == "chat"
    assert "output" not in recorded_span["object"].completed[0]
    assert recorded_span["object"].completed[0]["usage"]["total_tokens"] == 3


def test_is_fail_open_when_sdk_operations_raise() -> None:
    class FailingClient:
        def trace(self, **arguments: Any) -> None:
            raise RuntimeError("telemetry unavailable")

    observer = OpikObserver(client=FailingClient())

    with observer.trace("Investigation") as trace:
        with trace.span("prepare"):
            pass
        with trace.llm_span("answer") as llm_span:
            llm_span.complete(output={"answer": "application continues"})
