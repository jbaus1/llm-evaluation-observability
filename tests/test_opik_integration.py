from __future__ import annotations

import os

import pytest

from app.llm.models import TokenUsage
from app.observability import OpikObserver


pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.getenv("OPIK_RUN_INTEGRATION_TESTS", "false").lower() != "true",
    reason="set OPIK_RUN_INTEGRATION_TESTS=true with local Opik running",
)
def test_records_minimal_tree_to_local_opik() -> None:
    observer = OpikObserver(capture_llm_io=True)

    with observer.trace("Integration investigation") as trace:
        with trace.span("general operation"):
            pass
        with trace.llm_span(
            "LLM operation",
            input={"messages": [{"role": "user", "content": "Hello"}]},
            model="integration-model",
            provider="local-test",
            operation="chat",
            prompt_version="integration-v1",
        ) as llm_span:
            llm_span.complete(
                output={"message": "Hello"},
                usage=TokenUsage(input_tokens=1, output_tokens=1),
            )
