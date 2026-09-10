from __future__ import annotations

from contextlib import AbstractContextManager
from types import TracebackType
from typing import Any

from examples.run_investigation import run_investigation


class RecordingSpan(AbstractContextManager["RecordingSpan"]):
    def __init__(self, events: list[tuple[str, dict[str, Any]]], name: str) -> None:
        self._events = events
        self._name = name

    def __enter__(self) -> RecordingSpan:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def complete(self, **arguments: Any) -> None:
        self._events.append((f"complete:{self._name}", arguments))


class RecordingTrace(RecordingSpan):
    def span(self, name: str, **arguments: Any) -> RecordingSpan:
        self._events.append((f"start:{name}", arguments))
        return RecordingSpan(self._events, name)

    def llm_span(self, name: str, **arguments: Any) -> RecordingSpan:
        self._events.append((f"start:{name}", arguments))
        return RecordingSpan(self._events, name)


class RecordingObserver:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def trace(self, name: str, **arguments: Any) -> RecordingTrace:
        self.events.append((f"start:{name}", arguments))
        return RecordingTrace(self.events, name)


def test_investigation_records_expected_event_sequence() -> None:
    observer = RecordingObserver()

    result = run_investigation(observer=observer)  # type: ignore[arg-type]

    assert result == {"case_id": "CASE-001", "status": "reviewed"}
    assert [name for name, _ in observer.events] == [
        "start:investigation:CASE-001",
        "start:evidence:process",
        "complete:evidence:process",
        "start:llm:extract_facts",
        "complete:llm:extract_facts",
        "start:review:human",
        "complete:review:human",
        "complete:investigation:CASE-001",
    ]

    llm_start = observer.events[3][1]
    llm_complete = observer.events[4][1]
    assert llm_start["input"]["evidence"]
    assert llm_start["model"] == "synthetic-extractor-v1"
    assert llm_start["provider"] == "local-simulation"
    assert llm_start["operation"] == "extract_facts"
    assert llm_start["prompt_version"] == "1.0"
    assert llm_complete["output"]["facts"]
    assert llm_complete["usage"].as_opik_usage()["total_tokens"] == 54

    review_complete = observer.events[6][1]
    assert review_complete["output"]["action"] == "approved"
