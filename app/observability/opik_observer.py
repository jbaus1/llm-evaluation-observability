from __future__ import annotations

import os
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Any, Mapping

from app.llm.models import TokenUsage

Metadata = Mapping[str, Any]
Payload = Mapping[str, Any]


def _capture_llm_io_from_environment() -> bool:
    return os.getenv("OPIK_CAPTURE_LLM_IO", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


class OpikObserver:
    """Small, fail-open boundary around the optional Opik SDK."""

    def __init__(
        self,
        client: Any | None = None,
        *,
        capture_llm_io: bool | None = None,
    ) -> None:
        self._client = client if client is not None else self._create_client()
        self._capture_llm_io = (
            _capture_llm_io_from_environment()
            if capture_llm_io is None
            else capture_llm_io
        )

    @staticmethod
    def _create_client() -> Any | None:
        try:
            from opik import Opik

            return Opik()
        except Exception:
            return None

    def trace(
        self,
        name: str,
        *,
        input: Payload | None = None,
        metadata: Metadata | None = None,
    ) -> TraceHandle:
        trace = None
        if self._client is not None:
            try:
                trace = self._client.trace(
                    name=name,
                    input=dict(input) if input is not None else None,
                    metadata=dict(metadata) if metadata is not None else None,
                )
            except Exception:
                pass
        return TraceHandle(trace, self._capture_llm_io, metadata)


class _CompletableHandle(AbstractContextManager["_CompletableHandle"]):
    def __init__(self, target: Any | None, metadata: Metadata | None = None) -> None:
        self._target = target
        self._metadata = dict(metadata or {})
        self._completed = False

    def __enter__(self) -> _CompletableHandle:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if not self._completed:
            self.complete()

    def complete(
        self,
        *,
        output: Payload | None = None,
        metadata: Metadata | None = None,
        usage: TokenUsage | None = None,
    ) -> None:
        if self._completed:
            return

        self._metadata.update(metadata or {})
        arguments: dict[str, Any] = {"metadata": dict(self._metadata)}
        if output is not None:
            arguments["output"] = dict(output)
        if usage is not None:
            arguments["usage"] = usage.as_opik_usage()

        if self._target is not None:
            try:
                self._target.end(**arguments)
            except Exception:
                pass
        self._completed = True


class SpanHandle(_CompletableHandle):
    def __init__(
        self,
        target: Any | None,
        metadata: Metadata | None = None,
        *,
        capture_output: bool = True,
    ) -> None:
        super().__init__(target, metadata)
        self._capture_output = capture_output

    def complete(
        self,
        *,
        output: Payload | None = None,
        metadata: Metadata | None = None,
        usage: TokenUsage | None = None,
    ) -> None:
        super().complete(
            output=output if self._capture_output else None,
            metadata=metadata,
            usage=usage,
        )


class TraceHandle(_CompletableHandle):
    def __init__(
        self,
        target: Any | None,
        capture_llm_io: bool,
        metadata: Metadata | None = None,
    ) -> None:
        super().__init__(target, metadata)
        self._capture_llm_io = capture_llm_io

    def complete(
        self,
        *,
        output: Payload | None = None,
        metadata: Metadata | None = None,
    ) -> None:
        super().complete(output=output, metadata=metadata)

    def span(
        self,
        name: str,
        *,
        input: Payload | None = None,
        metadata: Metadata | None = None,
    ) -> SpanHandle:
        return self._start_span(
            name=name,
            span_type="general",
            input=input,
            metadata=metadata,
        )

    def llm_span(
        self,
        name: str,
        *,
        input: Payload | None = None,
        model: str | None = None,
        provider: str | None = None,
        operation: str | None = None,
        prompt_version: str | None = None,
        metadata: Metadata | None = None,
    ) -> SpanHandle:
        llm_metadata = dict(metadata or {})
        if operation is not None:
            llm_metadata["operation"] = operation
        if prompt_version is not None:
            llm_metadata["prompt_version"] = prompt_version

        return self._start_span(
            name=name,
            span_type="llm",
            input=input if self._capture_llm_io else None,
            metadata=llm_metadata,
            model=model,
            provider=provider,
            capture_output=self._capture_llm_io,
        )

    def _start_span(
        self,
        *,
        name: str,
        span_type: str,
        input: Payload | None,
        metadata: Metadata | None,
        model: str | None = None,
        provider: str | None = None,
        capture_output: bool = True,
    ) -> SpanHandle:
        span = None
        if self._target is not None:
            arguments: dict[str, Any] = {
                "name": name,
                "type": span_type,
                "input": dict(input) if input is not None else None,
                "metadata": dict(metadata) if metadata is not None else None,
            }
            if model is not None:
                arguments["model"] = model
            if provider is not None:
                arguments["provider"] = provider
            try:
                span = self._target.span(**arguments)
            except Exception:
                pass
        return SpanHandle(span, metadata, capture_output=capture_output)
